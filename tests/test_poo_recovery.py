from dataclasses import replace

import pytest

from security.poo.ownership_guard import evaluate_ownership
from security.poo.recovery_guard import (
    RecoveryEvidence,
    derive_recovery_ownership_candidate,
    evaluate_recovery,
    recovery_digest,
)


def valid_recovery():
    return RecoveryEvidence(
        asset_id="asset:alpha",
        prior_poo_digest="prior-poo-digest-002",
        claimant_id="claimant:one",
        recovery_reason="COMPROMISED_CONTROL",
        title_reference="title:ref:001",
        new_control_key_fingerprint="key:new789",
        recovery_work_reference="work:recovery:001",
        recovery_concept_reference="concept:recovery:001",
        recovery_stake_reference="stake:recovery:001",
        recovery_request_reference="recovery:req:001",
        issued_at="2026-09-16T01:00:00Z",
        expires_at="2026-09-17T01:00:00Z",
        prior_poo_valid=True,
        asset_continuity_verified=True,
        claimant_continuity_verified=True,
        claimant_identity_reverified=True,
        title_or_provenance_reverified=True,
        compromise_or_loss_evidence_bound=True,
        recovery_pow_verified=True,
        recovery_poc_concept_verified=True,
        alternate_control_or_custody_verified=True,
        recovery_pos_bond_verified=True,
        multisource_or_quorum_verified=True,
        freshness_verified=True,
        recovery_not_revoked=True,
        active_dispute=False,
        dispute_resolution_verified=False,
        human_approval_verified=True,
    )


def test_recovery_ready_is_nonexecuting_same_owner_supersession_only():
    d = evaluate_recovery(valid_recovery())
    assert d.recovery_ready is True
    assert d.prior_control_revocation_ready is True
    assert d.status == "READY_FOR_GOVERNED_RECOVERY_SUPERSESSION"
    assert d.ownership_restored is False
    assert d.control_rotated is False
    assert d.transfer_executed is False
    assert d.live_value_authorized is False
    assert d.legal_title_changed is False


def test_every_recovery_predicate_is_fail_closed():
    base = valid_recovery()
    for field in (
        "prior_poo_valid",
        "asset_continuity_verified",
        "claimant_continuity_verified",
        "claimant_identity_reverified",
        "title_or_provenance_reverified",
        "compromise_or_loss_evidence_bound",
        "recovery_pow_verified",
        "recovery_poc_concept_verified",
        "alternate_control_or_custody_verified",
        "recovery_pos_bond_verified",
        "multisource_or_quorum_verified",
        "freshness_verified",
        "recovery_not_revoked",
        "human_approval_verified",
    ):
        d = evaluate_recovery(replace(base, **{field: False}))
        assert d.recovery_ready is False, field
        assert d.missing_predicates, field


def test_poc_and_control_are_distinct_recovery_requirements():
    base = valid_recovery()
    missing_concept = evaluate_recovery(replace(base, recovery_poc_concept_verified=False))
    missing_control = evaluate_recovery(replace(base, alternate_control_or_custody_verified=False))
    assert "recovery PoC concept not verified" in missing_concept.missing_predicates
    assert "alternate control/custody not verified" in missing_control.missing_predicates
    assert missing_concept.recovery_ready is False
    assert missing_control.recovery_ready is False


def test_active_dispute_requires_explicit_resolution():
    blocked = evaluate_recovery(replace(valid_recovery(), active_dispute=True))
    assert blocked.status == "RECOVERY_DISPUTE_REVIEW_REQUIRED"
    assert blocked.recovery_ready is False
    assert "active dispute not resolved" in blocked.missing_predicates

    resolved = evaluate_recovery(
        replace(valid_recovery(), active_dispute=True, dispute_resolution_verified=True)
    )
    assert resolved.recovery_ready is True
    assert resolved.status == "READY_FOR_GOVERNED_RECOVERY_SUPERSESSION"


def test_invalid_recovery_reason_is_blocked():
    d = evaluate_recovery(replace(valid_recovery(), recovery_reason="OWNER_CHANGE"))
    assert d.recovery_ready is False
    assert "recovery reason not allowed" in d.missing_predicates


def test_ready_recovery_derives_same_claimant_poo_candidate():
    recovery = valid_recovery()
    candidate = derive_recovery_ownership_candidate(recovery)
    decision = evaluate_ownership(candidate)
    assert candidate.claimant_id == recovery.claimant_id
    assert candidate.previous_poo_digest == recovery.prior_poo_digest
    assert candidate.control_key_fingerprint == recovery.new_control_key_fingerprint
    assert candidate.poc_concept_verified is True
    assert candidate.control_or_custody_verified is True
    assert decision.poo_valid is True
    assert decision.legal_ownership_established is False


def test_unready_recovery_cannot_derive_candidate():
    with pytest.raises(ValueError):
        derive_recovery_ownership_candidate(
            replace(valid_recovery(), claimant_identity_reverified=False)
        )


def test_recovery_digest_is_deterministic_and_reason_sensitive():
    r = valid_recovery()
    assert recovery_digest(r) == recovery_digest(r)
    altered = replace(r, recovery_reason="LOST_CONTROL")
    assert recovery_digest(altered) != recovery_digest(r)


def test_recovery_does_not_change_owner_even_with_external_title_reference():
    r = replace(valid_recovery(), external_title_reference_verified=True)
    candidate = derive_recovery_ownership_candidate(r)
    d = evaluate_ownership(candidate)
    assert candidate.claimant_id == r.claimant_id
    assert d.status == "TECHNICAL_ATTESTATION_WITH_EXTERNAL_TITLE_REFERENCE"
    assert d.legal_ownership_established is False
