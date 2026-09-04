from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worldshepherd_sara.hmaa_human_acceptance import (
    HMAAHumanAcceptanceDecision,
    HumanAcceptanceAction,
    HumanAcceptanceState,
    record_human_acceptance,
    verify_human_acceptance_record,
)
from worldshepherd_sara.hmaa_partner_response import (
    HMAAPartnerAttestationAssessment,
    PartnerAttestationOutcome,
    PartnerAttestationState,
)


REQUEST_HASH = "sha256:" + "1" * 64
RESPONSE_HASH = "sha256:" + "2" * 64


def _assessment(
    *,
    state=PartnerAttestationState.VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE,
    outcome=PartnerAttestationOutcome.CONFIRMED,
    signature_verified=True,
    all_checks=True,
    partner_validated=False,
    live=False,
    flight=False,
    operational=False,
):
    return HMAAPartnerAttestationAssessment(
        state=state,
        request_package_sha256=REQUEST_HASH,
        response_sha256=RESPONSE_HASH,
        outcome=outcome,
        signature_verified=signature_verified,
        verifier_id="trusted-verifier-001",
        verifier_reason="external signature authenticated",
        all_requested_checks_confirmed=all_checks,
        human_acceptance_required=True,
        partner_validated=partner_validated,
        live_environment_validated=live,
        flight_validated=flight,
        operationally_validated=operational,
        claimable_labels=["IMPLEMENTED IN SOFTWARE", "REQUIRES PARTNER VALIDATION"],
        blocking_reasons=["human acceptance is required"],
    )


def _decision(action=HumanAcceptanceAction.ACCEPT):
    return HMAAHumanAcceptanceDecision(
        decision_id="decision-001",
        decision_by="authorized-human-reviewer",
        decided_at=datetime(2026, 9, 4, 23, 30, tzinfo=timezone.utc),
        action=action,
        rationale="Reviewed the authenticated evidence and scope boundaries.",
    )


def test_accept_records_partner_attestation_for_requested_scope_only():
    record = record_human_acceptance(_assessment(), _decision())

    assert record.state is HumanAcceptanceState.PARTNER_ATTESTATION_ACCEPTED_FOR_REQUESTED_SCOPE
    assert record.partner_attestation_accepted is True
    assert record.accepted_scope_limited_to_request is True
    assert record.partner_validated is False
    assert record.live_environment_validated is False
    assert record.flight_validated is False
    assert record.operationally_validated is False
    assert "PARTNER ATTESTATION ACCEPTED FOR REQUESTED SCOPE" in record.claimable_labels
    assert verify_human_acceptance_record(record) is True


def test_unverified_response_cannot_be_accepted():
    assessment = _assessment(
        state=PartnerAttestationState.UNVERIFIED_EXTERNAL_RESPONSE,
        signature_verified=False,
    )

    with pytest.raises(ValueError, match="verified CONFIRMED"):
        record_human_acceptance(assessment, _decision())


def test_partial_response_cannot_be_accepted():
    assessment = _assessment(
        state=PartnerAttestationState.VERIFIED_RESPONSE_REQUIRES_HUMAN_REVIEW,
        outcome=PartnerAttestationOutcome.PARTIAL,
        all_checks=False,
    )

    with pytest.raises(ValueError, match="verified CONFIRMED"):
        record_human_acceptance(assessment, _decision())


def test_preexisting_validation_claim_blocks_acceptance():
    assessment = _assessment(partner_validated=True)

    with pytest.raises(ValueError, match="preexisting validation claim"):
        record_human_acceptance(assessment, _decision())


def test_reject_is_recordable_without_promoting_claims():
    record = record_human_acceptance(
        _assessment(
            state=PartnerAttestationState.VERIFIED_RESPONSE_REJECTED,
            outcome=PartnerAttestationOutcome.REJECTED,
            all_checks=False,
        ),
        _decision(HumanAcceptanceAction.REJECT),
    )

    assert record.state is HumanAcceptanceState.PARTNER_ATTESTATION_REJECTED
    assert record.partner_attestation_accepted is False
    assert "REQUIRES PARTNER VALIDATION" in record.claimable_labels
    assert verify_human_acceptance_record(record) is True


def test_defer_is_recordable_for_unverified_response():
    record = record_human_acceptance(
        _assessment(
            state=PartnerAttestationState.UNVERIFIED_EXTERNAL_RESPONSE,
            signature_verified=False,
        ),
        _decision(HumanAcceptanceAction.DEFER),
    )

    assert record.state is HumanAcceptanceState.PARTNER_ATTESTATION_DEFERRED
    assert record.partner_attestation_accepted is False
    assert record.live_environment_validated is False
    assert verify_human_acceptance_record(record) is True


def test_accept_requires_complete_requested_check_coverage():
    assessment = _assessment(all_checks=False)

    with pytest.raises(ValueError, match="every requested check"):
        record_human_acceptance(assessment, _decision())


def test_accept_requires_signature_authentication():
    assessment = _assessment(signature_verified=False)

    with pytest.raises(ValueError, match="authenticated external signature"):
        record_human_acceptance(assessment, _decision())


def test_record_hash_detects_tampering():
    record = record_human_acceptance(_assessment(), _decision())
    tampered = record.model_copy(update={"rationale": "tampered rationale"})

    assert verify_human_acceptance_record(tampered) is False
