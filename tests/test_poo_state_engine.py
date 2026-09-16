from dataclasses import replace

from security.poo.coc_guard import COCEvidence, coc_digest
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.recovery_guard import RecoveryEvidence
from security.poo.state_engine import (
    bootstrap_technical_state,
    evaluate_state_lineage,
    prepare_recovery_transition,
    prepare_transfer_transition,
)
from security.poo.transfer_guard import TransferEvidence


def genesis_ownership(coc_reference):
    return OwnershipEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:one",
        title_reference="title:001",
        control_key_fingerprint="key:one",
        work_reference="work:001",
        concept_reference="concept:001",
        coc_reference=coc_reference,
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


def coc_for(claimant, key, *, previous=None, point="custody:point:001"):
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id=claimant,
        control_key_fingerprint=key,
        custody_reference=f"custody:{claimant}:{key}",
        custody_point_reference=point,
        challenge_reference=f"challenge:{claimant}:{key}",
        observed_at="2026-09-16T00:00:00Z",
        expires_at="2026-09-17T00:00:00Z",
        previous_coc_digest=previous,
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def transfer_from(state, coc_reference, *, recipient="claimant:two", key="key:two"):
    return TransferEvidence(
        asset_id=state.asset_id,
        prior_poo_digest=state.active_poo_digest,
        current_owner_id=state.claimant_id,
        recipient_id=recipient,
        title_transition_reference="title:transition:002",
        recipient_control_key_fingerprint=key,
        recipient_work_reference="work:002",
        recipient_concept_reference="concept:002",
        recipient_coc_reference=coc_reference,
        recipient_stake_reference="stake:002",
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


def recovery_from(state, coc_reference, *, key="key:recovered"):
    return RecoveryEvidence(
        asset_id=state.asset_id,
        prior_poo_digest=state.active_poo_digest,
        claimant_id=state.claimant_id,
        recovery_reason="COMPROMISED_CONTROL",
        title_reference=state.title_reference,
        new_control_key_fingerprint=key,
        recovery_work_reference="work:recovery",
        recovery_concept_reference="concept:recovery",
        recovery_coc_reference=coc_reference,
        recovery_stake_reference="stake:recovery",
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


def bootstrap():
    coc = coc_for("claimant:one", "key:one")
    decision = bootstrap_technical_state(genesis_ownership(coc_digest(coc)), coc)
    assert decision.ready is True
    return decision.candidate_state


def test_bootstrap_binds_genesis_poo_to_exact_coc_digest():
    coc = coc_for("claimant:one", "key:one")
    decision = bootstrap_technical_state(genesis_ownership(coc_digest(coc)), coc)
    assert decision.ready is True
    state = decision.candidate_state
    assert state.active_coc_digest == coc_digest(coc)
    assert state.generation == 0
    assert state.legal_title_established is False


def test_bootstrap_rejects_semantically_wrong_coc_reference():
    coc = coc_for("claimant:one", "key:one")
    decision = bootstrap_technical_state(genesis_ownership("coc:wrong"), coc)
    assert decision.ready is False
    assert "COC digest does not match semantic COC reference" in decision.reasons


def test_bootstrap_rejects_mismatched_coc_claimant():
    coc = coc_for("claimant:other", "key:one")
    decision = bootstrap_technical_state(genesis_ownership(coc_digest(coc)), coc)
    assert decision.ready is False
    assert "COC claimant does not match ownership claimant" in decision.reasons


def test_transfer_advances_poo_and_coc_lineages_together():
    current = bootstrap()
    next_coc = coc_for("claimant:two", "key:two", previous=current.active_coc_digest)
    transfer = transfer_from(current, coc_digest(next_coc))
    decision = prepare_transfer_transition(current, transfer, next_coc)
    assert decision.ready is True
    assert decision.technical_state_committed is False
    candidate = decision.candidate_state
    assert candidate.claimant_id == "claimant:two"
    assert candidate.previous_poo_digest == current.active_poo_digest
    assert candidate.previous_coc_digest == current.active_coc_digest
    assert candidate.generation == 1


def test_transfer_boolean_coc_cannot_hide_wrong_coc_digest_reference():
    current = bootstrap()
    next_coc = coc_for("claimant:two", "key:two", previous=current.active_coc_digest)
    transfer = transfer_from(current, "coc:wrong")
    assert transfer.recipient_coc_verified is True
    decision = prepare_transfer_transition(current, transfer, next_coc)
    assert decision.ready is False
    assert "COC digest does not match semantic COC reference" in decision.reasons


def test_transfer_rejects_stale_active_poo_predecessor():
    current = bootstrap()
    next_coc = coc_for("claimant:two", "key:two", previous=current.active_coc_digest)
    transfer = replace(transfer_from(current, coc_digest(next_coc)), prior_poo_digest="stale-poo")
    decision = prepare_transfer_transition(current, transfer, next_coc)
    assert decision.ready is False
    assert "transfer predecessor does not match active PoO" in decision.reasons


def test_transfer_rejects_wrong_coc_predecessor():
    current = bootstrap()
    next_coc = coc_for("claimant:two", "key:two", previous="wrong-coc")
    transfer = transfer_from(current, coc_digest(next_coc))
    decision = prepare_transfer_transition(current, transfer, next_coc)
    assert decision.ready is False
    assert "COC predecessor does not match active COC lineage" in decision.reasons


def test_recovery_advances_coc_but_preserves_claimant():
    current = bootstrap()
    next_coc = coc_for(current.claimant_id, "key:recovered", previous=current.active_coc_digest)
    recovery = recovery_from(current, coc_digest(next_coc))
    decision = prepare_recovery_transition(current, recovery, next_coc)
    assert decision.ready is True
    candidate = decision.candidate_state
    assert candidate.claimant_id == current.claimant_id
    assert candidate.active_coc_digest == coc_digest(next_coc)
    assert candidate.generation == current.generation + 1
    assert decision.external_transfer_executed is False


def test_recovery_boolean_coc_cannot_hide_wrong_coc_digest_reference():
    current = bootstrap()
    next_coc = coc_for(current.claimant_id, "key:recovered", previous=current.active_coc_digest)
    recovery = recovery_from(current, "coc:wrong")
    assert recovery.alternate_coc_verified is True
    decision = prepare_recovery_transition(current, recovery, next_coc)
    assert decision.ready is False
    assert "COC digest does not match semantic COC reference" in decision.reasons


def test_recovery_cannot_change_active_claimant():
    current = bootstrap()
    next_coc = coc_for("claimant:other", "key:recovered", previous=current.active_coc_digest)
    recovery = replace(
        recovery_from(current, coc_digest(next_coc)), claimant_id="claimant:other"
    )
    decision = prepare_recovery_transition(current, recovery, next_coc)
    assert decision.ready is False
    assert "recovery claimant must match active technical claimant" in decision.reasons


def test_end_to_end_claim_transfer_recovery_lineage_is_consistent():
    genesis = bootstrap()
    transfer_coc = coc_for("claimant:two", "key:two", previous=genesis.active_coc_digest)
    transfer = transfer_from(genesis, coc_digest(transfer_coc))
    transferred = prepare_transfer_transition(genesis, transfer, transfer_coc).candidate_state

    recovery_coc = coc_for("claimant:two", "key:three", previous=transferred.active_coc_digest)
    recovery = recovery_from(transferred, coc_digest(recovery_coc), key="key:three")
    recovered = prepare_recovery_transition(transferred, recovery, recovery_coc).candidate_state

    lineage = evaluate_state_lineage([genesis, transferred, recovered])
    assert lineage.lineage_valid is True
    assert lineage.poo_lineage_valid is True
    assert lineage.coc_lineage_valid is True
    assert lineage.active_tip_digest == recovered.active_poo_digest
    assert lineage.legal_title_established is False


def test_two_successors_from_same_state_create_detectable_fork():
    genesis = bootstrap()
    c1 = coc_for("claimant:two", "key:two", previous=genesis.active_coc_digest)
    t1 = transfer_from(genesis, coc_digest(c1), recipient="claimant:two", key="key:two")
    s1 = prepare_transfer_transition(genesis, t1, c1).candidate_state

    c2 = coc_for("claimant:three", "key:three", previous=genesis.active_coc_digest)
    t2 = transfer_from(genesis, coc_digest(c2), recipient="claimant:three", key="key:three")
    s2 = prepare_transfer_transition(genesis, t2, c2).candidate_state

    lineage = evaluate_state_lineage([genesis, s1, s2])
    assert lineage.lineage_valid is False
    assert lineage.fork_detected is True
    assert any("forked ownership lineage detected" in issue for issue in lineage.issues)
