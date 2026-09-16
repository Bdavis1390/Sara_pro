from dataclasses import replace

from security.poo.governance_guard import (
    evaluate_governed_recovery,
    evaluate_governed_transfer,
)
from security.poo.lineage_guard import LineageNode
from security.poo.recovery_guard import RecoveryEvidence
from security.poo.transfer_guard import TransferEvidence


def healthy_lineage():
    return [
        LineageNode(
            poo_digest="poo:001",
            asset_id="asset:alpha",
            claimant_id="claimant:one",
            previous_poo_digest=None,
            event_type="CLAIM",
            technical_poo_valid=True,
            superseded=True,
        ),
        LineageNode(
            poo_digest="poo:002",
            asset_id="asset:alpha",
            claimant_id="claimant:two",
            previous_poo_digest="poo:001",
            event_type="TRANSFER",
            technical_poo_valid=True,
        ),
    ]


def forked_lineage():
    return [
        LineageNode(
            poo_digest="poo:001",
            asset_id="asset:alpha",
            claimant_id="claimant:one",
            previous_poo_digest=None,
            event_type="CLAIM",
            technical_poo_valid=True,
            superseded=True,
        ),
        LineageNode(
            poo_digest="poo:002a",
            asset_id="asset:alpha",
            claimant_id="claimant:two",
            previous_poo_digest="poo:001",
            event_type="TRANSFER",
            technical_poo_valid=True,
        ),
        LineageNode(
            poo_digest="poo:002b",
            asset_id="asset:alpha",
            claimant_id="claimant:three",
            previous_poo_digest="poo:001",
            event_type="TRANSFER",
            technical_poo_valid=True,
        ),
    ]


def valid_transfer():
    return TransferEvidence(
        asset_id="asset:alpha",
        prior_poo_digest="poo:002",
        current_owner_id="claimant:two",
        recipient_id="claimant:three",
        title_transition_reference="title:transition:003",
        recipient_control_key_fingerprint="key:recipient003",
        recipient_work_reference="work:003",
        recipient_concept_reference="concept:003",
        recipient_stake_reference="stake:003",
        initiated_at="2026-09-16T03:00:00Z",
        expires_at="2026-09-17T03:00:00Z",
        prior_poo_valid=True,
        asset_continuity_verified=True,
        current_owner_authorized=True,
        recipient_identity_bound=True,
        recipient_poc_concept_verified=True,
        recipient_coc_verified=True,
        recipient_pow_verified=True,
        recipient_pos_bond_verified=True,
        title_or_provenance_transition_bound=True,
        freshness_verified=True,
        no_active_dispute=True,
        transfer_not_revoked=True,
        human_approval_verified=True,
    )


def valid_recovery():
    return RecoveryEvidence(
        asset_id="asset:alpha",
        prior_poo_digest="poo:002",
        claimant_id="claimant:two",
        recovery_reason="COMPROMISED_CONTROL",
        title_reference="title:ref:002",
        new_control_key_fingerprint="key:recovery002",
        recovery_work_reference="work:recovery:002",
        recovery_concept_reference="concept:recovery:002",
        recovery_stake_reference="stake:recovery:002",
        recovery_request_reference="recovery:req:002",
        issued_at="2026-09-16T03:00:00Z",
        expires_at="2026-09-17T03:00:00Z",
        prior_poo_valid=True,
        asset_continuity_verified=True,
        claimant_continuity_verified=True,
        claimant_identity_reverified=True,
        title_or_provenance_reverified=True,
        compromise_or_loss_evidence_bound=True,
        recovery_pow_verified=True,
        recovery_poc_concept_verified=True,
        alternate_coc_verified=True,
        recovery_pos_bond_verified=True,
        multisource_or_quorum_verified=True,
        freshness_verified=True,
        recovery_not_revoked=True,
        active_dispute=False,
        dispute_resolution_verified=False,
        human_approval_verified=True,
    )


def assert_nonexecuting(d):
    assert d.transfer_executed is False
    assert d.control_rotated is False
    assert d.live_value_authorized is False
    assert d.legal_title_changed is False
    assert d.conflict_winner_selected is False
    assert d.lineage_auto_resolved is False


