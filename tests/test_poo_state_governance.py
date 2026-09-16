from dataclasses import replace

from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.recovery_guard import RecoveryEvidence
from security.poo.state_engine import bootstrap_technical_state, prepare_transfer_transition
from security.poo.state_governance_guard import (
    evaluate_governed_recovery_transition,
    evaluate_governed_transfer_transition,
)
from security.poo.transfer_guard import TransferEvidence


def coc(*, claimant: str, key: str, suffix: str, previous: str | None = None) -> COCEvidence:
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id=claimant,
        control_key_fingerprint=key,
        custody_reference=f"custody:{suffix}",
        custody_point_reference=f"point:{suffix}",
        challenge_reference=f"challenge:{suffix}",
        observed_at="2026-09-16T04:00:00Z",
        expires_at="2026-09-17T04:00:00Z",
        previous_coc_digest=previous,
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def genesis():
    c0 = coc(claimant="claimant:one", key="key:001", suffix="001")
    c0d = evaluate_coc(c0).digest
    own = OwnershipEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:one",
        title_reference="title:001",
        control_key_fingerprint="key:001",
        work_reference="work:001",
        concept_reference="concept:001",
        coc_reference=c0d,
        stake_reference="stake:001",
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
    decision = bootstrap_technical_state(own, c0)
    assert decision.ready and decision.candidate_state is not None
    return decision.candidate_state


