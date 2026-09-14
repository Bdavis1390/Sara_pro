from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from pydantic import BaseModel, Field

from .hmaa_partner_package import (
    HMAAPartnerEvidenceReference,
    HMAAPartnerValidationRequest,
    PARTNER_VALIDATION_SCOPE,
)
from .hmaa_partner_response import (
    HMAAPartnerAttestationAssessment,
    HMAAPartnerAttestationResponse,
    NoPartnerAttestationVerifier,
    PartnerAttestationOutcome,
    PartnerAttestationState,
    PartnerAttestationVerifier,
    canonical_unsigned_response_bytes,
    expected_response_sha256,
)


HMAA_SESSION_PARTNER_REQUEST_VERSION = (
    "worldshepherd.hmaa.session-partner-validation-request.v1.2"
)


class SessionReceiptBinding(Protocol):
    mission_id: str
    endpoint: str
    preflight_report_sha256: str
    receipt_sha256: str
    partner_request_package_sha256: str | None
    external_environment_provenance_confirmed: bool
    live_environment_validated: bool
    partner_validated: bool
    flight_validated: bool
    operationally_validated: bool


class HMAASessionPartnerValidationRequest(BaseModel):
    package_version: str = HMAA_SESSION_PARTNER_REQUEST_VERSION
    request_status: str = "READY_FOR_PARTNER_VALIDATION_REQUEST"
    mission_id: str = Field(min_length=1, max_length=512)
    requested_scope: str = PARTNER_VALIDATION_SCOPE
    environment_endpoint: str = Field(min_length=1, max_length=2048)
    preflight_report_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    session_receipt_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    inner_request_package_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    attestation_aggregate_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    qualifying_capture_count: int = Field(ge=3)
    evidence_references: list[HMAAPartnerEvidenceReference]
    requested_checks: list[str]
    claimable_labels: list[str]
    prohibited_claims: list[str]
    external_environment_provenance_confirmed: bool = False
    live_environment_validated: bool = False
    partner_validated: bool = False
    flight_validated: bool = False
    operationally_validated: bool = False
    package_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def build_session_partner_validation_request(
    receipt: SessionReceiptBinding,
    inner_request: HMAAPartnerValidationRequest,
) -> HMAASessionPartnerValidationRequest:
    """Bind the v0.8 evidence request to the exact v1.2 session and endpoint."""

    if receipt.mission_id != inner_request.mission_id:
        raise ValueError("session receipt and inner partner request mission IDs do not match")
    if receipt.partner_request_package_sha256 != inner_request.package_sha256:
        raise ValueError("session receipt is not bound to the supplied inner partner request")
    if inner_request.attestation_aggregate_sha256 is None:
        raise ValueError("inner partner request is missing aggregate attestation evidence")
    if (
        receipt.external_environment_provenance_confirmed
        or receipt.live_environment_validated
        or receipt.partner_validated
        or receipt.flight_validated
        or receipt.operationally_validated
    ):
        raise ValueError("session receipt contains a preexisting external validation claim")
    if inner_request.live_environment_validated:
        raise ValueError("inner partner request contains a live-validation claim")

    references = sorted(
        inner_request.evidence_references,
        key=lambda item: item.capture_sha256,
    )
    body = {
        "package_version": HMAA_SESSION_PARTNER_REQUEST_VERSION,
        "request_status": "READY_FOR_PARTNER_VALIDATION_REQUEST",
        "mission_id": receipt.mission_id,
        "requested_scope": PARTNER_VALIDATION_SCOPE,
        "environment_endpoint": receipt.endpoint,
        "preflight_report_sha256": receipt.preflight_report_sha256,
        "session_receipt_sha256": receipt.receipt_sha256,
        "inner_request_package_sha256": inner_request.package_sha256,
        "attestation_aggregate_sha256": inner_request.attestation_aggregate_sha256,
        "qualifying_capture_count": inner_request.qualifying_capture_count,
        "evidence_references": [item.model_dump(mode="json") for item in references],
        "requested_checks": [
            "confirm the named Sandbox environment endpoint and access were authorized for this read-only validation session",
            "confirm the cited preflight report and session receipt hashes correspond to the session reviewed",
            "confirm the cited entity/task stream evidence originated from the named Sandbox environment",
            "confirm WS-HMAA requested no entity publication, task mutation, agent execution, manual-control, flight-control, or weapons action",
            "verify the inner request, aggregate attestation, capture, fixture, and evidence-chain SHA-256 references against the review evidence",
            "return an independently attributable external attestation bound to this session-partner request package SHA-256",
        ],
        "claimable_labels": [
            "IMPLEMENTED IN SOFTWARE",
            "REQUIRES PARTNER VALIDATION",
        ],
        "prohibited_claims": [
            "LIVE_ENVIRONMENT_VALIDATED",
            "PARTNER_VALIDATED",
            "FLIGHT_VALIDATED",
            "OPERATIONALLY_VALIDATED",
        ],
        "external_environment_provenance_confirmed": False,
        "live_environment_validated": False,
        "partner_validated": False,
        "flight_validated": False,
        "operationally_validated": False,
    }
    return HMAASessionPartnerValidationRequest(
        **body,
        package_sha256=_sha256_json(body),
    )


def canonical_session_partner_request_bytes(
    request: HMAASessionPartnerValidationRequest,
) -> bytes:
    body = request.model_dump(mode="json", exclude={"package_sha256"})
    if _sha256_json(body) != request.package_sha256:
        raise ValueError("session partner request package hash verification failed")
    return json.dumps(
        request.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def session_requested_check_digests(
    request: HMAASessionPartnerValidationRequest,
) -> list[str]:
    return sorted({_sha256_text(check) for check in request.requested_checks})


def assess_session_partner_attestation_response(
    request: HMAASessionPartnerValidationRequest,
    response: HMAAPartnerAttestationResponse,
    *,
    verifier: PartnerAttestationVerifier | None = None,
) -> HMAAPartnerAttestationAssessment:
    """Assess an external response bound to the v1.2 session envelope.

    The returned assessment intentionally reuses the existing v0.9 assessment
    type so the v1.0 human-acceptance gate remains the next mandatory step.
    """

    if response.request_package_sha256 != request.package_sha256:
        raise ValueError("partner response is not bound to this session request package")
    if response.mission_id != request.mission_id:
        raise ValueError("partner response mission_id does not match session request")
    if response.attested_scope != request.requested_scope:
        raise ValueError("partner response scope does not match session request")
    if expected_response_sha256(response) != response.response_sha256:
        raise ValueError("partner response hash verification failed")

    required_checks = set(session_requested_check_digests(request))
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
