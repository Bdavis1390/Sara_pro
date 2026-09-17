from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

class DifferenceClass(str, Enum):
    T0_STABLE = "T0_STABLE"
    T1_STYLE = "T1_STYLE"
    T2_LEXICAL = "T2_LEXICAL"
    T3_GRAMMATICAL = "T3_GRAMMATICAL"
    T4_WITNESS = "T4_WITNESS"
    T5_RESTORATION = "T5_RESTORATION"
    T6_SUPERSEDED = "T6_SUPERSEDED"
    T7_INTERPOLATION = "T7_INTERPOLATION"
    T8_UNRESOLVED = "T8_UNRESOLVED"

@dataclass(frozen=True)
class TokenAlignment:
    source_token: str
    translation_span: str | None
    confidence: float
    notes: tuple[str, ...] = ()

@dataclass
class TranslationAudit:
    audit_id: str
    witness_ref: str
    translation_ref: str
    translation_date: str | None = None
    alignments: list[TokenAlignment] = field(default_factory=list)
    supplied_concepts: list[str] = field(default_factory=list)
    omitted_source_items: list[str] = field(default_factory=list)
    uncertain_source_items: list[str] = field(default_factory=list)
    restored_source_items: list[str] = field(default_factory=list)
    witness_variants: list[str] = field(default_factory=list)
    lexical_alternatives: list[str] = field(default_factory=list)
    grammar_alternatives: list[str] = field(default_factory=list)
    superseded_readings: list[str] = field(default_factory=list)
    difference_classes: set[DifferenceClass] = field(default_factory=set)
    source_refs: list[str] = field(default_factory=list)

    def classify(self) -> set[DifferenceClass]:
        classes = set(self.difference_classes)
        if self.lexical_alternatives:
            classes.add(DifferenceClass.T2_LEXICAL)
        if self.grammar_alternatives:
            classes.add(DifferenceClass.T3_GRAMMATICAL)
        if self.witness_variants:
            classes.add(DifferenceClass.T4_WITNESS)
        if self.restored_source_items:
            classes.add(DifferenceClass.T5_RESTORATION)
        if self.superseded_readings:
            classes.add(DifferenceClass.T6_SUPERSEDED)
        if self.supplied_concepts:
            classes.add(DifferenceClass.T7_INTERPOLATION)
        if not classes:
            classes.add(DifferenceClass.T0_STABLE)
        return classes

    def confidence_vector(self) -> dict[str, float | int]:
        valid = [a.confidence for a in self.alignments]
        return {
            "aligned_token_count": len(self.alignments),
            "mean_alignment_confidence": sum(valid) / len(valid) if valid else 0.0,
            "supplied_concept_count": len(self.supplied_concepts),
            "omitted_source_count": len(self.omitted_source_items),
            "uncertain_source_count": len(self.uncertain_source_items),
            "restored_source_count": len(self.restored_source_items),
            "witness_variant_count": len(self.witness_variants),
            "lexical_alternative_count": len(self.lexical_alternatives),
            "grammar_alternative_count": len(self.grammar_alternatives),
            "superseded_reading_count": len(self.superseded_readings),
        }

    def claim_ceiling(self) -> str:
        classes = self.classify()
        if DifferenceClass.T6_SUPERSEDED in classes:
            return "DO_NOT_USE_AS_CURRENT_WITHOUT_REVISION"
        if DifferenceClass.T4_WITNESS in classes or DifferenceClass.T5_RESTORATION in classes:
            return "WITNESS_DEPENDENT_TRANSLATION"
        if DifferenceClass.T7_INTERPOLATION in classes:
            return "INTERPRETIVE_TRANSLATION_REQUIRES_LABEL"
        if DifferenceClass.T2_LEXICAL in classes or DifferenceClass.T3_GRAMMATICAL in classes:
            return "TRANSLATION_WITH_MATERIAL_UNCERTAINTY"
        if classes == {DifferenceClass.T1_STYLE}:
            return "SEMANTICALLY_STABLE_STYLE_VARIANT"
        if classes == {DifferenceClass.T0_STABLE}:
            return "CURRENTLY_STABLE_WITHIN_AUDITED_EVIDENCE"
        return "MIXED_TRANSLATION_RISK"

def summarize(audits: Iterable[TranslationAudit]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for audit in audits:
        for c in audit.classify():
            counts[c.value] = counts.get(c.value, 0) + 1
    return counts
