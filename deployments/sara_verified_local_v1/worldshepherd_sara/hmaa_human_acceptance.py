from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .hmaa_partner_response import (
    HMAAPartnerAttestationAssessment,
    PartnerAttestationOutcome,
    PartnerAttestationState,
)


HMAA_HUMAN_ACCEPTANCE_VERSION = "worldshepherd.hmaa.human-acceptance.v1.0"


class HumanAcceptanceAction(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    DEFER = "DEFER"


class HumanAcceptanceState(str, Enum):
    PARTNER_ATTESTATION_ACCEPTED_FOR_REQUESTED_SCOPE = (
        "PARTNER_ATTESTATION_ACCEPTED_FOR_REQUESTED_SCOPE"
    )
    PARTNER_ATTESTATION_REJECTED = "PARTNER_ATTESTATION_REJECTED"
    PARTNER_ATTESTATION_DEFERRED = "PARTNER_ATTESTATION_DEFERRED"


class HMAAHumanAcceptanceDecision(BaseModel):
    decision_id: str = Field(min_length=1, max_length=512)
    decision_by: str = Field(min_length=1, max_length=512)
    decided_at: datetime
    action: HumanAcceptanceAction
    rationale: str = Field(min_length=1, max_length=4096)


class HMAAHumanAcceptanceRecord(BaseModel):
    record_version: str = HMAA_HUMAN_ACCEPTANCE_VERSION
    state: HumanAcceptanceState
    decision_id: str
    decision_by: str
    decided_at: datetime
    action: HumanAcceptanceAction
    rationale: str
    request_package_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    response_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    verifier_id: str = Field(min_length=1, max_length=512)
    partner_attestation_accepted: bool = False
    accepted_scope_limited_to_request: bool = False
    partner_validated: bool = False
    live_environment_validated: bool = False
    flight_validated: bool = False
    operationally_validated: bool = False
    claimable_labels: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    record_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _acceptance_preconditions(assessment: HMAAPartnerAttestationAssessment) -> None:
    if assessment.state is not PartnerAttestationState.VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE:
        raise ValueError(
            "ACCEPT requires a verified CONFIRMED response awaiting human acceptance"
        )
    if not assessment.signature_verified:
        raise ValueError("ACCEPT requires authenticated external signature evidence")
    if assessment.outcome is not PartnerAttestationOutcome.CONFIRMED:
        raise ValueError("ACCEPT requires a CONFIRMED external outcome")
    if not assessment.all_requested_checks_confirmed:
        raise ValueError("ACCEPT requires every requested check to be confirmed")
    if not assessment.human_acceptance_required:
        raise ValueError("assessment does not require a human acceptance decision")
    if (
        assessment.partner_validated
        or assessment.live_environment_validated
        or assessment.flight_validated
        or assessment.operationally_validated
    ):
        raise ValueError("assessment contains a preexisting validation claim")


def record_human_acceptance(
    assessment: HMAAPartnerAttestationAssessment,
    decision: HMAAHumanAcceptanceDecision,
) -> HMAAHumanAcceptanceRecord:
    if decision.action is HumanAcceptanceAction.ACCEPT:
        _acceptance_preconditions(assessment)
        state = HumanAcceptanceState.PARTNER_ATTESTATION_ACCEPTED_FOR_REQUESTED_SCOPE
        partner_attestation_accepted = True
        scope_limited = True
        blocking = [
            "acceptance is limited to the partner attestation and requested scope",
            "live-environment, flight, and operational validation require separate evidence",
        ]
        claimable = [
            "IMPLEMENTED IN SOFTWARE",
            "PARTNER ATTESTATION ACCEPTED FOR REQUESTED SCOPE",
        ]
    elif decision.action is HumanAcceptanceAction.REJECT:
        state = HumanAcceptanceState.PARTNER_ATTESTATION_REJECTED
        partner_attestation_accepted = False
        scope_limited = False
        blocking = ["human reviewer rejected the partner attestation"]
        claimable = ["IMPLEMENTED IN SOFTWARE", "REQUIRES PARTNER VALIDATION"]
    else:
        state = HumanAcceptanceState.PARTNER_ATTESTATION_DEFERRED
        partner_attestation_accepted = False
        scope_limited = False
        blocking = ["human acceptance decision is deferred"]
        claimable = ["IMPLEMENTED IN SOFTWARE", "REQUIRES PARTNER VALIDATION"]

    body = {
        "record_version": HMAA_HUMAN_ACCEPTANCE_VERSION,
        "state": state.value,
        "decision_id": decision.decision_id,
        "decision_by": decision.decision_by,
        "decided_at": decision.decided_at.isoformat(),
        "action": decision.action.value,
        "rationale": decision.rationale,
        "request_package_sha256": assessment.request_package_sha256,
        "response_sha256": assessment.response_sha256,
        "verifier_id": assessment.verifier_id,
        "partner_attestation_accepted": partner_attestation_accepted,
        "accepted_scope_limited_to_request": scope_limited,
        "partner_validated": False,
        "live_environment_validated": False,
        "flight_validated": False,
        "operationally_validated": False,
        "claimable_labels": claimable,
        "blocking_reasons": blocking,
    }
    return HMAAHumanAcceptanceRecord(
        **body,
        record_sha256=_sha256_json(body),
    )


def verify_human_acceptance_record(record: HMAAHumanAcceptanceRecord) -> bool:
    body = record.model_dump(mode="json", exclude={"record_sha256"})
    return _sha256_json(body) == record.record_sha256
