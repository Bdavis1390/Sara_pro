from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worldshepherd_sara.hmaa_authorized_session import (
    HMAAAuthorizedReadSessionRequest,
    run_authorized_read_session,
)
from worldshepherd_sara.hmaa_human_acceptance import (
    HMAAHumanAcceptanceDecision,
    HumanAcceptanceAction,
    HumanAcceptanceState,
    record_human_acceptance,
)
from worldshepherd_sara.hmaa_lattice_capture import SandboxReadCapturePlan
from worldshepherd_sara.hmaa_partner_response import (
    ExternalSignature,
    HMAAPartnerAttestationResponse,
    PartnerAttestationOutcome,
    PartnerAttestationState,
    PartnerSignatureVerification,
    expected_response_sha256,
)
from worldshepherd_sara.hmaa_session_partner import (
    assess_session_partner_attestation_response,
    canonical_session_partner_request_bytes,
    session_requested_check_digests,
)


ENDPOINT = "https://partner-session.env.sandboxes.developer.anduril.com"


def _env():
    return {
        "LATTICE_ENDPOINT": ENDPOINT,
        "ENVIRONMENT_TOKEN": "static-test-token",
        "LATTICE_CLIENT_ID": None,
        "LATTICE_CLIENT_SECRET": None,
        "SANDBOXES_TOKEN": "sandbox-test-token",
    }


class _DistinctTransport:
    def __init__(self) -> None:
        self.calls = 0

    def stream_entities(self, request):
        self.calls += 1
        yield {
            "heartbeat": {
                "timestamp": f"2026-09-14T20:00:0{self.calls}Z",
                "sequence": self.calls,
            }
        }

    def stream_tasks(self, request):
        if False:
            yield {}


def _session_request():
    return HMAAAuthorizedReadSessionRequest(
        mission_id="SESSION-PARTNER-001",
        authorization_confirmed=True,
        capture_attempts=3,
        capture_plan=SandboxReadCapturePlan(
            max_entity_messages=1,
            max_task_messages=0,
        ),
    )


def _envelope():
    transport = _DistinctTransport()
    run = run_authorized_read_session(
        _session_request(),
        env=_env(),
        transport_factory=lambda report, env: transport,
    )
    assert run.partner_validation_envelope is not None
    return run.partner_validation_envelope, run


def _response(request, *, package_sha256: str | None = None):
    response = HMAAPartnerAttestationResponse(
        request_package_sha256=package_sha256 or request.package_sha256,
        mission_id=request.mission_id,
        attested_scope=request.requested_scope,
        organization_id="authorized-review-org",
        reviewer_id="reviewer-session-001",
        attested_at=datetime(2026, 9, 14, 20, 10, tzinfo=timezone.utc),
        outcome=PartnerAttestationOutcome.CONFIRMED,
        confirmed_check_sha256=session_requested_check_digests(request),
        evidence_references=["review-case:session-001"],
        signature=ExternalSignature(
            algorithm="external-verifier-test",
            key_id="session-partner-key-001",
            value="test-signature-not-production-crypto",
        ),
        response_sha256="sha256:" + "0" * 64,
    )
    return response.model_copy(
        update={"response_sha256": expected_response_sha256(response)}
    )


class _VerifiedTestVerifier:
    def verify(self, *, canonical_payload: bytes, signature: ExternalSignature):
        assert canonical_payload
        assert signature.key_id == "session-partner-key-001"
        return PartnerSignatureVerification(
            verified=True,
            verifier_id="session-test-verifier",
            reason="test fixture authenticated the response",
        )


def test_session_partner_request_binds_endpoint_preflight_receipt_and_inner_request():
    request, run = _envelope()

    assert canonical_session_partner_request_bytes(request)
    assert request.environment_endpoint == ENDPOINT
    assert request.preflight_report_sha256 == run.preflight.report_sha256
    assert request.session_receipt_sha256 == run.receipt.receipt_sha256
    assert request.inner_request_package_sha256 == run.partner_validation_request.package_sha256
    assert request.attestation_aggregate_sha256 == run.attestation.aggregate_sha256
    assert request.external_environment_provenance_confirmed is False
    assert request.live_environment_validated is False


def test_external_confirmation_binds_to_session_envelope_then_requires_human_acceptance():
    request, _ = _envelope()
    response = _response(request)
    assessment = assess_session_partner_attestation_response(
        request,
        response,
        verifier=_VerifiedTestVerifier(),
    )

    assert assessment.request_package_sha256 == request.package_sha256
    assert assessment.state is PartnerAttestationState.VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE
    assert assessment.signature_verified is True
    assert assessment.all_requested_checks_confirmed is True
    assert assessment.partner_validated is False
    assert assessment.live_environment_validated is False

    decision = HMAAHumanAcceptanceDecision(
        decision_id="human-session-acceptance-001",
        decision_by="CRE1AWS-test-reviewer",
        decided_at=datetime(2026, 9, 14, 20, 15, tzinfo=timezone.utc),
        action=HumanAcceptanceAction.ACCEPT,
        rationale="accept only the authenticated read-only Sandbox attestation scope",
    )
    record = record_human_acceptance(assessment, decision)

    assert record.state is HumanAcceptanceState.PARTNER_ATTESTATION_ACCEPTED_FOR_REQUESTED_SCOPE
    assert record.request_package_sha256 == request.package_sha256
    assert record.partner_attestation_accepted is True
    assert record.accepted_scope_limited_to_request is True
    assert record.partner_validated is False
    assert record.live_environment_validated is False
    assert record.flight_validated is False
    assert record.operationally_validated is False


def test_response_bound_only_to_inner_v08_request_is_rejected():
    request, run = _envelope()
    response = _response(
        request,
        package_sha256=run.partner_validation_request.package_sha256,
    )

    with pytest.raises(ValueError, match="not bound to this session request"):
        assess_session_partner_attestation_response(
            request,
            response,
            verifier=_VerifiedTestVerifier(),
        )


def test_tampered_environment_endpoint_invalidates_request_before_response_verification():
    request, _ = _envelope()
    tampered = request.model_copy(
        update={"environment_endpoint": "https://other.env.sandboxes.developer.anduril.com"}
    )

    with pytest.raises(ValueError, match="package hash verification failed"):
        assess_session_partner_attestation_response(
            tampered,
            _response(request),
            verifier=_VerifiedTestVerifier(),
        )


def test_default_external_verifier_stays_fail_closed():
    request, _ = _envelope()
    assessment = assess_session_partner_attestation_response(request, _response(request))

    assert assessment.state is PartnerAttestationState.UNVERIFIED_EXTERNAL_RESPONSE
    assert assessment.signature_verified is False
    assert assessment.partner_validated is False
    assert assessment.live_environment_validated is False