def test_transfer_requires_valid_active_lineage_tip():
    d = evaluate_governed_transfer(valid_transfer(), healthy_lineage())
    assert d.readiness_allowed is True
    assert d.base_readiness is True
    assert d.lineage_valid is True
    assert d.status == "TRANSFER_READY_WITH_LINEAGE_GUARD"
    assert d.active_tip_digest == "poo:002"
    assert d.active_tip_claimant_id == "claimant:two"
    assert d.missing_predicates == []
    assert_nonexecuting(d)


def test_perfect_transfer_evidence_is_blocked_by_forked_lineage():
    d = evaluate_governed_transfer(
        replace(valid_transfer(), prior_poo_digest="poo:002a"),
        forked_lineage(),
    )
    assert d.base_readiness is True
    assert d.lineage_valid is False
    assert d.readiness_allowed is False
    assert d.status == "LINEAGE_CONFLICT_BLOCKED"
    assert "lineage integrity not verified" in d.missing_predicates
    assert d.active_tip_digest is None
    assert_nonexecuting(d)


def test_stale_prior_digest_blocks_otherwise_ready_transfer():
    d = evaluate_governed_transfer(
        replace(valid_transfer(), prior_poo_digest="poo:001"),
        healthy_lineage(),
    )
    assert d.base_readiness is True
    assert d.lineage_valid is True
    assert d.readiness_allowed is False
    assert d.status == "STALE_LINEAGE_REFERENCE_BLOCKED"
    assert "transfer prior PoO is not active lineage tip" in d.missing_predicates
    assert_nonexecuting(d)


def test_current_owner_must_match_active_technical_tip_claimant():
    d = evaluate_governed_transfer(
        replace(valid_transfer(), current_owner_id="claimant:one"),
        healthy_lineage(),
    )
    assert d.base_readiness is True
    assert d.readiness_allowed is False
    assert d.status == "ACTIVE_TIP_CLAIMANT_MISMATCH"
    assert "current owner does not match active technical lineage tip" in d.missing_predicates
    assert_nonexecuting(d)


def test_base_transfer_failure_remains_blocking_even_with_clean_lineage():
    d = evaluate_governed_transfer(
        replace(valid_transfer(), recipient_coc_verified=False),
        healthy_lineage(),
    )
    assert d.base_readiness is False
    assert d.lineage_valid is True
    assert d.readiness_allowed is False
    assert d.status == "BASE_TRANSFER_NOT_READY"
    assert_nonexecuting(d)


def test_recovery_requires_same_active_tip_claimant():
    d = evaluate_governed_recovery(valid_recovery(), healthy_lineage())
    assert d.readiness_allowed is True
    assert d.base_readiness is True
    assert d.lineage_valid is True
    assert d.status == "RECOVERY_READY_WITH_LINEAGE_GUARD"
    assert d.active_tip_digest == "poo:002"
    assert d.active_tip_claimant_id == "claimant:two"
    assert_nonexecuting(d)


def test_recovery_cannot_use_owner_change_as_same_owner_recovery():
    d = evaluate_governed_recovery(
        replace(valid_recovery(), claimant_id="claimant:one"),
        healthy_lineage(),
    )
    assert d.base_readiness is True
    assert d.readiness_allowed is False
    assert d.status == "ACTIVE_TIP_CLAIMANT_MISMATCH"
    assert "recovery claimant does not match active technical lineage tip" in d.missing_predicates
    assert_nonexecuting(d)


def test_recovery_is_blocked_by_forked_lineage_even_if_base_ready():
    d = evaluate_governed_recovery(
        replace(valid_recovery(), prior_poo_digest="poo:002a"),
        forked_lineage(),
    )
    assert d.base_readiness is True
    assert d.lineage_valid is False
    assert d.readiness_allowed is False
    assert d.status == "LINEAGE_CONFLICT_BLOCKED"
    assert_nonexecuting(d)


def test_governance_digest_changes_when_lineage_changes():
    healthy = evaluate_governed_transfer(valid_transfer(), healthy_lineage())
    stale_lineage = healthy_lineage()
    stale_lineage[-1] = replace(stale_lineage[-1], claimant_id="claimant:changed")
    changed = evaluate_governed_transfer(valid_transfer(), stale_lineage)
    assert healthy.digest != changed.digest
