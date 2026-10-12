from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from math import log2
import random
from typing import Iterable, Sequence

CONTAMINATION_CLASSES = {
    "C0_SESSION_BLIND",
    "C1_PARTIAL_LEXICON",
    "C2_RETROSPECTIVE",
    "C3_EDITORIAL_DEPENDENT",
    "C4_UNKNOWN",
}

EPISTEMIC_CLASSES = {
    "KNOWN_DECIPHERED",
    "PARTIALLY_CONSTRAINED",
    "UNDECIPHERED",
    "SYNTHETIC_NULL",
}

@dataclass(frozen=True)
class BenchmarkMeta:
    benchmark_id: str
    epistemic_class: str
    contamination_class: str
    source_witness: str
    target_translation_exposed: bool = False
    allowed_evidence: tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if self.epistemic_class not in EPISTEMIC_CLASSES:
            raise ValueError(f"unknown epistemic_class: {self.epistemic_class}")
        if self.contamination_class not in CONTAMINATION_CLASSES:
            raise ValueError(f"unknown contamination_class: {self.contamination_class}")
        if self.target_translation_exposed and self.contamination_class in {
            "C0_SESSION_BLIND", "C1_PARTIAL_LEXICON"
        }:
            raise ValueError(
                "exposed target translation is incompatible with blind/partial-lexicon label"
            )

def tokenize(text: str) -> list[str]:
    return [t for t in text.replace("\n", " ").split(" ") if t]

def shannon_entropy(items: Sequence[str]) -> float:
    if not items:
        return 0.0
    counts = Counter(items)
    n = len(items)
    return -sum((c / n) * log2(c / n) for c in counts.values())

def conditional_entropy(items: Sequence[str]) -> float:
    if len(items) < 2:
        return 0.0
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    prev_counts = Counter(items[:-1])
    for a, b in zip(items, items[1:]):
        transitions[a][b] += 1
    total = len(items) - 1
    result = 0.0
    for prev, nexts in transitions.items():
        p_prev = prev_counts[prev] / total
        subtotal = sum(nexts.values())
        h = -sum((c / subtotal) * log2(c / subtotal) for c in nexts.values())
        result += p_prev * h
    return result

def ngram_counts(items: Sequence[str], n: int) -> Counter[tuple[str, ...]]:
    if n <= 0:
        raise ValueError("n must be positive")
    return Counter(tuple(items[i:i+n]) for i in range(max(0, len(items)-n+1)))

def positional_profile(sequences: Iterable[Sequence[str]]) -> dict[str, dict[str, float]]:
    stats: dict[str, Counter[str]] = defaultdict(Counter)
    totals = Counter()
    for seq in sequences:
        if not seq:
            continue
        for i, tok in enumerate(seq):
            totals[tok] += 1
            if i == 0:
                stats[tok]["initial"] += 1
            if i == len(seq) - 1:
                stats[tok]["final"] += 1
            if 0 < i < len(seq) - 1:
                stats[tok]["medial"] += 1
    return {
        tok: {
            k: stats[tok][k] / totals[tok]
            for k in ("initial", "medial", "final")
        }
        for tok in totals
    }

def repeated_subsequences(
    items: Sequence[str], min_n: int = 2, max_n: int = 5
) -> dict[int, Counter[tuple[str, ...]]]:
    out = {}
    for n in range(min_n, max_n + 1):
        counts = ngram_counts(items, n)
        out[n] = Counter({k: v for k, v in counts.items() if v > 1})
    return out

def shuffle_surrogate(items: Sequence[str], seed: int) -> list[str]:
    rng = random.Random(seed)
    out = list(items)
    rng.shuffle(out)
    return out

def markov_surrogate(
    items: Sequence[str], seed: int, length: int | None = None
) -> list[str]:
    if not items:
        return []
    if len(items) == 1:
        return [items[0]] * (length or 1)
    rng = random.Random(seed)
    transitions: dict[str, list[str]] = defaultdict(list)
    for a, b in zip(items, items[1:]):
        transitions[a].append(b)
    all_tokens = list(items)
    current = rng.choice(all_tokens)
    out = [current]
    target = length or len(items)
    while len(out) < target:
        options = transitions.get(current)
        current = rng.choice(options if options else all_tokens)
        out.append(current)
    return out

def claim_ceiling(
    meta: BenchmarkMeta, has_validated_decipherment: bool = False
) -> str:
    meta.validate()
    if meta.epistemic_class == "UNDECIPHERED" and not has_validated_decipherment:
        return "STRUCTURE_ONLY_NO_TRANSLATION"
    if meta.contamination_class in {
        "C2_RETROSPECTIVE", "C3_EDITORIAL_DEPENDENT", "C4_UNKNOWN"
    }:
        return "CALIBRATION_ONLY"
    return "SESSION_BLIND_HOLDOUT_RESULT"

def assert_translation_permitted(
    meta: BenchmarkMeta, has_validated_decipherment: bool = False
) -> None:
    if claim_ceiling(meta, has_validated_decipherment) == "STRUCTURE_ONLY_NO_TRANSLATION":
        raise PermissionError(
            "running semantic translation is prohibited for undeciphered controls "
            "without validated decipherment"
        )

def diagnostics(text: str) -> dict:
    tokens = tokenize(text)
    return {
        "token_count": len(tokens),
        "type_count": len(set(tokens)),
        "unigram_entropy": shannon_entropy(tokens),
        "conditional_entropy": conditional_entropy(tokens),
        "top_unigrams": Counter(tokens).most_common(20),
        "top_bigrams": ngram_counts(tokens, 2).most_common(20),
        "repeated_subsequences": {
            n: [(" ".join(k), v) for k, v in c.most_common(20)]
            for n, c in repeated_subsequences(tokens).items()
        },
    }
