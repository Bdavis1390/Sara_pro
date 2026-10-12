from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

class ReadingStatus(str, Enum):
    CORPUS_STANDARD = "CORPUS_STANDARD"
    COMPETING_PUBLISHED = "COMPETING_PUBLISHED"
    HISTORICAL = "HISTORICAL"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class ReadingHypothesis:
    value: str
    status: ReadingStatus
    evidence_refs: tuple[str, ...] = ()
    confidence: float | None = None
    note: str | None = None

@dataclass
class ReadingLattice:
    lemma_id: str
    semantic_value: str | None
    display_transliteration: str
    corpus_pragmatic_choice: bool = False
    readings: list[ReadingHypothesis] = field(default_factory=list)

    def validate(self) -> None:
        if not self.display_transliteration:
            raise ValueError("display_transliteration is required")
        seen = set()
        for r in self.readings:
            if r.value in seen:
                raise ValueError(f"duplicate reading hypothesis: {r.value}")
            seen.add(r.value)
            if r.confidence is not None and not (0.0 <= r.confidence <= 1.0):
                raise ValueError("confidence must be between 0 and 1")

    def candidate_readings(self) -> set[str]:
        self.validate()
        values = {self.display_transliteration}
        values.update(r.value for r in self.readings)
        return values

    def has_live_competition(self) -> bool:
        return any(
            r.status == ReadingStatus.COMPETING_PUBLISHED
            for r in self.readings
        )

    def claim_ceiling_for_sound_match(self) -> str:
        if self.corpus_pragmatic_choice or self.has_live_competition():
            return "PHONOLOGICAL_MATCH_UNRESOLVED"
        return "PHONOLOGICAL_MATCH_MAY_BE_TESTED"

def surface_match(a: ReadingLattice, b: ReadingLattice) -> bool:
    return a.display_transliteration == b.display_transliteration

def lattice_overlap(a: ReadingLattice, b: ReadingLattice) -> set[str]:
    return a.candidate_readings() & b.candidate_readings()

def phonological_match_status(a: ReadingLattice, b: ReadingLattice) -> dict:
    overlap = lattice_overlap(a, b)
    if not overlap:
        return {
            "match": False,
            "overlap": [],
            "claim_ceiling": "NO_READING_OVERLAP",
        }
    unresolved = (
        a.claim_ceiling_for_sound_match() == "PHONOLOGICAL_MATCH_UNRESOLVED"
        or b.claim_ceiling_for_sound_match() == "PHONOLOGICAL_MATCH_UNRESOLVED"
    )
    return {
        "match": True,
        "overlap": sorted(overlap),
        "claim_ceiling": (
            "CORRESPONDENCE_ONLY_READING_UNCERTAIN"
            if unresolved
            else "PHONOLOGICAL_MATCH_MAY_BE_TESTED"
        ),
    }

def reject_naive_cognate_claim(a: ReadingLattice, b: ReadingLattice) -> None:
    status = phonological_match_status(a, b)
    if not status["match"]:
        raise ValueError("no phonological overlap")
    raise PermissionError(
        "a matching transliteration/reading is insufficient for cognacy or transmission; "
        "historical-comparative and chronology/contact evidence is required"
    )
