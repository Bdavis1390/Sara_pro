from dataclasses import replace

from security.poo.audit_projection import (
    POO_AUDIT_SCHEMA,
    coc_audit_projection,
    governed_state_transition_audit_projection,
    ownership_audit_projection,
    recovery_audit_projection,
    registry_audit_projection,
    registry_commit_readiness_audit_projection,
    state_lineage_audit_projection,
    state_transition_audit_projection,
    transfer_audit_projection,
)
from security.poo.coc_guard import COCEvidence, coc_digest
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.recovery_guard import RecoveryEvidence
from security.poo.registry_governance_guard import evaluate_governed_registry_commit
from security.poo.registry_guard import evaluate_registry, registry_digest
from security.poo.state_engine import bootstrap_technical_state, evaluate_state_lineage
from security.poo.state_governance_guard import evaluate_governed_transfer_transition
from security.poo.transfer_guard import TransferEvidence


def coc_evidence():
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:one",
        control_key_fingerprint="key:abc123",
        custody_reference="custody:001",
        custody_point_reference="custody:point:001",
        challenge_reference="challenge:coc:001",
        observed_at="2026-09-16T00:00:00Z",
        expires_at="2026-09-17T00:00:00Z",
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def ownership_evidence():
    coc = coc_evidence()
    return OwnershipEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:one",
        title_reference="title:ref:001",
        control_key_fingerprint="key:abc123",
        work_reference="work:challenge:001",
        concept_reference="concept:demo:001",
        coc_reference=coc_digest(coc),
        stake_reference="stake:bond:001",
        issued_at="2026-09-16T00:00:00Z",
        expires_at="2026-09-17T00:00:00Z",
        asset_fingerprint_bound=True,
        claimant_identity_bound=True,
        title_or_provenance_bound=True,
        pow_verified=True,
        poc_concept_verified=True,
        coc_verified=True,
        pos_bond_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def recipient_coc(previous_coc_digest: str):
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:two",
        control_key_fingerprint="key:def456",
        custody_reference="custody:002",
        custody_point_reference="custody:point:002",
        challenge_reference="challenge:coc:002",
        observed_at="2026-09-16T01:00:00Z",
        expires_at="2026-09-17T01:00:00Z",
        previous_coc_digest=previous_coc_digest,
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def transfer_evidence(*, prior_poo_digest="prior:001", current_owner_id="claimant:one", recipient_coc_reference="coc:recipient:002"):
    return TransferEvidence(
        asset_id="asset:alpha",
        prior_poo_digest=prior_poo_digest,
        current_owner_id=current_owner_id,
        recipient_id="claimant:two",
        title_transition_reference="title:transition:002",
        recipient_control_key_fingerprint="key:def456",
        recipient_work_reference="work:challenge:002",
        recipient_concept_reference="concept:demo:002",
        recipient_coc_reference=recipient_coc_reference,
        recipient_stake_reference="stake:bond:002",
        initiated_at="2026-09-16T01:00:00Z",
        expires_at="2026-09-17T01:00:00Z",
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
        recovery_coc_reference="coc:recovery:001",
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
        alternate_coc_verified=True,
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
    assert projection["technical_registry_committed"] is False
    assert projection["durable_registry_write_authorized"] is False
    assert projection["conflict_winner_selected"] is False
    assert projection["lineage_auto_resolved"] is False


def assert_only(projection, field):
    fields = (
        "technical_attestation_ready",
        "coc_valid",
        "transfer_ready",
        "recovery_ready",
        "state_transition_ready",
        "registry_consistent",
        "registry_commit_ready",
    )
    for item in fields:
        assert projection[item] is (item == field)


def test_ownership_projection_is_ready_but_non_authoritative():
    p = ownership_audit_projection(ownership_evidence())
    assert p["schema"] == POO_AUDIT_SCHEMA
    assert p["operation"] == "OWNERSHIP_ATTESTATION"
    assert_only(p, "technical_attestation_ready")
    assert_non_authoritative(p)


def test_coc_projection_is_first_class_and_non_authoritative():
    p = coc_audit_projection(coc_evidence())
    assert p["operation"] == "COC_ATTESTATION"
    assert_only(p, "coc_valid")
    assert p["prime_state"] == "PRIME_COC_ACCEPTED"
    assert_non_authoritative(p)


def test_invalid_coc_projection_is_blocked():
    p = coc_audit_projection(replace(coc_evidence(), challenge_response_verified=False))
    assert p["coc_valid"] is False
    assert p["prime_state"] == "PRIME_COC_BLOCKED"
    assert_non_authoritative(p)


def test_incomplete_ownership_projection_records_blocked_state():
    p = ownership_audit_projection(replace(ownership_evidence(), poc_concept_verified=False))
    assert p["technical_attestation_ready"] is False
    assert p["prime_state"] == "PRIME_POO_BLOCKED"
    assert p["sara_state"] == "SARA_POO_BLOCKED"
    assert_non_authoritative(p)


def test_transfer_projection_remains_base_evidence_only():
    p = transfer_audit_projection(transfer_evidence())
    assert p["operation"] == "TRANSFER_READINESS"
    assert p["previous_poo_digest"] == "prior:001"
    assert_only(p, "transfer_ready")
    assert p["state_lineage_checked"] is False
    assert p["registry_commit_ready"] is False
    assert_non_authoritative(p)


def test_disputed_transfer_projection_is_explicitly_blocked():
    p = transfer_audit_projection(replace(transfer_evidence(), no_active_dispute=False))
    assert p["transfer_ready"] is False
    assert p["prime_state"] == "PRIME_POO_TRANSFER_BLOCKED_DISPUTE"
    assert p["overwatch_state"] == "OVERWATCH_POO_DISPUTE_ACTIVE"
    assert_non_authoritative(p)


def test_recovery_projection_is_same_owner_base_readiness_only():
    p = recovery_audit_projection(recovery_evidence())
    assert p["operation"] == "RECOVERY_READINESS"
    assert p["previous_poo_digest"] == "prior:001"
    assert_only(p, "recovery_ready")
    assert p["state_lineage_checked"] is False
    assert_non_authoritative(p)


def test_local_state_transition_projection_is_candidate_only_not_commit_ready():
    decision = bootstrap_technical_state(ownership_evidence(), coc_evidence())
    assert decision.ready is True
    p = state_transition_audit_projection(decision, asset_id="asset:alpha", previous_poo_digest=None)
    assert p["operation"] == "TECHNICAL_STATE_TRANSITION"
    assert_only(p, "state_transition_ready")
    assert p["overwatch_state"] == "OVERWATCH_POO_STATE_CANDIDATE_MONITOR"
    assert p["state_lineage_checked"] is False
    assert p["registry_commit_ready"] is False
    assert p["candidate_state_digest"] == decision.candidate_state_digest
    assert_non_authoritative(p)


def _governed_fixture():
    state = bootstrap_technical_state(ownership_evidence(), coc_evidence()).candidate_state
    history = [state]
    rcoc = recipient_coc(state.active_coc_digest)
    transfer = transfer_evidence(
        prior_poo_digest=state.active_poo_digest,
        current_owner_id=state.claimant_id,
        recipient_coc_reference=coc_digest(rcoc),
    )
    governed = evaluate_governed_transfer_transition(history, transfer, rcoc)
    return history, transfer, governed


def test_state_lineage_projection_exposes_poo_coc_generation_health():
    history, _transfer, _governed = _governed_fixture()
    lineage = evaluate_state_lineage(history)
    p = state_lineage_audit_projection(lineage, asset_id="asset:alpha")
    assert p["operation"] == "STATE_LINEAGE_INTEGRITY"
    assert p["state_lineage_checked"] is True
    assert p["state_lineage_valid"] is True
    assert p["poo_lineage_valid"] is True
    assert p["coc_lineage_valid"] is True
    assert p["generation_valid"] is True
    assert p["active_tip_digest"] == history[0].active_poo_digest
    assert p["lineage_issue_count"] == 0
    assert p["prime_state"] == "PRIME_POO_STATE_LINEAGE_ELIGIBLE"
    assert_non_authoritative(p)


def test_governed_state_projection_requires_full_lineage_but_still_does_not_commit():
    history, transfer, governed = _governed_fixture()
    p = governed_state_transition_audit_projection(
        governed,
        asset_id="asset:alpha",
        previous_poo_digest=transfer.prior_poo_digest,
    )
    assert governed.ready is True
    assert p["operation"] == "GOVERNED_STATE_TRANSITION"
    assert_only(p, "state_transition_ready")
    assert p["state_lineage_checked"] is True
    assert p["state_lineage_valid"] is True
    assert p["active_tip_digest"] == history[0].active_poo_digest
    assert p["registry_commit_ready"] is False
    assert p["prime_state"] == "PRIME_POO_GOVERNED_STATE_TRANSITION_READY"
    assert_non_authoritative(p)


def test_registry_health_projection_is_auditable_but_not_government_authority():
    state = bootstrap_technical_state(ownership_evidence(), coc_evidence()).candidate_state
    registry = evaluate_registry([state])
    p = registry_audit_projection(registry)
    assert p["operation"] == "REGISTRY_HEALTH"
    assert_only(p, "registry_consistent")
    assert p["asset_id"] == "registry:technical-ownership"
    assert p["prime_state"] == "PRIME_POO_REGISTRY_CONSISTENT"
    assert_non_authoritative(p)


def test_registry_conflict_projection_is_explicitly_review_required():
    state = bootstrap_technical_state(ownership_evidence(), coc_evidence()).candidate_state
    registry = evaluate_registry([state, state])
    p = registry_audit_projection(registry)
    assert p["registry_consistent"] is False
    assert p["overwatch_state"] == "OVERWATCH_POO_REGISTRY_CONFLICT"
    assert_non_authoritative(p)


def test_full_governance_commit_projection_binds_lineage_and_registry_snapshot():
    history, transfer, governed = _governed_fixture()
    decision = evaluate_governed_registry_commit(
        history,
        governed,
        expected_registry_digest=registry_digest(history),
    )
    p = registry_commit_readiness_audit_projection(
        decision,
        asset_id="asset:alpha",
        previous_poo_digest=transfer.prior_poo_digest,
    )
    assert decision.ready is True
    assert p["operation"] == "REGISTRY_COMMIT_READINESS"
    assert_only(p, "registry_commit_ready")
    assert p["state_lineage_checked"] is True
    assert p["state_lineage_valid"] is True
    assert p["optimistic_concurrency_checked"] is True
    assert p["optimistic_concurrency_match"] is True
    assert p["expected_registry_digest"] == p["current_registry_digest"]
    assert p["candidate_registry_digest"]
    assert p["candidate_state_digest"] == governed.candidate_state_digest
    assert p["prime_state"] == "PRIME_POO_REGISTRY_COMMIT_CANDIDATE_READY"
    assert_non_authoritative(p)


def test_stale_snapshot_projection_is_fail_closed_and_requires_reevaluation():
    history, transfer, governed = _governed_fixture()
    decision = evaluate_governed_registry_commit(
        history,
        governed,
        expected_registry_digest="stale-digest",
    )
    p = registry_commit_readiness_audit_projection(
        decision,
        asset_id="asset:alpha",
        previous_poo_digest=transfer.prior_poo_digest,
    )
    assert decision.ready is False
    assert p["registry_commit_ready"] is False
    assert p["state_lineage_valid"] is True
    assert p["optimistic_concurrency_checked"] is True
    assert p["optimistic_concurrency_match"] is False
    assert p["prime_state"] == "PRIME_POO_REGISTRY_COMMIT_BLOCKED_STALE"
    assert p["sara_state"] == "SARA_POO_REGISTRY_COMMIT_REEVALUATION_REQUIRED"
    assert p["candidate_registry_digest"] is None
    assert_non_authoritative(p)
