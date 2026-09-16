from dataclasses import replace

from security.poo.coc_guard import COCEvidence, coc_digest
from security.poo.commit_guard import prepare_registry_commit
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.registry_guard import registry_digest
from security.poo.state_engine import bootstrap_technical_state, prepare_transfer_transition
from security.poo.transfer_guard import TransferEvidence


def coc(claimant, key, previous=None):
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id=claimant,
        control_key_fingerprint=key,
        custody_reference=f"custody:{claimant}",
        custody_point_reference=f"point:{claimant}",
        challenge_reference=f"challenge:{claimant}",
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


def ownership(coc_reference):
    return OwnershipEvidence(
        asset_id="asset:alpha",
        claimant_id="alice",
        title_reference="title:alpha",
        control_key_fingerprint="key:alice",
        work_reference="work:1",
        concept_reference="concept:1",
        coc_reference=coc_reference,
        stake_reference="stake:1",
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


def transfer(current, coc_reference, recipient="bob", key="key:bob"):
    return TransferEvidence(
        asset_id=current.asset_id,
        prior_poo_digest=current.active_poo_digest,
        current_owner_id=current.claimant_id,
        recipient_id=recipient,
        title_transition_reference="title:alpha:transfer",
        recipient_control_key_fingerprint=key,
        recipient_work_reference="work:2",
        recipient_concept_reference="concept:2",
        recipient_coc_reference=coc_reference,
        recipient_stake_reference="stake:2",
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


def genesis_transition():
    c = coc("alice", "key:alice")
    return bootstrap_technical_state(ownership(coc_digest(c)), c)


def test_genesis_compare_and_swap_prepares_registry_without_committing():
    transition = genesis_transition()
    d = prepare_registry_commit([], transition, expected_registry_digest=registry_digest([]))
    assert d.commit_ready is True
    assert d.status == "REGISTRY_COMMIT_CANDIDATE_READY"
    assert len(d.candidate_states) == 1
    assert d.technical_registry_committed is False
    assert d.legal_title_changed is False
    assert d.live_value_moved is False
    assert d.external_transfer_executed is False


def test_stale_writer_digest_is_blocked():
    transition = genesis_transition()
    d = prepare_registry_commit([], transition, expected_registry_digest="stale")
    assert d.commit_ready is False
    assert "stale registry digest" in d.reasons


def test_second_bootstrap_for_existing_asset_is_blocked():
    first = genesis_transition()
    initial = prepare_registry_commit([], first, expected_registry_digest=registry_digest([]))
    current = list(initial.candidate_states)
    d = prepare_registry_commit(current, first, expected_registry_digest=registry_digest(current))
    assert d.commit_ready is False
    assert "candidate PoO already exists in registry" in d.reasons
    assert "bootstrap asset already exists in registry" in d.reasons


def transfer_transition(genesis, recipient="bob", key="key:bob"):
    c = coc(recipient, key, previous=genesis.active_coc_digest)
    t = transfer(genesis, coc_digest(c), recipient=recipient, key=key)
    return prepare_transfer_transition(genesis, t, c)


def test_transfer_commit_requires_active_poo_and_coc_tips():
    genesis = genesis_transition().candidate_state
    transition = transfer_transition(genesis)
    d = prepare_registry_commit(
        [genesis], transition, expected_registry_digest=registry_digest([genesis])
    )
    assert d.commit_ready is True
    candidate = d.candidate_states[-1]
    assert candidate.previous_poo_digest == genesis.active_poo_digest
    assert candidate.previous_coc_digest == genesis.active_coc_digest
    assert candidate.generation == 1


def test_stale_transfer_candidate_cannot_commit_after_tip_advanced():
    genesis = genesis_transition().candidate_state
    tr1 = transfer_transition(genesis, recipient="bob", key="key:bob")
    first_commit = prepare_registry_commit(
        [genesis], tr1, expected_registry_digest=registry_digest([genesis])
    )
    advanced = list(first_commit.candidate_states)

    stale_transition = transfer_transition(genesis, recipient="mallory", key="key:mallory")
    d = prepare_registry_commit(
        advanced, stale_transition, expected_registry_digest=registry_digest(advanced)
    )
    assert d.commit_ready is False
    assert "candidate predecessor is not the active PoO tip" in d.reasons


def test_replay_of_same_candidate_is_blocked():
    genesis = genesis_transition().candidate_state
    transition = transfer_transition(genesis)
    commit = prepare_registry_commit(
        [genesis], transition, expected_registry_digest=registry_digest([genesis])
    )
    advanced = list(commit.candidate_states)
    replay = prepare_registry_commit(
        advanced, transition, expected_registry_digest=registry_digest(advanced)
    )
    assert replay.commit_ready is False
    assert "candidate PoO already exists in registry" in replay.reasons
    assert "candidate technical state is a replay" in replay.reasons


def test_transition_claiming_external_authority_is_blocked():
    transition = replace(genesis_transition(), legal_title_changed=True)
    d = prepare_registry_commit([], transition, expected_registry_digest=registry_digest([]))
    assert d.commit_ready is False
    assert "transition asserts forbidden external authority" in d.reasons
