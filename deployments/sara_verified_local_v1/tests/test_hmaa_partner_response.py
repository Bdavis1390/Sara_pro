from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worldshepherd_sara.hmaa_attestation import attest_candidate_captures
from worldshepherd_sara.hmaa_interop import run_public_contract_replay
from worldshepherd_sara.hmaa_lattice_capture import SandboxReadCaptureResult
from worldshepherd_sara.hmaa_partner_package import build_partner_validation_request
from worldshepherd_sara.hmaa_partner_response import (
    ExternalSignature,
    HMAAPartnerAttestationResponse,
    PartnerAttestationOutcome,
    PartnerAttestationState,
    PartnerSignatureVerification,
    assess_partner_attestation_response,
    canonical_unsigned_response_bytes,
    expected_response_sha256,
    requested_check_digests,
)


def _capture(sequence: int) -> SandboxReadCaptureResult:
    interop = run_public_contract_replay(
        mission_id="PARTNER-RESPONSE-001",
        source_label="authorized-sandbox-readonly-candidate",
        items=[
            {
                "stream": "entities",
                "message": {
                    "heartbeat": {
                        "timestamp": f"2026-09-04T23:1{sequence}:00Z",
                        "sequence": sequence,
                    }
                },
            }
        ],
    )
    return SandboxReadCaptureResult(
        live_environment_validated=False,
        source_label="authorized-sandbox-readonly-candidate",
        captured_entity_messages=1,
        captured_task_messages=0,
        interop=interop,
    )


def _request():
    report = attest_candidate_captures([_capture(1), _capture(2), _capture(3)])
    return build_partner_validation_request(report)


