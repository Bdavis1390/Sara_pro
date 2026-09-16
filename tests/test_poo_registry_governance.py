from dataclasses import replace

from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.registry_governance_guard import evaluate_governed_registry_commit
from security.poo.registry_guard import registry_digest
from security.poo.state_engine import bootstrap_technical_state
from security.poo.state_governance_guard import evaluate_governed_transfer_transition
from security.poo.transfer_guard import TransferEvidence


def coc(*, claimant: str, key: str, suffix: str, previous: str | None = None) -> COCEvidence:
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id=claimant,
        control_key_fingerprint=key,
        custody_reference=f"custody:{suffix}",
        custody_point_reference=f"point:{suffix}",
        challenge_reference=f"challenge:{suffix}",
        observed_at="2026-09-16T05:00:00Z",
        expires_at="2026-09-17T05:00:00Z",
        previous_coc_digest=previous,
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def genesis_state():
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


def transfer_and_coc(current):
    c1 = coc(
        claimant="claimant:two",
        key="key:002",
        suffix="002",
        previous=current.active_coc_digest,
    )
    c1d = evaluate_coc(c1).digest
    t = TransferEvidence(
        asset_id=current.asset_id,
        prior_poo_digest=current.active_poo_digest,
        current_owner_id=current.claimant_id,
        recipient_id="claimant:two",
        title_transition_reference="title:002",
        recipient_control_key_fingerprint="key:002",
        recipient_work_reference="work:002",
        recipient_concept_reference="concept:002",
        recipient_coc_reference=c1d,
        recipient_stake_reference="stake:002",
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
    return t, c1


def assert_non_authoritative(d):
    assert d.technical_registry_committed is False
    assert d.durable_registry_write_authorized is False
    assert d.conflict_winner_selected is False
    assert d.lineage_auto_resolved is False
    assert d.legal_title_changed is False
    assert d.live_value_moved is False
    assert d.external_transfer_executed is False


def test_full_governance_prepares_commit_candidate_without_durable_write():
    current = [genesis_state()]
    transfer, c = transfer_and_coc(current[0])
    governed = evaluate_governed_transfer_transition(current, transfer, c)
    decision = evaluate_governed_registry_commit(
        current,
        governed,
        expected_registry_digest=registry_digest(current),
    )
    assert governed.ready is True
    assert decision.ready is True
    assert decision.state_governance_ready is True
    assert decision.state_lineage_valid is True
    assert decision.optimistic_concurrency_checked is True
    assert decision.optimistic_concurrency_match is True
    assert decision.status == "REGISTRY_COMMIT_READY_WITH_FULL_GOVERNANCE"
    assert decision.commit_decision is not None and decision.commit_decision.commit_ready is True
    assert decision.candidate_registry_digest
    assert decision.candidate_state_digest == governed.candidate_state_digest
    assert_non_authoritative(decision)


def test_stale_snapshot_blocks_fully_ready_transition():
    current = [genesis_state()]
    transfer, c = transfer_and_coc(current[0])
    governed = evaluate_governed_transfer_transition(current, transfer, c)
    decision = evaluate_governed_registry_commit(
        current,
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


def test_state_lineage_failure_blocks_before_commit_guard_can_promote():
    current = [genesis_state()]
    broken = [replace(current[0], generation=1)]
    transfer, c = transfer_and_coc(broken[0])
    governed = evaluate_governed_transfer_transition(broken, transfer, c)
    decision = evaluate_governed_registry_commit(
        broken,
        governed,
        expected_registry_digest=registry_digest(broken),
    )
    assert governed.base_evidence_ready is True
    assert governed.state_lineage_valid is False
    assert decision.ready is False
    assert decision.status == "REGISTRY_COMMIT_BLOCKED_STATE_LINEAGE"
    assert decision.commit_decision is None
    assert_non_authoritative(decision)


def test_state_governance_failure_blocks_even_with_fresh_snapshot():
    current = [genesis_state()]
    transfer, c = transfer_and_coc(current[0])
    governed = evaluate_governed_transfer_transition(
        current,
        replace(transfer, prior_poo_digest="poo:stale"),
        c,
    )
    decision = evaluate_governed_registry_commit(
        current,
        governed,
        expected_registry_digest=registry_digest(current),
    )
    assert governed.state_lineage_valid is True
    assert governed.ready is False
    assert decision.optimistic_concurrency_match is True
    assert decision.ready is False
    assert decision.status == "REGISTRY_COMMIT_BLOCKED_STATE_GOVERNANCE"
    assert decision.commit_decision is None
    assert_non_authoritative(decision)


def test_governance_digest_binds_expected_registry_snapshot():
    current = [genesis_state()]
    transfer, c = transfer_and_coc(current[0])
    governed = evaluate_governed_transfer_transition(current, transfer, c)
    good = evaluate_governed_registry_commit(
        current,
        governed,
        expected_registry_digest=registry_digest(current),
    )
    stale = evaluate_governed_registry_commit(
        current,
        governed,
        expected_registry_digest="different",
    )
    assert good.digest != stale.digest
