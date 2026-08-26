from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .qualification import canonical_digest


class ConformanceState(str, Enum):
    UNTESTED = "UNTESTED"
    INTERNAL_PASS = "INTERNAL_PASS"
    INTERNAL_FAIL = "INTERNAL_FAIL"
    PARTNER_VALIDATED = "PARTNER_VALIDATED"
    EXTERNALLY_CERTIFIED = "EXTERNALLY_CERTIFIED"


class InterfaceContract(BaseModel):
    contract_id: str = Field(min_length=1)
    interface_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    required_message_types: list[str] = Field(default_factory=list)
    required_fields: dict[str, list[str]] = Field(default_factory=dict)
    authoritative_spec_ref: str | None = None
    spec_digest: str | None = None

    def digest(self) -> str:
        return canonical_digest(self)


class ConformanceCheck(BaseModel):
    check_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    passed: bool
    evidence_refs: list[str] = Field(default_factory=list)
    observed: dict[str, Any] = Field(default_factory=dict)


class InterfaceConformanceRecord(BaseModel):
    record_id: str = Field(min_length=1)
    contract_digest: str = Field(min_length=1)
    implementation_id: str = Field(min_length=1)
    implementation_digest: str = Field(min_length=1)
    state: ConformanceState = ConformanceState.UNTESTED
    checks: list[ConformanceCheck] = Field(default_factory=list)
    partner: str | None = None
    external_authority: str | None = None
    certificate_ref: str | None = None

    @model_validator(mode="after")
    def state_requires_evidence(self) -> "InterfaceConformanceRecord":
        if self.state == ConformanceState.INTERNAL_PASS:
            if not self.checks or not all(check.passed for check in self.checks):
                raise ValueError("INTERNAL_PASS requires at least one check and all checks passing")
        if self.state == ConformanceState.INTERNAL_FAIL:
            if not self.checks or all(check.passed for check in self.checks):
                raise ValueError("INTERNAL_FAIL requires at least one failing check")
        if self.state == ConformanceState.PARTNER_VALIDATED and not self.partner:
            raise ValueError("PARTNER_VALIDATED requires partner identity")
        if self.state == ConformanceState.EXTERNALLY_CERTIFIED:
            if not self.external_authority or not self.certificate_ref:
                raise ValueError("EXTERNALLY_CERTIFIED requires authority and certificate reference")
        return self

    def claims_boundary(self) -> str:
        if self.state == ConformanceState.EXTERNALLY_CERTIFIED:
            return "External certification metadata is recorded; scope, validity period, and certificate terms still govern the claim."
        if self.state == ConformanceState.PARTNER_VALIDATED:
            return "Partner validation is recorded only for the stated interface and evidence scope; no government certification is inferred."
        return "Internal interface-conformance evidence only; no platform acceptance, government certification, or operational interoperability is claimed."
