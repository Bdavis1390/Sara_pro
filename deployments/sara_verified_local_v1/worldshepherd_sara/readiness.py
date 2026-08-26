from __future__ import annotations

from enum import IntEnum
from pydantic import BaseModel, Field, model_validator


class ReadinessRung(IntEnum):
    SCHEMA = 1
    FIXTURE = 2
    INTERNAL_SOFTWARE = 3
    SIMULATION = 4
    HIL = 5
    PHYSICAL_LAB = 6
    PARTNER = 7
    INDEPENDENT = 8
    COMPLIANCE_CERTIFICATION = 9
    OPERATIONAL = 10


class CapabilityReadinessRecord(BaseModel):
    capability_id: str = Field(min_length=1)
    capability_name: str = Field(min_length=1)
    highest_supported_rung: ReadinessRung
    evidence_refs: dict[ReadinessRung, list[str]] = Field(default_factory=dict)
    blocked_next_rung: ReadinessRung | None = None
    missing_evidence: list[str] = Field(default_factory=list)
    claims_boundary: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_required_for_claimed_rung(self) -> "CapabilityReadinessRecord":
        for rung in ReadinessRung:
            if rung <= self.highest_supported_rung and not self.evidence_refs.get(rung):
                raise ValueError(f"evidence reference required for supported rung {rung.name}")
        if self.blocked_next_rung is not None and self.blocked_next_rung <= self.highest_supported_rung:
            raise ValueError("blocked_next_rung must be above highest_supported_rung")
        return self

    def can_claim(self, rung: ReadinessRung) -> bool:
        return rung <= self.highest_supported_rung and bool(self.evidence_refs.get(rung))

    def next_rung(self) -> ReadinessRung | None:
        value = int(self.highest_supported_rung) + 1
        return ReadinessRung(value) if value <= int(ReadinessRung.OPERATIONAL) else None
