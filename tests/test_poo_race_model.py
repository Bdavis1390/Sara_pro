from security.poo.coc_guard import COCEvidence, coc_digest
from security.poo.commit_guard import prepare_registry_commit
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.registry_guard import registry_digest
from security.poo.recovery_guard import RecoveryEvidence
from security.poo.state_engine import (
    bootstrap_technical_state,
    prepare_recovery_transition,
    prepare_transfer_transition,
)
from security.poo.transfer_guard import TransferEvidence


def coc(claimant, key, *, previous=None, suffix="0"):
    return COCEvidence(
        asset_id="asset:race",
        claimant_id=claimant,
        control_key_fingerprint=key,
        custody_reference=f"custody:{claimant}:{suffix}",
        custody_point_reference=f"point:{claimant}:{suffix}",
        challenge_reference=f"challenge:{claimant}:{suffix}",
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


def genesis():
    c = coc("alice", "key:alice")
    ownership = OwnershipEvidence(
        asset_id="asset:race",
        claimant_id="alice",
        title_reference="title:race",
        control_key_fingerprint="key:alice",
        work_reference="work:genesis",
        concept_reference="concept:genesis",
        coc_reference=coc_digest(c),
        stake_reference="stake:genesis",
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
    decision = bootstrap_technical_state(ownership, c)
    assert decision.ready is True
    return decision.candidate_state


def transfer(current, recipient, key, suffix):
    next_coc = coc(
        recipient,
        key,
        previous=current.active_coc_digest,
        suffix=suffix,
    )
    evidence = TransferEvidence(
        asset_id=current.asset_id,
        prior_poo_digest=current.active_poo_digest,
        current_owner_id=current.claimant_id,
        recipient_id=recipient,
        title_transition_reference=f"title:race:{suffix}",
        recipient_control_key_fingerprint=key,
        recipient_work_reference=f"work:{suffix}",
        recipient_concept_reference=f"concept:{suffix}",
        recipient_coc_reference=coc_digest(next_coc),
        recipient_stake_reference=f"stake:{suffix}",
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
    decision = prepare_transfer_transition(current, evidence, next_coc)
    assert decision.ready is True
    return decision


def recovery(current, suffix="recovery"):
    next_coc = coc(
        current.claimant_id,
        f"key:{suffix}",
        previous=current.active_coc_digest,
        suffix=suffix,
    )
    evidence = RecoveryEvidence(
        asset_id=current.asset_id,
        prior_poo_digest=current.active_poo_digest,
        claimant_id=current.claimant_id,
        recovery_reason="COMPROMISED_CONTROL",
        title_reference=current.title_reference,
        new_control_key_fingerprint=f"key:{suffix}",
        recovery_work_reference=f"work:{suffix}",
        recovery_concept_reference=f"concept:{suffix}",
        recovery_coc_reference=coc_digest(next_coc),
        recovery_stake_reference=f"stake:{suffix}",
        recovery_request_reference=f"request:{suffix}",
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
        alternate_coc_verified=True,
        recovery_pos_bond_verified=True,
        multisource_or_quorum_verified=True,
        freshness_verified=True,
        recovery_not_revoked=True,
        active_dispute=False,
        human_approval_verified=True,
    )
    decision = prepare_recovery_transition(current, evidence, next_coc)
    assert decision.ready is True
    return decision


def commit(current_states, transition, expected=None):
    if expected is None:
        expected = registry_digest(current_states)
    return prepare_registry_commit(
        current_states,
        transition,
        expected_registry_digest=expected,
    )


def test_two_prepared_transfers_cannot_both_commit_regardless_of_order():
    root = genesis()
    prepared = [
        transfer(root, "bob", "key:bob", "bob"),
        transfer(root, "carol", "key:carol", "carol"),
    ]
    for winner_index in (0, 1):
        loser_index = 1 - winner_index
        first = commit([root], prepared[winner_index])
        assert first.commit_ready is True
        advanced = list(first.candidate_states)

        # A stale writer using the old compare-and-swap digest fails immediately.
        stale = commit(
            advanced,
            prepared[loser_index],
            expected=registry_digest([root]),
        )
        assert stale.commit_ready is False
        assert "stale registry digest" in stale.reasons

        # Even if the stale writer refreshes the registry digest, its predecessor
        # remains obsolete and cannot become a second active branch.
        refreshed = commit(advanced, prepared[loser_index])
        assert refreshed.commit_ready is False
        assert "candidate predecessor is not the active PoO tip" in refreshed.reasons
        assert "candidate predecessor is not the active COC tip" in refreshed.reasons


def test_transfer_and_recovery_prepared_from_same_tip_are_mutually_exclusive():
    root = genesis()
    transfer_candidate = transfer(root, "bob", "key:bob", "transfer")
    recovery_candidate = recovery(root)

    transfer_commit = commit([root], transfer_candidate)
    assert transfer_commit.commit_ready is True
    after_transfer = list(transfer_commit.candidate_states)
    rejected_recovery = commit(after_transfer, recovery_candidate)
    assert rejected_recovery.commit_ready is False
    assert "candidate predecessor is not the active PoO tip" in rejected_recovery.reasons

    recovery_commit = commit([root], recovery_candidate)
    assert recovery_commit.commit_ready is True
    after_recovery = list(recovery_commit.candidate_states)
    rejected_transfer = commit(after_recovery, transfer_candidate)
    assert rejected_transfer.commit_ready is False
    assert "candidate predecessor is not the active PoO tip" in rejected_transfer.reasons


def test_committed_candidate_replay_is_always_rejected():
    root = genesis()
    transition = transfer(root, "bob", "key:bob", "replay")
    first = commit([root], transition)
    assert first.commit_ready is True
    advanced = list(first.candidate_states)

    replay = commit(advanced, transition)
    assert replay.commit_ready is False
    assert "candidate technical state is a replay" in replay.reasons
    assert "candidate PoO already exists in registry" in replay.reasons
