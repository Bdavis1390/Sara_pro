from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ControlEvidenceState(str, Enum):
    UNKNOWN = "UNKNOWN"
    PRESENT = "PRESENT"
    GAP = "GAP"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ControlEvidence(BaseModel):
    control_id: str = Field(min_length=1)
    state: ControlEvidenceState = ControlEvidenceState.UNKNOWN
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def present_requires_evidence(self) -> "ControlEvidence":
        if self.state == ControlEvidenceState.PRESENT and not self.evidence_refs:
            raise ValueError("PRESENT control evidence requires at least one evidence reference")
        return self


class ComplianceReadinessProfile(BaseModel):
    framework: str = Field(min_length=1)
    assessment_status: str = "UNKNOWN"
    controls: list[ControlEvidence] = Field(default_factory=list)
    authoritative_assessment_ref: str | None = None

    def gap_summary(self) -> dict[str, int]:
        counts = {state.value: 0 for state in ControlEvidenceState}
        for control in self.controls:
            counts[control.state.value] += 1
        return counts

    def externally_validated(self) -> bool:
        return (
            self.assessment_status == "AUTHORITATIVE_VALIDATED"
            and bool(self.authoritative_assessment_ref)
        )

    def claims_boundary(self) -> str:
        if self.externally_validated():
            return "Authoritative assessment reference is recorded; scope and currency still govern any external claim."
        return "Readiness evidence only. No CMMC/NIST 800-171 compliance, certification, SPRS score, or government authorization is claimed."
