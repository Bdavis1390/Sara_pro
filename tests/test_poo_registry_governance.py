from dataclasses import replace

from security.poo.coc_guard import COCEvidence
from security.poo.registry_governance_guard import evaluate_governed_registry_commit
from security.poo.registry_guard import registry_digest
from security.poo.state_engine import TechnicalOwnershipState
from security.poo.state_governance_guard import evaluate_governed_transfer_transition
from security.poo.transfer_guard import TransferEvidence


def state(
    *,
    claimant: str,
    poo: str,
    coc: str,
    generation: int,
    previous_poo: str | None,
    previous_coc: str | None,
    event: str,
    key: str,
) -> TechnicalOwnershipState:
    return TechnicalOwnershipState(
        schema="WS-POO-TECHNICAL-STATE-V1",
        asset_id="asset:alpha",
        claimant_id=claimant,
        active_poo_digest=poo,
        active_coc_digest=coc,
        control_key_fingerprint=key,
        title_reference=f"title:{generation}",
        generation=generation,
        source_event_type=event,
        previous_poo_digest=previous_poo,
        previous_coc_digest=previous_coc,
    )


def history():
    return [
        state(
            claimant="claimant:one",
            poo="poo:001",
            coc="coc:001",
            generation=0,
            previous_poo=None,
            previous_coc=None,
            event="CLAIM",
            key="key:001",
        ),
        state(
            claimant="claimant:two",
            poo="poo:002",
            coc="coc:002",
            generation=1,
            previous_poo="poo:001",
            previous_coc="coc:001",
            event="TRANSFER",
            key="key:002",
        ),
    ]


def transfer():
    return TransferEvidence(
        asset_id="asset:alpha",
        prior_poo_digest="poo:002",
        current_owner_id="claimant:two",
        recipient_id="claimant:three",
        title_transition_reference="title:3",
        recipient_control_key_fingerprint="key:003",
        recipient_work_reference="work:003",
        recipient_concept_reference="concept:003",
        recipient_stake_reference="stake:003",
        initiated_at="2026-09-16T05:00:00Z",
        expires_at="2026-09-17T05:00:00Z",
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


def coc():
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:three",
        control_key_fingerprint="key:003",
        custody_reference="custody:003",
        custody_point_reference="point:003",
        challenge_reference="challenge:003",
        observed_at="2026-09-16T05:00:00Z",
        expires_at="2026-09-17T05:00:00Z",
        previous_coc_digest="coc:002",
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def assert_non_authoritative(decision):
    assert decision.technical_registry_committed is False
    assert decision.durable_registry_write_authorized is False
    assert decision.conflict_winner_selected is False
    assert decision.lineage_auto_resolved is False
    assert decision.legal_title_changed is False
    assert decision.live_value_moved is False
    assert decision.external_transfer_executed is False


def test_full_governance_prepares_commit_candidate_without_committing():
    states = history()
    governed = evaluate_governed_transfer_transition(states, transfer(), coc())
    decision = evaluate_governed_registry_commit(
        states,
        governed,
        expected_registry_digest=registry_digest(states),
    )
    assert governed.ready is True
    assert decision.ready is True
    assert decision.state_governance_ready is True
    assert decision.state_lineage_valid is True
    assert decision.optimistic_concurrency_checked is True
    assert decision.optimistic_concurrency_match is True
    assert decision.status == "REGISTRY_COMMIT_READY_WITH_FULL_GOVERNANCE"
    assert decision.commit_decision is not None
    assert decision.commit_decision.commit_ready is True
    assert decision.candidate_registry_digest
    assert decision.candidate_state_digest == governed.candidate_state_digest
    assert_non_authoritative(decision)


def test_stale_registry_snapshot_blocks_otherwise_fully_ready_transition():
    states = history()
    governed = evaluate_governed_transfer_transition(states, transfer(), coc())
    decision = evaluate_governed_registry_commit(
        states,
        governed,
        expected_registry_digest="stale-registry-digest",
    )
    assert governed.ready is True
    assert decision.state_lineage_valid is True
    assert decision.optimistic_concurrency_checked is True
    assert decision.optimistic_concurrency_match is False
    assert decision.ready is False
    assert decision.status == "REGISTRY_COMMIT_BLOCKED_STALE_SNAPSHOT"
    assert "stale registry digest" in decision.reasons
    assert decision.candidate_registry_digest is None
    assert_non_authoritative(decision)


def test_invalid_state_lineage_blocks_before_registry_commit_candidate():
    states = history()
    states[1] = replace(states[1], previous_coc_digest="coc:wrong")
    governed = evaluate_governed_transfer_transition(states, transfer(), coc())
    decision = evaluate_governed_registry_commit(
        states,
        governed,
        expected_registry_digest=registry_digest(states),
    )
    assert governed.base_evidence_ready is True
    assert governed.state_lineage_valid is False
    assert decision.ready is False
    assert decision.state_lineage_valid is False
    assert decision.status == "REGISTRY_COMMIT_BLOCKED_STATE_LINEAGE"
    assert decision.commit_decision is None
    assert "state lineage is not internally consistent" in decision.reasons
    assert_non_authoritative(decision)


def test_state_governance_failure_blocks_even_with_fresh_registry_snapshot():
    states = history()
    stale_transfer = replace(transfer(), prior_poo_digest="poo:001")
    governed = evaluate_governed_transfer_transition(states, stale_transfer, coc())
    decision = evaluate_governed_registry_commit(
        states,
        governed,
        expected_registry_digest=registry_digest(states),
    )
    assert governed.state_lineage_valid is True
    assert governed.ready is False
    assert decision.optimistic_concurrency_match is True
    assert decision.ready is False
    assert decision.status == "REGISTRY_COMMIT_BLOCKED_STATE_GOVERNANCE"
    assert decision.commit_decision is None
    assert_non_authoritative(decision)


def test_governance_digest_binds_expected_registry_snapshot():
    states = history()
    governed = evaluate_governed_transfer_transition(states, transfer(), coc())
    current = evaluate_governed_registry_commit(
        states,
        governed,
        expected_registry_digest=registry_digest(states),
    )
    stale = evaluate_governed_registry_commit(
        states,
        governed,
        expected_registry_digest="different",
    )
    assert current.digest != stale.digest
