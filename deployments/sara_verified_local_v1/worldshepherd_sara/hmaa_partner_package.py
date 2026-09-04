from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from .hmaa_attestation import HMAAAttestationReport, HMAAAttestationState


HMAA_PARTNER_REQUEST_VERSION = "worldshepherd.hmaa.partner-validation-request.v0.8"
PARTNER_VALIDATION_SCOPE = "read-only-sandbox-interoperability"


class HMAAPartnerEvidenceReference(BaseModel):
    capture_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    fixture_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    final_chain_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    event_count: int = Field(gt=0)


class HMAAPartnerValidationRequest(BaseModel):
    package_version: str = HMAA_PARTNER_REQUEST_VERSION
    request_status: str = "READY_FOR_PARTNER_VALIDATION_REQUEST"
    mission_id: str = Field(min_length=1)
    requested_scope: str = PARTNER_VALIDATION_SCOPE
    attestation_aggregate_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    qualifying_capture_count: int = Field(ge=3)
    evidence_references: list[HMAAPartnerEvidenceReference]
    requested_checks: list[str]
    claimable_labels: list[str]
    prohibited_claims: list[str]
    live_environment_validated: bool = False
    package_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _request_body(report: HMAAAttestationReport) -> dict[str, Any]:
    if report.live_environment_validated:
        raise ValueError("partner request cannot be built from a live-validation claim")
    if report.state is not HMAAAttestationState.EXTERNAL_ATTESTATION_REQUIRED:
        raise ValueError(
            "partner request requires an EXTERNAL_ATTESTATION_REQUIRED report"
        )
    if not report.repeatability_satisfied:
        raise ValueError("partner request requires repeatability-qualified evidence")
    if not report.external_attestation_required:
        raise ValueError("partner request requires external attestation to remain pending")
    if report.aggregate_sha256 is None:
        raise ValueError("partner request requires an aggregate attestation digest")
    if not report.mission_id:
        raise ValueError("partner request requires a mission_id")

    distinct = {capture.capture_sha256 for capture in report.captures}
    if len(distinct) != report.distinct_capture_count:
        raise ValueError("attestation distinct-capture count is inconsistent")
    if report.distinct_capture_count < 3:
        raise ValueError("partner request requires at least three distinct captures")

    references = [
        HMAAPartnerEvidenceReference(
            capture_sha256=capture.capture_sha256,
            fixture_sha256=capture.fixture_sha256,
            final_chain_hash=capture.final_chain_hash,
            event_count=capture.event_count,
        )
        for capture in report.captures
    ]
    references.sort(key=lambda item: item.capture_sha256)

    return {
        "package_version": HMAA_PARTNER_REQUEST_VERSION,
        "request_status": "READY_FOR_PARTNER_VALIDATION_REQUEST",
        "mission_id": report.mission_id,
        "requested_scope": PARTNER_VALIDATION_SCOPE,
        "attestation_aggregate_sha256": report.aggregate_sha256,
        "qualifying_capture_count": report.distinct_capture_count,
        "evidence_references": [
            reference.model_dump(mode="json") for reference in references
        ],
        "requested_checks": [
            "confirm the cited environment and access were authorized for read-only validation",
            "confirm the cited entity/task stream evidence originated from the stated environment",
            "confirm no publish, task mutation, manual-control, flight-control, or weapons action was requested by WS-HMAA",
            "verify the supplied capture and aggregate SHA-256 references against the review evidence",
            "return an independently attributable partner attestation bound to this package SHA-256",
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
        "live_environment_validated": False,
    }


def build_partner_validation_request(
    report: HMAAAttestationReport,
) -> HMAAPartnerValidationRequest:
    body = _request_body(report)
    return HMAAPartnerValidationRequest(
        **body,
        package_sha256=_sha256_json(body),
    )


def canonical_partner_request_bytes(request: HMAAPartnerValidationRequest) -> bytes:
    body = request.model_dump(mode="json", exclude={"package_sha256"})
    expected = _sha256_json(body)
    if expected != request.package_sha256:
        raise ValueError("partner validation request package hash verification failed")
    return json.dumps(
        request.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
