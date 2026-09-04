from __future__ import annotations

import pytest

from worldshepherd_sara.hmaa_attestation import attest_candidate_captures
from worldshepherd_sara.hmaa_interop import run_public_contract_replay
from worldshepherd_sara.hmaa_lattice_capture import SandboxReadCaptureResult
from worldshepherd_sara.hmaa_partner_package import (
    PARTNER_VALIDATION_SCOPE,
    build_partner_validation_request,
    canonical_partner_request_bytes,
)


def _capture(sequence: int) -> SandboxReadCaptureResult:
    interop = run_public_contract_replay(
        mission_id="PARTNER-PACKAGE-001",
        source_label="authorized-sandbox-readonly-candidate",
        items=[
            {
                "stream": "entities",
                "message": {
                    "heartbeat": {
                        "timestamp": f"2026-09-04T23:0{sequence}:00Z",
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


def _repeatable_report():
    return attest_candidate_captures([_capture(1), _capture(2), _capture(3)])


def test_repeatable_attestation_builds_partner_request_without_promoting_claims():
    request = build_partner_validation_request(_repeatable_report())

    assert request.request_status == "READY_FOR_PARTNER_VALIDATION_REQUEST"
    assert request.requested_scope == PARTNER_VALIDATION_SCOPE
    assert request.qualifying_capture_count == 3
    assert request.live_environment_validated is False
    assert "REQUIRES PARTNER VALIDATION" in request.claimable_labels
    assert "PARTNER_VALIDATED" in request.prohibited_claims
    assert "LIVE_ENVIRONMENT_VALIDATED" in request.prohibited_claims
    assert request.package_sha256.startswith("sha256:")


def test_candidate_only_evidence_cannot_build_partner_request():
    candidate = attest_candidate_captures([_capture(1)])

    with pytest.raises(ValueError, match="EXTERNAL_ATTESTATION_REQUIRED"):
        build_partner_validation_request(candidate)


def test_partner_request_is_deterministic_for_same_attestation():
    report = _repeatable_report()
    first = build_partner_validation_request(report)
    second = build_partner_validation_request(report)

    assert first.package_sha256 == second.package_sha256
    assert canonical_partner_request_bytes(first) == canonical_partner_request_bytes(second)


def test_partner_request_exports_references_not_raw_stream_payloads_or_credentials():
    request = build_partner_validation_request(_repeatable_report())
    encoded = canonical_partner_request_bytes(request)

    assert b"heartbeat" not in encoded
    assert b"access_token" not in encoded
    assert b"client_secret" not in encoded
    assert b"SANDBOXES_TOKEN" not in encoded
    assert len(request.evidence_references) == 3
    assert all(reference.capture_sha256.startswith("sha256:") for reference in request.evidence_references)


def test_tampered_package_hash_is_rejected_on_canonical_export():
    request = build_partner_validation_request(_repeatable_report())
    tampered = request.model_copy(update={"package_sha256": "sha256:" + "0" * 64})

    with pytest.raises(ValueError, match="hash verification failed"):
        canonical_partner_request_bytes(tampered)


def test_inconsistent_distinct_capture_count_is_rejected():
    report = _repeatable_report().model_copy(update={"distinct_capture_count": 4})

    with pytest.raises(ValueError, match="distinct-capture count is inconsistent"):
        build_partner_validation_request(report)


def test_preexisting_live_claim_is_rejected():
    report = _repeatable_report().model_copy(update={"live_environment_validated": True})

    with pytest.raises(ValueError, match="live-validation claim"):
        build_partner_validation_request(report)
