from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field, field_validator

from .hmaa_partner_package import HMAAPartnerValidationRequest


HMAA_PARTNER_RESPONSE_VERSION = "worldshepherd.hmaa.partner-attestation-response.v0.9"


class PartnerAttestationOutcome(str, Enum):
    CONFIRMED = "CONFIRMED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"


class PartnerAttestationState(str, Enum):
    UNVERIFIED_EXTERNAL_RESPONSE = "UNVERIFIED_EXTERNAL_RESPONSE"
    VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE = (
        "VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE"
    )
    VERIFIED_RESPONSE_REQUIRES_HUMAN_REVIEW = "VERIFIED_RESPONSE_REQUIRES_HUMAN_REVIEW"
    VERIFIED_RESPONSE_REJECTED = "VERIFIED_RESPONSE_REJECTED"


class ExternalSignature(BaseModel):
    algorithm: str = Field(min_length=1, max_length=128)
    key_id: str = Field(min_length=1, max_length=512)
    value: str = Field(min_length=1, max_length=16384)


class HMAAPartnerAttestationResponse(BaseModel):
    response_version: str = HMAA_PARTNER_RESPONSE_VERSION
    request_package_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mission_id: str = Field(min_length=1, max_length=512)
    attested_scope: str = Field(min_length=1, max_length=512)
    organization_id: str = Field(min_length=1, max_length=512)
    reviewer_id: str = Field(min_length=1, max_length=512)
    attested_at: datetime
    outcome: PartnerAttestationOutcome
    confirmed_check_sha256: list[str] = Field(default_factory=list, max_length=64)
    evidence_references: list[str] = Field(default_factory=list, max_length=64)
    signature: ExternalSignature
    response_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("confirmed_check_sha256")
    @classmethod
    def validate_check_hashes(cls, value: list[str]) -> list[str]:
        pattern_prefix = "sha256:"
        for item in value:
            if not item.startswith(pattern_prefix) or len(item) != 71:
                raise ValueError("confirmed check references must be sha256 digests")
            try:
                int(item[len(pattern_prefix) :], 16)
            except ValueError as exc:
                raise ValueError("confirmed check references must be sha256 digests") from exc
        if len(set(value)) != len(value):
            raise ValueError("confirmed check references must be unique")
        return value


class PartnerSignatureVerification(BaseModel):
    verified: bool
    verifier_id: str = Field(min_length=1, max_length=512)
    reason: str = Field(min_length=1, max_length=2048)


class PartnerAttestationVerifier(Protocol):
    def verify(
        self,
        *,
        canonical_payload: bytes,
        signature: ExternalSignature,
    ) -> PartnerSignatureVerification: ...


class NoPartnerAttestationVerifier:
    """Fail-closed production default until a trusted verifier is configured."""

    def verify(
        self,
        *,
        canonical_payload: bytes,
        signature: ExternalSignature,
    ) -> PartnerSignatureVerification:
        del canonical_payload, signature
        return PartnerSignatureVerification(
            verified=False,
            verifier_id="none-configured",
            reason="no trusted external-attestation verifier is configured",
        )


class HMAAPartnerAttestationAssessment(BaseModel):
    state: PartnerAttestationState
    request_package_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    response_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    outcome: PartnerAttestationOutcome
    signature_verified: bool
    verifier_id: str
    verifier_reason: str
    all_requested_checks_confirmed: bool
    human_acceptance_required: bool = True
    partner_validated: bool = False
    live_environment_validated: bool = False
    flight_validated: bool = False
    operationally_validated: bool = False
    claimable_labels: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def requested_check_digests(request: HMAAPartnerValidationRequest) -> list[str]:
    return sorted({_sha256_text(check) for check in request.requested_checks})


def _response_unsigned_body(response: HMAAPartnerAttestationResponse) -> dict[str, Any]:
    return response.model_dump(
        mode="json",
        exclude={"signature", "response_sha256"},
    )


def canonical_unsigned_response_bytes(response: HMAAPartnerAttestationResponse) -> bytes:
    return json.dumps(
        _response_unsigned_body(response),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def expected_response_sha256(response: HMAAPartnerAttestationResponse) -> str:
    signed_container = {
        **_response_unsigned_body(response),
        "signature": response.signature.model_dump(mode="json"),
    }
    encoded = json.dumps(
        signed_container,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def assess_partner_attestation_response(
    request: HMAAPartnerValidationRequest,
    response: HMAAPartnerAttestationResponse,
    *,
    verifier: PartnerAttestationVerifier | None = None,
) -> HMAAPartnerAttestationAssessment:
    if response.request_package_sha256 != request.package_sha256:
        raise ValueError("partner response is not bound to this request package")
    if response.mission_id != request.mission_id:
        raise ValueError("partner response mission_id does not match request")
    if response.attested_scope != request.requested_scope:
        raise ValueError("partner response scope does not match request")
    if expected_response_sha256(response) != response.response_sha256:
        raise ValueError("partner response hash verification failed")

    required_checks = set(requested_check_digests(request))
    confirmed_checks = set(response.confirmed_check_sha256)
    unknown_checks = confirmed_checks - required_checks
    if unknown_checks:
        raise ValueError("partner response contains unknown requested-check references")
    all_confirmed = confirmed_checks == required_checks
    if response.outcome is PartnerAttestationOutcome.CONFIRMED and not all_confirmed:
        raise ValueError("CONFIRMED response must confirm every requested check")
    if response.outcome is PartnerAttestationOutcome.REJECTED and confirmed_checks:
        raise ValueError("REJECTED response must not claim confirmed requested checks")

    active_verifier = verifier or NoPartnerAttestationVerifier()
    verification = active_verifier.verify(
        canonical_payload=canonical_unsigned_response_bytes(response),
        signature=response.signature,
    )

    blockers: list[str] = []
    if not verification.verified:
        blockers.append("external signature authenticity has not been verified")
        state = PartnerAttestationState.UNVERIFIED_EXTERNAL_RESPONSE
    elif response.outcome is PartnerAttestationOutcome.CONFIRMED:
        blockers.append("human acceptance is required before any partner-validation claim")
        state = PartnerAttestationState.VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE
    elif response.outcome is PartnerAttestationOutcome.PARTIAL:
        blockers.append("partial external attestation requires human review")
        state = PartnerAttestationState.VERIFIED_RESPONSE_REQUIRES_HUMAN_REVIEW
    else:
        blockers.append("external reviewer rejected the validation request")
        state = PartnerAttestationState.VERIFIED_RESPONSE_REJECTED

    return HMAAPartnerAttestationAssessment(
        state=state,
        request_package_sha256=request.package_sha256,
        response_sha256=response.response_sha256,
        outcome=response.outcome,
        signature_verified=verification.verified,
        verifier_id=verification.verifier_id,
        verifier_reason=verification.reason,
        all_requested_checks_confirmed=all_confirmed,
        human_acceptance_required=True,
        partner_validated=False,
        live_environment_validated=False,
        flight_validated=False,
        operationally_validated=False,
        claimable_labels=[
            "IMPLEMENTED IN SOFTWARE",
            "REQUIRES PARTNER VALIDATION",
        ],
        blocking_reasons=blockers,
    )
