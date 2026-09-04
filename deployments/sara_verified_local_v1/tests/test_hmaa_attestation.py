from __future__ import annotations

import pytest

from worldshepherd_sara.hmaa_attestation import (
    HMAAAttestationState,
    attest_candidate_captures,
)
from worldshepherd_sara.hmaa_interop import run_public_contract_replay
from worldshepherd_sara.hmaa_lattice_capture import SandboxReadCaptureResult


def _capture(sequence: int, *, mission_id: str = "ATTEST-MISSION-001") -> SandboxReadCaptureResult:
    timestamp = f"2026-09-04T22:5{sequence}:00Z"
    interop = run_public_contract_replay(
        mission_id=mission_id,
        source_label="authorized-sandbox-readonly-candidate",
        items=[
            {
                "stream": "entities",
                "message": {
                    "heartbeat": {
                        "timestamp": timestamp,
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


def test_empty_evidence_stays_unvalidated():
    report = attest_candidate_captures([])

    assert report.state is HMAAAttestationState.NO_EVIDENCE
    assert report.live_environment_validated is False
    assert report.external_attestation_required is True
    assert report.repeatability_satisfied is False
    assert report.aggregate_sha256 is None


def test_single_capture_is_candidate_only():
    report = attest_candidate_captures([_capture(1)])

    assert report.state is HMAAAttestationState.CANDIDATE_EVIDENCE
    assert report.capture_count == 1
    assert report.distinct_capture_count == 1
    assert report.repeatability_satisfied is False
    assert report.live_environment_validated is False
    assert "REQUIRES PARTNER VALIDATION" in report.claimable_labels
    assert "PROVEN INTERNALLY" not in report.claimable_labels


def test_three_distinct_captures_require_external_attestation_not_live_claim():
    report = attest_candidate_captures([_capture(1), _capture(2), _capture(3)])

    assert report.state is HMAAAttestationState.EXTERNAL_ATTESTATION_REQUIRED
    assert report.capture_count == 3
    assert report.distinct_capture_count == 3
    assert report.repeatability_satisfied is True
    assert report.live_environment_validated is False
    assert report.external_attestation_required is True
    assert report.aggregate_sha256 is not None
    assert any("external/partner" in reason for reason in report.blocking_reasons)


def test_duplicate_capture_does_not_satisfy_repeatability():
    first = _capture(1)
    report = attest_candidate_captures([first, first, _capture(2)])

    assert report.capture_count == 3
    assert report.distinct_capture_count == 2
    assert report.repeatability_satisfied is False
    assert report.state is HMAAAttestationState.CANDIDATE_EVIDENCE


def test_aggregate_digest_is_order_independent():
    captures = [_capture(1), _capture(2), _capture(3)]
    forward = attest_candidate_captures(captures)
    reverse = attest_candidate_captures(list(reversed(captures)))

    assert forward.aggregate_sha256 == reverse.aggregate_sha256
    assert [item.capture_sha256 for item in forward.captures] == [
        item.capture_sha256 for item in reverse.captures
    ]


def test_mission_mismatch_is_rejected():
    with pytest.raises(ValueError, match="same mission_id"):
        attest_candidate_captures(
            [_capture(1, mission_id="A"), _capture(2, mission_id="B")]
        )


def test_candidate_layer_rejects_any_preexisting_live_validation_claim():
    candidate = _capture(1)
    asserted_live = candidate.model_copy(update={"live_environment_validated": True})

    with pytest.raises(ValueError, match="must not assert live-environment validation"):
        attest_candidate_captures([asserted_live])


def test_non_allow_capture_requires_review_and_cannot_qualify():
    candidate = _capture(1)
    manifest = candidate.interop.manifest.model_copy(
        update={"disposition_counts": {"REVIEW": 1}}
    )
    interop = candidate.interop.model_copy(update={"manifest": manifest})
    needs_review = candidate.model_copy(update={"interop": interop})

    with pytest.raises(ValueError, match="non-ALLOW"):
        attest_candidate_captures([needs_review])


def test_manifest_count_must_match_finite_capture_count():
    candidate = _capture(1)
    manifest = candidate.interop.manifest.model_copy(update={"event_count": 2})
    interop = candidate.interop.model_copy(update={"manifest": manifest})
    inconsistent = candidate.model_copy(update={"interop": interop})

    with pytest.raises(ValueError, match="does not match sampled message count"):
        attest_candidate_captures([inconsistent])
