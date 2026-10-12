"""Utilities for provenance-aware translation comparison.

This intentionally avoids a single 'accuracy' score. Translation differences are
classified so textual drift is not mistaken for discovery or failure.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

TOKEN_RE = re.compile(r"[A-Za-z0-9'-]+")


@dataclass(frozen=True)
class TranslationVector:
    literal_tokens: int
    comparison_tokens: int
    shared_tokens: int
    literal_only: tuple[str, ...]
    comparison_only: tuple[str, ...]


def tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text)]


def token_vector(literal: str, comparison: str) -> TranslationVector:
    """Return a transparent lexical-overlap vector, not a quality score."""
    a = Counter(tokens(literal))
    b = Counter(tokens(comparison))
    shared = a & b
    a_only = a - b
    b_only = b - a
    return TranslationVector(
        literal_tokens=sum(a.values()),
        comparison_tokens=sum(b.values()),
        shared_tokens=sum(shared.values()),
        literal_only=tuple(sorted(a_only.elements())),
        comparison_only=tuple(sorted(b_only.elements())),
    )


ALLOWED_CLASSES = {
    "manuscript_variant",
    "transcription_variant",
    "spelling_variant",
    "segmentation_variant",
    "lexical_disagreement",
    "grammatical_disagreement",
    "poetic_editorial_expansion",
    "editorial_expansion",
    "later_doctrinal_reinterpretation",
    "manuscript_lacuna_risk",
    "possible_copying_error",
    "unresolved",
}


def validate_difference_classes(classes: Iterable[str]) -> None:
    unknown = sorted(set(classes) - ALLOWED_CLASSES)
    if unknown:
        raise ValueError(f"Unknown translation-difference classes: {unknown}")


def blind_status(translations_seen_before_freeze: bool) -> str:
    return "RETROSPECTIVE_CALIBRATION" if translations_seen_before_freeze else "BLIND"
