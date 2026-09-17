from dataclasses import replace

import pytest

from security.qcrypto.applied_work_postwork import (
    AppliedWorkReceipt,
    WorkValidationState,
    apply_post_work_stake,
    rotate_pq_credential,
    run_bounded_post_work_proof,
    slash_position,
    stake_eligible,
    verify_post_work_preservation,
)


def receipt(**overrides):
    values = dict(
        work_id="work-1",
        contributor_id="contributor-1",
        evidence_digest="ab" * 32,
        validated_work_units=100,
        validation_state=WorkValidationState.PROVEN_INTERNALLY,
        evidence_retained=True,
        reproducible=True,
        safety_authorized=True,
        measurement_accessible=True,
        revoked=False,
    )
    values.update(overrides)
    return AppliedWorkReceipt(**values)


def test_only_validated_evidenced_work_is_stake_eligible():
    assert stake_eligible(receipt()) is True
    assert stake_eligible(receipt(validation_state=WorkValidationState.IMPLEMENTED_IN_SOFTWARE)) is False
    assert stake_eligible(receipt(evidence_retained=False)) is False
    assert stake_eligible(receipt(reproducible=False)) is False
    assert stake_eligible(receipt(safety_authorized=False)) is False
    assert stake_eligible(receipt(measurement_accessible=False)) is False
    assert stake_eligible(receipt(revoked=True)) is False


def test_post_work_stake_cannot_amplify_validated_work():
    r = receipt(validated_work_units=10)
    with pytest.raises(ValueError, match="cannot exceed"):
        apply_post_work_stake(r, consensus_domain="A", epoch=1, requested_stake_units=11)


def test_same_work_receipt_cannot_double_count_in_domain_epoch():
    r = receipt()
    p = apply_post_work_stake(r, consensus_domain="A", epoch=7, requested_stake_units=50)
    with pytest.raises(ValueError, match="already used"):
        apply_post_work_stake(
            r,
            consensus_domain="A",
            epoch=7,
            requested_stake_units=50,
            existing_positions=(p,),
        )


def test_same_receipt_can_be_reapplied_in_later_epoch_without_rewriting_work():
    r = receipt()
    p1 = apply_post_work_stake(r, consensus_domain="A", epoch=7, requested_stake_units=50)
    p2 = apply_post_work_stake(r, consensus_domain="A", epoch=8, requested_stake_units=50, existing_positions=(p1,))
    assert p1.evidence_digest == p2.evidence_digest == r.evidence_digest
    assert p1.work_id == p2.work_id == r.work_id


def test_slashing_changes_active_stake_not_work_proof():
    r = receipt()
    p = apply_post_work_stake(r, consensus_domain="A", epoch=1, requested_stake_units=80)
    s = slash_position(p, 20)
    verify_post_work_preservation(r, p, s)
    assert s.active_stake_units == 60
    assert s.slashed_units == 20
    assert s.evidence_digest == r.evidence_digest


def test_pq_rotation_changes_only_replaceable_credential():
    r = receipt()
    p = apply_post_work_stake(
        r,
        consensus_domain="A",
        epoch=1,
        requested_stake_units=80,
        pq_credential_id="pq-1",
    )
    q = rotate_pq_credential(p, "pq-2")
    verify_post_work_preservation(r, p, q)
    assert q.pq_credential_id == "pq-2"
    assert q.stake_units == p.stake_units
    assert q.evidence_digest == p.evidence_digest


def test_tampering_with_evidence_digest_is_rejected_by_preservation_check():
    r = receipt()
    p = apply_post_work_stake(r, consensus_domain="A", epoch=1, requested_stake_units=80)
    tampered = replace(p, evidence_digest="cd" * 32)
    with pytest.raises(ValueError, match="evidence_digest"):
        verify_post_work_preservation(r, p, tampered)


def test_bounded_proof_passes_and_preserves_claim_boundary():
    report = run_bounded_post_work_proof()
    assert report.status == "PASS"
    assert report.claim_state == "BOUNDED_MODEL_PROOF_OF_APPLIED_WORK_TO_POST_WORK_STAKE_PRESERVATION"
    assert report.receipts_checked == 128
    assert report.applications_checked == 6
    assert "economic valuation of applied work" in report.excluded_claims
    assert "production consensus security" in report.excluded_claims