def transfer_from(current, *, recipient="claimant:two", key="key:002", suffix="002"):
    next_coc = coc(
        claimant=recipient,
        key=key,
        suffix=suffix,
        previous=current.active_coc_digest,
    )
    next_coc_digest = evaluate_coc(next_coc).digest
    transfer = TransferEvidence(
        asset_id=current.asset_id,
        prior_poo_digest=current.active_poo_digest,
        current_owner_id=current.claimant_id,
        recipient_id=recipient,
        title_transition_reference=f"title:{suffix}",
        recipient_control_key_fingerprint=key,
        recipient_work_reference=f"work:{suffix}",
        recipient_concept_reference=f"concept:{suffix}",
        recipient_coc_reference=next_coc_digest,
        recipient_stake_reference=f"stake:{suffix}",
        initiated_at="2026-09-16T04:00:00Z",
        expires_at="2026-09-17T04:00:00Z",
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
    return transfer, next_coc


def two_state_history():
    s0 = genesis()
    t1, c1 = transfer_from(s0)
    decision = prepare_transfer_transition(s0, t1, c1)
    assert decision.ready and decision.candidate_state is not None
    return [s0, decision.candidate_state]


def recovery_from(current):
    c = coc(
        claimant=current.claimant_id,
        key="key:recovery",
        suffix="recovery",
        previous=current.active_coc_digest,
    )
    cd = evaluate_coc(c).digest
    r = RecoveryEvidence(
        asset_id=current.asset_id,
        prior_poo_digest=current.active_poo_digest,
        claimant_id=current.claimant_id,
        recovery_reason="COMPROMISED_CONTROL",
        title_reference=current.title_reference,
        new_control_key_fingerprint="key:recovery",
        recovery_work_reference="work:recovery",
        recovery_concept_reference="concept:recovery",
        recovery_coc_reference=cd,
        recovery_stake_reference="stake:recovery",
        recovery_request_reference="request:recovery",
        issued_at="2026-09-16T04:00:00Z",
        expires_at="2026-09-17T04:00:00Z",
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
    return r, c


def assert_non_authoritative(d):
    assert d.technical_state_committed is False
    assert d.conflict_winner_selected is False
    assert d.lineage_auto_resolved is False
    assert d.legal_title_changed is False
    assert d.live_value_moved is False
    assert d.external_transfer_executed is False


def test_clean_history_allows_lineage_governed_transfer_candidate_only():
    history = two_state_history()
    transfer, c = transfer_from(history[-1], recipient="claimant:three", key="key:003", suffix="003")
    d = evaluate_governed_transfer_transition(history, transfer, c)
    assert d.ready is True
    assert d.base_evidence_ready is True
    assert d.state_lineage_valid is True
    assert d.poo_lineage_valid is True
    assert d.coc_lineage_valid is True
    assert d.generation_valid is True
    assert d.status == "STATE_TRANSFER_READY_WITH_LINEAGE_GUARD"
    assert d.transition is not None and d.transition.ready is True
    assert d.candidate_state_digest == d.transition.candidate_state_digest
    assert_non_authoritative(d)


def test_exact_coc_digest_binding_is_required_by_governed_transfer():
    history = two_state_history()
    transfer, c = transfer_from(history[-1], recipient="claimant:three", key="key:003", suffix="003")
    d = evaluate_governed_transfer_transition(
        history,
        replace(transfer, recipient_coc_reference="wrong-coc-digest"),
        c,
    )
    assert d.base_evidence_ready is True
    assert d.state_lineage_valid is True
    assert d.ready is False
    assert any("COC digest does not match semantic COC reference" in reason for reason in d.reasons)
    assert_non_authoritative(d)


def test_broken_historical_coc_lineage_blocks_perfect_new_evidence():
    history = two_state_history()
    history[1] = replace(history[1], previous_coc_digest="coc:wrong")
    transfer, c = transfer_from(history[1], recipient="claimant:three", key="key:003", suffix="003")
    d = evaluate_governed_transfer_transition(history, transfer, c)
    assert d.base_evidence_ready is True
    assert d.ready is False
    assert d.state_lineage_valid is False
    assert d.poo_lineage_valid is True
    assert d.coc_lineage_valid is False
    assert d.status == "STATE_LINEAGE_CONFLICT_BLOCKED"
    assert_non_authoritative(d)


def test_generation_gap_blocks_perfect_new_evidence():
    history = two_state_history()
    history[1] = replace(history[1], generation=2)
    transfer, c = transfer_from(history[1], recipient="claimant:three", key="key:003", suffix="003")
    d = evaluate_governed_transfer_transition(history, transfer, c)
    assert d.base_evidence_ready is True
    assert d.ready is False
    assert d.generation_valid is False
    assert d.status == "STATE_LINEAGE_CONFLICT_BLOCKED"
    assert_non_authoritative(d)


def test_forked_history_blocks_without_selecting_a_winner():
    history = two_state_history()
    fork = replace(
        history[1],
        active_poo_digest="poo:fork",
        active_coc_digest="coc:fork",
        claimant_id="claimant:fork",
        control_key_fingerprint="key:fork",
    )
    forked = history + [fork]
    transfer, c = transfer_from(history[1], recipient="claimant:three", key="key:003", suffix="003")
    d = evaluate_governed_transfer_transition(forked, transfer, c)
    assert d.base_evidence_ready is True
    assert d.ready is False
    assert d.state_lineage_valid is False
    assert d.fork_detected is True
    assert d.active_tip_poo_digest is None
    assert d.conflict_winner_selected is False
    assert_non_authoritative(d)


def test_stale_poo_predecessor_blocks_after_clean_lineage_check():
    history = two_state_history()
    transfer, c = transfer_from(history[-1], recipient="claimant:three", key="key:003", suffix="003")
    d = evaluate_governed_transfer_transition(
        history,
        replace(transfer, prior_poo_digest=history[0].active_poo_digest),
        c,
    )
    assert d.base_evidence_ready is True
    assert d.state_lineage_valid is True
    assert d.ready is False
    assert any("predecessor does not match active PoO" in reason for reason in d.reasons)
    assert_non_authoritative(d)


def test_clean_history_allows_same_owner_recovery_candidate_only():
    history = two_state_history()
    recovery, c = recovery_from(history[-1])
    d = evaluate_governed_recovery_transition(history, recovery, c)
    assert d.ready is True
    assert d.base_evidence_ready is True
    assert d.state_lineage_valid is True
    assert d.status == "STATE_RECOVERY_READY_WITH_LINEAGE_GUARD"
    assert d.transition is not None and d.transition.ready is True
    assert_non_authoritative(d)


def test_recovery_cannot_change_active_claimant():
    history = two_state_history()
    recovery, c = recovery_from(history[-1])
    d = evaluate_governed_recovery_transition(
        history,
        replace(recovery, claimant_id="claimant:one"),
        c,
    )
    assert d.base_evidence_ready is True
    assert d.state_lineage_valid is True
    assert d.ready is False
    assert any("recovery claimant must match active technical claimant" in reason for reason in d.reasons)
    assert_non_authoritative(d)
