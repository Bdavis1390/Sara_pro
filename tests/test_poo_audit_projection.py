from dataclasses import replace

from security.poo.audit_projection import (
    POO_AUDIT_SCHEMA,
    ownership_audit_projection,
    recovery_audit_projection,
    transfer_audit_projection,
)
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.recovery_guard import RecoveryEvidence
from security.poo.transfer_guard import TransferEvidence


def ownership_evidence():
    return OwnershipEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:one",
        title_reference="title:ref:001",
        control_key_fingerprint="key:abc123",
        work_reference="work:challenge:001",
        concept_reference="concept:demo:001",
        stake_reference="stake:bond:001",
        issued_at="2026-09-16T00:00:00Z",
        expires_at="2026-09-17T00:00:00Z",
        asset_fingerprint_bound=True,
        claimant_identity_bound=True,
        title_or_provenance_bound=True,
        pow_verified=True,
        poc_concept_verified=True,
        control_or_custody_verified=True,
        pos_bond_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def transfer_evidence():
    return TransferEvidence(
        asset_id="asset:alpha",
        prior_poo_digest="prior:001",
        current_owner_id="claimant:one",
        recipient_id="claimant:two",
        title_transition_reference="title:transition:002",
        recipient_control_key_fingerprint="key:def456",
        recipient_work_reference="work:challenge:002",
        recipient_concept_reference="concept:demo:002",
        recipient_stake_reference="stake:bond:002",
        initiated_at="2026-09-16T01:00:00Z",
        expires_at="2026-09-17T01:00:00Z",
        prior_poo_valid=True,
        asset_continuity_verified=True,
        current_owner_authorized=True,
        recipient_identity_bound=True,
        recipient_poc_concept_verified=True,
        recipient_control_or_custody_verified=True,
        recipient_pow_verified=True,
        recipient_pos_bond_verified=True,
        title_or_provenance_transition_bound=True,
        freshness_verified=True,
        no_active_dispute=True,
        transfer_not_revoked=True,
        human_approval_verified=True,
    )


def recovery_evidence():
    return RecoveryEvidence(
        asset_id="asset:alpha",
        prior_poo_digest="prior:001",
        claimant_id="claimant:one",
        recovery_reason="LOST_CONTROL",
        title_reference="title:ref:001",
        new_control_key_fingerprint="key:new789",
        recovery_work_reference="work:recovery:001",
        recovery_concept_reference="concept:recovery:001",
        recovery_stake_reference="stake:recovery:001",
        recovery_request_reference="recovery:req:001",
        issued_at="2026-09-16T02:00:00Z",
        expires_at="2026-09-17T02:00:00Z",
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
        human_approval_verified=True,
    )


def assert_non_authoritative(projection):
    assert projection["human_approval_required"] is True
    assert projection["ownership_changed"] is False
    assert projection["transfer_executed"] is False
    assert projection["live_value_authorized"] is False
    assert projection["legal_title_established"] is False
    assert projection["legal_title_transferred"] is False
    assert projection["control_rotated"] is False


def test_ownership_projection_is_ready_but_non_authoritative():
    p = ownership_audit_projection(ownership_evidence())
    assert p["schema"] == POO_AUDIT_SCHEMA
    assert p["operation"] == "OWNERSHIP_ATTESTATION"
    assert p["technical_attestation_ready"] is True
    assert p["transfer_ready"] is False
    assert p["recovery_ready"] is False
    assert_non_authoritative(p)


def test_incomplete_ownership_projection_records_blocked_state():
    p = ownership_audit_projection(replace(ownership_evidence(), poc_concept_verified=False))
    assert p["technical_attestation_ready"] is False
    assert p["prime_state"] == "PRIME_POO_BLOCKED"
    assert p["sara_state"] == "SARA_POO_BLOCKED"
    assert_non_authoritative(p)


def test_transfer_projection_preserves_lineage_and_nonexecution():
    p = transfer_audit_projection(transfer_evidence())
    assert p["operation"] == "TRANSFER_READINESS"
    assert p["previous_poo_digest"] == "prior:001"
    assert p["transfer_ready"] is True
    assert p["technical_attestation_ready"] is False
    assert p["recovery_ready"] is False
    assert_non_authoritative(p)


def test_disputed_transfer_projection_is_explicitly_blocked():
    p = transfer_audit_projection(replace(transfer_evidence(), no_active_dispute=False))
    assert p["transfer_ready"] is False
    assert p["prime_state"] == "PRIME_POO_TRANSFER_BLOCKED_DISPUTE"
    assert p["overwatch_state"] == "OVERWATCH_POO_DISPUTE_ACTIVE"
    assert_non_authoritative(p)


def test_recovery_projection_is_same_owner_readiness_only():
    p = recovery_audit_projection(recovery_evidence())
    assert p["operation"] == "RECOVERY_READINESS"
    assert p["previous_poo_digest"] == "prior:001"
    assert p["recovery_ready"] is True
    assert p["transfer_ready"] is False
    assert p["technical_attestation_ready"] is False
    assert_non_authoritative(p)


def test_unresolved_recovery_dispute_records_blocked_state():
    p = recovery_audit_projection(replace(recovery_evidence(), active_dispute=True))
    assert p["recovery_ready"] is False
    assert p["prime_state"] == "PRIME_POO_RECOVERY_BLOCKED_DISPUTE"
    assert p["overwatch_state"] == "OVERWATCH_POO_DISPUTE_ACTIVE"
    assert_non_authoritative(p)
