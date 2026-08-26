from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .qualification import canonical_digest


class AttestationState(str, Enum):
    INTERNAL_UNSIGNED = "INTERNAL_UNSIGNED"
    INTERNALLY_SIGNED = "INTERNALLY_SIGNED"
    EXTERNALLY_VERIFIED = "EXTERNALLY_VERIFIED"


class SoftwareComponent(BaseModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    package_type: str = Field(min_length=1)
    supplier: str | None = None
    purl: str | None = None
    artifact_digest: str | None = None


class BuildProvenance(BaseModel):
    provenance_id: str = Field(min_length=1)
    source_repository: str = Field(min_length=1)
    source_commit: str = Field(min_length=1)
    builder_id: str = Field(min_length=1)
    build_environment_digest: str = Field(min_length=1)
    output_artifact_digest: str = Field(min_length=1)
    components: list[SoftwareComponent] = Field(default_factory=list)
    sbom_digest: str | None = None
    attestation_state: AttestationState = AttestationState.INTERNAL_UNSIGNED
    signature_ref: str | None = None
    external_verifier: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def verification_requires_evidence(self) -> "BuildProvenance":
        if self.attestation_state == AttestationState.INTERNALLY_SIGNED and not self.signature_ref:
            raise ValueError("internally signed attestation requires signature_ref")
        if self.attestation_state == AttestationState.EXTERNALLY_VERIFIED:
            if not self.signature_ref or not self.external_verifier:
                raise ValueError("external verification requires signature_ref and external_verifier")
        return self

    def digest(self) -> str:
        return canonical_digest(self)

    def claims_boundary(self) -> str:
        if self.attestation_state == AttestationState.EXTERNALLY_VERIFIED:
            return "External verifier is recorded; verification scope and signer trust still govern use."
        return "Internal software provenance evidence only; no external signing, SLSA level, government acceptance, or supply-chain certification is claimed."