def _response(request, *, outcome=PartnerAttestationOutcome.CONFIRMED, checks=None):
    if checks is None:
        checks = requested_check_digests(request) if outcome is not PartnerAttestationOutcome.REJECTED else []
    response = HMAAPartnerAttestationResponse(
        request_package_sha256=request.package_sha256,
        mission_id=request.mission_id,
        attested_scope=request.requested_scope,
        organization_id="example-partner-org",
        reviewer_id="reviewer-001",
        attested_at=datetime(2026, 9, 4, 23, 20, tzinfo=timezone.utc),
        outcome=outcome,
        confirmed_check_sha256=checks,
        evidence_references=["partner-evidence:case-001"],
        signature=ExternalSignature(
            algorithm="external-verifier-test",
            key_id="partner-key-001",
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
        assert signature.key_id == "partner-key-001"
        return PartnerSignatureVerification(
            verified=True,
            verifier_id="test-verifier",
            reason="test fixture authenticated the external response",
        )


class _RejectedTestVerifier:
    def verify(self, *, canonical_payload: bytes, signature: ExternalSignature):
        assert canonical_payload
        return PartnerSignatureVerification(
            verified=False,
            verifier_id="test-verifier",
            reason="signature authentication failed",
        )


def test_default_verifier_fails_closed_without_promoting_claims():
    request = _request()
    assessment = assess_partner_attestation_response(request, _response(request))

    assert assessment.state is PartnerAttestationState.UNVERIFIED_EXTERNAL_RESPONSE
    assert assessment.signature_verified is False
    assert assessment.partner_validated is False
    assert assessment.live_environment_validated is False
    assert assessment.flight_validated is False
    assert assessment.operationally_validated is False


def test_authenticated_confirmation_requires_human_acceptance_and_still_sets_no_validation_flag():
    request = _request()
    assessment = assess_partner_attestation_response(
        request,
        _response(request),
        verifier=_VerifiedTestVerifier(),
    )

    assert assessment.state is PartnerAttestationState.VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE
    assert assessment.signature_verified is True
    assert assessment.all_requested_checks_confirmed is True
    assert assessment.human_acceptance_required is True
    assert assessment.partner_validated is False
    assert assessment.live_environment_validated is False
    assert "REQUIRES PARTNER VALIDATION" in assessment.claimable_labels


def test_partial_authenticated_response_requires_human_review():
    request = _request()
    subset = requested_check_digests(request)[:2]
    assessment = assess_partner_attestation_response(
        request,
        _response(request, outcome=PartnerAttestationOutcome.PARTIAL, checks=subset),
        verifier=_VerifiedTestVerifier(),
    )

    assert assessment.state is PartnerAttestationState.VERIFIED_RESPONSE_REQUIRES_HUMAN_REVIEW
    assert assessment.all_requested_checks_confirmed is False
    assert assessment.partner_validated is False


def test_authenticated_rejection_is_preserved_as_rejected_not_validated():
    request = _request()
    assessment = assess_partner_attestation_response(
        request,
        _response(request, outcome=PartnerAttestationOutcome.REJECTED, checks=[]),
        verifier=_VerifiedTestVerifier(),
    )

    assert assessment.state is PartnerAttestationState.VERIFIED_RESPONSE_REJECTED
    assert assessment.signature_verified is True
    assert assessment.partner_validated is False
    assert assessment.live_environment_validated is False


def test_explicit_failed_verifier_stays_unverified():
    request = _request()
    assessment = assess_partner_attestation_response(
        request,
        _response(request),
        verifier=_RejectedTestVerifier(),
    )

    assert assessment.state is PartnerAttestationState.UNVERIFIED_EXTERNAL_RESPONSE
    assert assessment.signature_verified is False
    assert assessment.verifier_reason == "signature authentication failed"


def test_response_must_bind_to_exact_request_hash_mission_and_scope():
    request = _request()
    response = _response(request)

    wrong_hash = response.model_copy(update={"request_package_sha256": "sha256:" + "1" * 64})
    with pytest.raises(ValueError, match="not bound"):
        assess_partner_attestation_response(request, wrong_hash)

    wrong_mission = response.model_copy(update={"mission_id": "OTHER"})
    with pytest.raises(ValueError, match="mission_id"):
        assess_partner_attestation_response(request, wrong_mission)

    wrong_scope = response.model_copy(update={"attested_scope": "other-scope"})
    with pytest.raises(ValueError, match="scope"):
        assess_partner_attestation_response(request, wrong_scope)


def test_response_hash_detects_tampering_before_signature_verification():
    request = _request()
    response = _response(request)
    tampered = response.model_copy(update={"reviewer_id": "tampered-reviewer"})

    with pytest.raises(ValueError, match="hash verification failed"):
        assess_partner_attestation_response(
            request,
            tampered,
            verifier=_VerifiedTestVerifier(),
        )


def test_confirmed_response_must_cover_every_requested_check():
    request = _request()
    incomplete = _response(
        request,
        outcome=PartnerAttestationOutcome.CONFIRMED,
        checks=requested_check_digests(request)[:-1],
    )

    with pytest.raises(ValueError, match="every requested check"):
        assess_partner_attestation_response(request, incomplete)


def test_unknown_check_reference_is_rejected():
    request = _request()
    unknown = "sha256:" + "f" * 64
    response = _response(
        request,
        outcome=PartnerAttestationOutcome.PARTIAL,
        checks=[unknown],
    )

    with pytest.raises(ValueError, match="unknown requested-check"):
        assess_partner_attestation_response(request, response)


def test_rejected_response_cannot_simultaneously_confirm_checks():
    request = _request()
    response = _response(
        request,
        outcome=PartnerAttestationOutcome.REJECTED,
        checks=requested_check_digests(request)[:1],
    )

    with pytest.raises(ValueError, match="must not claim confirmed"):
        assess_partner_attestation_response(request, response)


def test_signature_is_not_inside_canonical_unsigned_payload():
    request = _request()
    response = _response(request)
    payload = canonical_unsigned_response_bytes(response)

    assert b"test-signature-not-production-crypto" not in payload
    assert b"response_sha256" not in payload
    assert request.package_sha256.encode("utf-8") in payload
