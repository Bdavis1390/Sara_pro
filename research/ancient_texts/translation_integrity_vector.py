from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class TranslationIntegrityVector:
    source_items: int
    aligned_items: int
    unsupported_insertions: int = 0
    omissions: int = 0
    uncertainty_markers_source: int = 0
    uncertainty_markers_preserved: int = 0
    restorations_source: int = 0
    restorations_disclosed: int = 0
    witness_variants_material: int = 0
    witness_variants_disclosed: int = 0
    named_entity_mismatches: int = 0
    superseded_reading_hits: int = 0
    untranslated_residue: int = 0
    notes: list[str] = field(default_factory=list)

    def validate(self) -> None:
        integer_fields = [
            self.source_items, self.aligned_items, self.unsupported_insertions,
            self.omissions, self.uncertainty_markers_source,
            self.uncertainty_markers_preserved, self.restorations_source,
            self.restorations_disclosed, self.witness_variants_material,
            self.witness_variants_disclosed, self.named_entity_mismatches,
            self.superseded_reading_hits, self.untranslated_residue,
        ]
        if any(v < 0 for v in integer_fields):
            raise ValueError("integrity counts cannot be negative")
        if self.aligned_items > self.source_items:
            raise ValueError("aligned items cannot exceed source items")
        if self.uncertainty_markers_preserved > self.uncertainty_markers_source:
            raise ValueError("preserved uncertainty cannot exceed source uncertainty")
        if self.restorations_disclosed > self.restorations_source:
            raise ValueError("disclosed restorations cannot exceed source restorations")
        if self.witness_variants_disclosed > self.witness_variants_material:
            raise ValueError("disclosed variants cannot exceed material variants")

    def vector(self) -> dict[str, float | int]:
        self.validate()
        coverage = self.aligned_items / self.source_items if self.source_items else 0.0
        uncertainty_preservation = (
            self.uncertainty_markers_preserved / self.uncertainty_markers_source
            if self.uncertainty_markers_source else 1.0
        )
        restoration_disclosure = (
            self.restorations_disclosed / self.restorations_source
            if self.restorations_source else 1.0
        )
        witness_disclosure = (
            self.witness_variants_disclosed / self.witness_variants_material
            if self.witness_variants_material else 1.0
        )
        return {
            "alignment_coverage": coverage,
            "unsupported_insertions": self.unsupported_insertions,
            "omissions": self.omissions,
            "uncertainty_preservation": uncertainty_preservation,
            "restoration_disclosure": restoration_disclosure,
            "witness_variant_disclosure": witness_disclosure,
            "named_entity_mismatches": self.named_entity_mismatches,
            "superseded_reading_hits": self.superseded_reading_hits,
            "untranslated_residue": self.untranslated_residue,
        }

    def claim_ceiling(self) -> str:
        self.validate()
        if self.superseded_reading_hits:
            return "DO_NOT_USE_AS_CURRENT_WITHOUT_REVISION"
        if self.named_entity_mismatches:
            return "MATERIAL_TRANSLATION_MISMATCH"
        if self.unsupported_insertions:
            return "INTERPRETIVE_TRANSLATION_REQUIRES_LABEL"
        if (
            self.uncertainty_markers_source
            and self.uncertainty_markers_preserved < self.uncertainty_markers_source
        ):
            return "UNCERTAINTY_FLATTENED_REQUIRES_REVIEW"
        if (
            self.restorations_source
            and self.restorations_disclosed < self.restorations_source
        ):
            return "RESTORATION_FLATTENED_REQUIRES_REVIEW"
        return "ELIGIBLE_FOR_SPECIALIST_REVIEW"

def compare_translation_vectors(
    a: TranslationIntegrityVector,
    b: TranslationIntegrityVector,
) -> dict[str, dict[str, float | int]]:
    av = a.vector()
    bv = b.vector()
    return {
        key: {"a": av[key], "b": bv[key]}
        for key in av
    }
