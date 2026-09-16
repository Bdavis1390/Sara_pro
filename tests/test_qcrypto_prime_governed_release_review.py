from copy import deepcopy

from security.qcrypto.prime_governed_release_review import (
    assess_prime_governed_release_review,
)


def prime_evidence(**overrides):
    data = {
        "schema": "WS-PRIME-SENTINEL-TWO-CONTAINER-INTEGRATION-V3",
        "status": "PASS",
        "signing_algorithm": "ML-DSA-65",
        "signature_context": "WS-PRIME-SENTINEL-AUTHZ-V2",
        "post_quantum_signature_protection": True,
        "same_request_retry_identical_before_restart": True,
        "same_request_retry_identical_after_restart": True,
        "conflicting_request_rejected_http_status": 409,
        "assertion_replay_rejected_http_status": 403,
        "activation_disposition": "ACTIVATION_ALLOWED",
        "authorization_registry_status": "CONSUMED",
        "end_to_end_pq_security_established": False,
        "claims_boundary": "bounded integration evidence only",
    }
    data.update(overrides)
    return data


def governed_evidence(**summary_overrides):
    summary = {
        "terminal_state": "HUMAN_REVIEW_REQUIRED",
        "ready_for_human_review": True,
        "human_approval_required": True,
        "human_approval_recorded": False,
        "replay_checkpoint_bound": True,
        "compatible_probe_count": 2,
        "verified_compatible_probe_count": 2,
        "execution_authority": False,
        "live_value_authorized": False,
        "live_transaction_signed": False,
        "production_protocol_integration": False,
        "end_to_end_pq_security_established": False,
    }
    summary.update(summary_overrides)
    return {
        "schema": "WS-QCRYPTO-GOVERNED-PQ-SIGNING-STATE-EVIDENCE-V1",
        "status": "PASS",
        "claim_state": "GOVERNED_PQ_SIGNING_READINESS_PROVEN_IN_CI",
        "proof_scope": "EPHEMERAL_ZERO_VALUE_PRE_APPROVAL_ONLY",
        "complete_path": {
            "state": "HUMAN_REVIEW_REQUIRED",
            "ready_for_human_review": True,
            "selected_suite_id": "HYBRID-ECDSA-MLDSA",
            "pq_algorithm_id": "ML-DSA",
            "negotiated_context_digest": "a" * 64,
            "negotiation_transcript_digest": "b" * 64,
            "verified_compatible_probe_count": 2,
            "human_approval_recorded": False,
            "execution_authority": False,
            "live_value_authorized": False,
        },
        "summary": summary,
        "evidence_sha256": "c" * 64,
    }


def test_valid_independent_evidence_lanes_bind_to_human_review_only():
    result = assess_prime_governed_release_review(prime_evidence(), governed_evidence())
    assert result.verdict == "PRIME_GOVERNED_RELEASE_READY_FOR_HUMAN_REVIEW"
    assert result.ready_for_human_release_review is True
    assert len(result.prime_evidence_sha256) == 64
    assert len(result.governed_evidence_sha256) == 64
    assert result.review_package_sha256 is not None
    assert len(result.review_package_sha256) == 64
    assert result.human_release_required is True
    assert result.human_release_recorded is False
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.live_transaction_signed is False
    assert result.production_protocol_integration is False
    assert result.end_to_end_pq_security_established is False
    assert any("ACTIVATION_ALLOWED" in warning for warning in result.warnings)


def test_prime_algorithm_mismatch_blocks_cross_boundary_review():
    result = assess_prime_governed_release_review(
        prime_evidence(signing_algorithm="Ed25519"), governed_evidence()
    )
    assert result.ready_for_human_release_review is False
    assert result.review_package_sha256 is None
    assert any("not ML-DSA-65" in blocker for blocker in result.blockers)


def test_prime_replay_control_failure_blocks_cross_boundary_review():
    result = assess_prime_governed_release_review(
        prime_evidence(assertion_replay_rejected_http_status=200), governed_evidence()
    )
    assert result.ready_for_human_release_review is False
    assert any("replay rejection" in blocker for blocker in result.blockers)


def test_prime_end_to_end_pq_claim_fails_closed():
    result = assess_prime_governed_release_review(
        prime_evidence(end_to_end_pq_security_established=True), governed_evidence()
    )
    assert result.ready_for_human_release_review is False
    assert any("end-to-end PQ security" in blocker for blocker in result.blockers)


def test_governed_lane_cannot_skip_human_review():
    result = assess_prime_governed_release_review(
        prime_evidence(), governed_evidence(terminal_state="EXECUTION_ALLOWED")
    )
    assert result.ready_for_human_release_review is False
    assert result.execution_authority is False
    assert result.review_package_sha256 is None


def test_recorded_human_approval_is_not_accepted_by_preapproval_bridge():
    result = assess_prime_governed_release_review(
        prime_evidence(), governed_evidence(human_approval_recorded=True)
    )
    assert result.ready_for_human_release_review is False
    assert any("unexpectedly records human approval" in blocker for blocker in result.blockers)


def test_execution_or_live_value_assertion_blocks_bridge():
    for field in ("execution_authority", "live_value_authorized", "live_transaction_signed"):
        result = assess_prime_governed_release_review(
            prime_evidence(), governed_evidence(**{field: True})
        )
        assert result.ready_for_human_release_review is False
        assert any(field in blocker for blocker in result.blockers)


def test_pq_algorithm_family_must_match_prime_mldsa65():
    evidence = governed_evidence()
    evidence["complete_path"]["pq_algorithm_id"] = "SLH-DSA"
    evidence["complete_path"]["selected_suite_id"] = "PQ-SLHDSA"
    result = assess_prime_governed_release_review(prime_evidence(), evidence)
    assert result.ready_for_human_release_review is False
    assert any("does not match PRIME ML-DSA-65" in blocker for blocker in result.blockers)


def test_review_package_digest_changes_if_valid_evidence_changes():
    left_prime = prime_evidence(evidence_instance="one")
    right_prime = deepcopy(left_prime)
    right_prime["evidence_instance"] = "two"
    left = assess_prime_governed_release_review(left_prime, governed_evidence())
    right = assess_prime_governed_release_review(right_prime, governed_evidence())
    assert left.ready_for_human_release_review is True
    assert right.ready_for_human_release_review is True
    assert left.prime_evidence_sha256 != right.prime_evidence_sha256
    assert left.review_package_sha256 != right.review_package_sha256


def test_missing_verified_compatible_probe_blocks_review():
    evidence = governed_evidence()
    evidence["complete_path"]["verified_compatible_probe_count"] = 0
    result = assess_prime_governed_release_review(prime_evidence(), evidence)
    assert result.ready_for_human_release_review is False
    assert any("no verified compatible PQ reference probe" in blocker for blocker in result.blockers)
