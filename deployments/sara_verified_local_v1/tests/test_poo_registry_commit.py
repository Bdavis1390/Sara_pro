from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from security.poo.audit_projection import registry_commit_readiness_audit_projection
from security.poo.bootstrap_audit_projection import bootstrap_commit_readiness_audit_projection
from security.poo.bootstrap_governance_guard import evaluate_governed_bootstrap_commit
from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.registry_governance_guard import evaluate_governed_registry_commit
from security.poo.registry_guard import registry_digest
from security.poo.state_engine import state_digest
from security.poo.state_governance_guard import evaluate_governed_transfer_transition
from security.poo.transfer_guard import TransferEvidence
from worldshepherd_sara.event_outbox import (
    EventOutboxError,
    MAX_PENDING_OUTBOX_EVENTS,
    queue_events_outbox_patch,
)
from worldshepherd_sara.poo_registry_commit import (
    POO_APPROVAL_INTENT,
    POO_TECHNICAL_REGISTRY_KEY,
    PoODurableCommitError,
    PoODurableCommitRequest,
    PoOTechnicalStateRecord,
    load_poo_registry_namespace,
    poo_registry_digest,
    poo_state_digest,
    prepare_poo_durable_commit_patch,
)
from worldshepherd_sara.storage import DurableStore


def coc(*, claimant: str, key: str, suffix: str, previous: str | None = None) -> COCEvidence:
    return COCEvidence(
        asset_id="asset:alpha",
        claimant_id=claimant,
        control_key_fingerprint=key,
        custody_reference=f"custody:{suffix}",
        custody_point_reference=f"point:{suffix}",
        challenge_reference=f"challenge:{suffix}",
        observed_at="2026-09-16T06:00:00Z",
        expires_at="2026-09-17T06:00:00Z",
        previous_coc_digest=previous,
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def genesis_material():
    c0 = coc(claimant="claimant:one", key="key:001", suffix="001")
    own = OwnershipEvidence(
        asset_id="asset:alpha",
        claimant_id="claimant:one",
        title_reference="title:001",
        control_key_fingerprint="key:001",
        work_reference="work:001",
        concept_reference="concept:001",
        coc_reference=evaluate_coc(c0).digest,
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
    decision = evaluate_governed_bootstrap_commit(
        [],
        own,
        c0,
        expected_registry_digest=registry_digest([]),
    )
    assert decision.ready is True
    assert decision.commit_decision is not None
    projection = bootstrap_commit_readiness_audit_projection(decision, asset_id="asset:alpha")
    states = [
        PoOTechnicalStateRecord.model_validate(asdict(state))
        for state in decision.commit_decision.candidate_states
    ]
    request = PoODurableCommitRequest(
        governance_projection=projection,
        candidate_states=states,
        approval_intent=POO_APPROVAL_INTENT,
        approval_reference="approval:bootstrap:001",
    )
    return decision, request


def transfer_material(current_state):
    c1 = coc(
        claimant="claimant:two",
        key="key:002",
        suffix="002",
        previous=current_state.active_coc_digest,
    )
    t = TransferEvidence(
        asset_id=current_state.asset_id,
        prior_poo_digest=current_state.active_poo_digest,
        current_owner_id=current_state.claimant_id,
        recipient_id="claimant:two",
        title_transition_reference="title:002",
        recipient_control_key_fingerprint="key:002",
        recipient_work_reference="work:002",
        recipient_concept_reference="concept:002",
        recipient_coc_reference=evaluate_coc(c1).digest,
        recipient_stake_reference="stake:002",
        initiated_at="2026-09-16T06:00:00Z",
        expires_at="2026-09-17T06:00:00Z",
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
    current = [current_state]
    governed = evaluate_governed_transfer_transition(current, t, c1)
    assert governed.ready is True
    decision = evaluate_governed_registry_commit(
        current,
        governed,
        expected_registry_digest=registry_digest(current),
    )
    assert decision.ready is True
    assert decision.commit_decision is not None
    projection = registry_commit_readiness_audit_projection(
        decision,
        asset_id=current_state.asset_id,
        previous_poo_digest=current_state.active_poo_digest,
    )
    states = [
        PoOTechnicalStateRecord.model_validate(asdict(state))
        for state in decision.commit_decision.candidate_states
    ]
    request = PoODurableCommitRequest(
        governance_projection=projection,
        candidate_states=states,
        approval_intent=POO_APPROVAL_INTENT,
        approval_reference="approval:transfer:002",
    )
    return decision, request


def apply_patch(registry: dict, patch: dict | None) -> dict:
    updated = dict(registry)
    if patch:
        updated.update(patch)
    return updated


def test_sara_state_and_registry_digests_match_security_reference():
    decision, request = genesis_material()
    state = decision.commit_decision.candidate_states[0]
    sara_state = request.candidate_states[0]
    assert poo_state_digest(sara_state) == state_digest(state)
    assert poo_registry_digest(request.candidate_states) == registry_digest([state])


def test_empty_registry_bootstrap_is_governed_and_committed_with_audit_intent():
    _decision, request = genesis_material()
    patch, result = prepare_poo_durable_commit_patch(
        {}, request, actor="admin", committed_at="2026-09-16T06:05:00+00:00"
    )
    assert patch is not None
    assert result.status == "COMMITTED"
    assert result.durable_internal_state_committed is True
    assert result.legal_title_changed is False
    assert result.live_value_moved is False
    assert result.credential_rotated is False
    assert result.external_transfer_executed is False
    updated = apply_patch({}, patch)
    namespace = load_poo_registry_namespace(updated)
    assert len(namespace.states) == 1
    assert len(namespace.commits) == 1
    assert namespace.registry_digest == result.registry_digest
    outbox = updated["SARA_EVENT_OUTBOX"]
    assert result.audit_event_id in outbox
    assert outbox[result.audit_event_id]["status"] == "PENDING"
    assert outbox[result.audit_event_id]["delivery_semantics"] == "AT_LEAST_ONCE"


def test_exact_retry_is_idempotent_and_does_not_append_second_state():
    _decision, request = genesis_material()
    patch, first = prepare_poo_durable_commit_patch({}, request, actor="admin")
    registry = apply_patch({}, patch)
    retry_patch, second = prepare_poo_durable_commit_patch(registry, request, actor="admin")
    assert first.commit_id == second.commit_id
    assert retry_patch is None
    assert second.status == "ALREADY_COMMITTED"
    assert len(load_poo_registry_namespace(registry).states) == 1


def test_transfer_extends_durable_genesis_by_exactly_one_state():
    bootstrap_decision, bootstrap_request = genesis_material()
    patch, _first = prepare_poo_durable_commit_patch({}, bootstrap_request, actor="admin")
    registry = apply_patch({}, patch)
    current_state = bootstrap_decision.commit_decision.candidate_states[0]
    _transfer_decision, transfer_request = transfer_material(current_state)
    patch2, result2 = prepare_poo_durable_commit_patch(registry, transfer_request, actor="admin")
    updated = apply_patch(registry, patch2)
    namespace = load_poo_registry_namespace(updated)
    assert result2.status == "COMMITTED"
    assert len(namespace.states) == 2
    assert len(namespace.commits) == 2
    assert namespace.registry_digest == result2.registry_digest


def test_stale_registry_snapshot_blocks_without_mutation():
    bootstrap_decision, bootstrap_request = genesis_material()
    patch, _ = prepare_poo_durable_commit_patch({}, bootstrap_request, actor="admin")
    registry = apply_patch({}, patch)
    current_state = bootstrap_decision.commit_decision.candidate_states[0]
    _decision, transfer_request = transfer_material(current_state)
    stale = transfer_request.model_copy(deep=True)
    stale.governance_projection["expected_registry_digest"] = "stale"
    stale.governance_projection["current_registry_digest"] = "stale"
    with pytest.raises(PoODurableCommitError):
        prepare_poo_durable_commit_patch(registry, stale, actor="admin")
    assert load_poo_registry_namespace(registry).registry_digest == load_poo_registry_namespace(registry).registry_digest


def test_candidate_cannot_remove_or_modify_existing_state_even_with_matching_submitted_digest():
    bootstrap_decision, bootstrap_request = genesis_material()
    patch, _ = prepare_poo_durable_commit_patch({}, bootstrap_request, actor="admin")
    registry = apply_patch({}, patch)
    current_state = bootstrap_decision.commit_decision.candidate_states[0]
    _decision, transfer_request = transfer_material(current_state)
    mutated = transfer_request.model_copy(deep=True)
    mutated.candidate_states[0] = mutated.candidate_states[0].model_copy(update={"title_reference": "title:tampered"})
    mutated.governance_projection["candidate_registry_digest"] = poo_registry_digest(mutated.candidate_states)
    with pytest.raises(PoODurableCommitError, match="modifies or removes existing"):
        prepare_poo_durable_commit_patch(registry, mutated, actor="admin")


def test_authority_escalation_in_v3_projection_is_rejected():
    bootstrap_decision, bootstrap_request = genesis_material()
    patch, _ = prepare_poo_durable_commit_patch({}, bootstrap_request, actor="admin")
    registry = apply_patch({}, patch)
    current_state = bootstrap_decision.commit_decision.candidate_states[0]
    _decision, transfer_request = transfer_material(current_state)
    forged = transfer_request.model_copy(deep=True)
    forged.governance_projection["durable_registry_write_authorized"] = True
    with pytest.raises(PoODurableCommitError, match="invalid PoO governance projection"):
        prepare_poo_durable_commit_patch(registry, forged, actor="admin")


def test_outbox_capacity_failure_aborts_state_commit(tmp_path):
    store = DurableStore(tmp_path / "data")
    events = [
        {"event": "capacity_probe", "actor": "test", "payload": {"index": i}}
        for i in range(MAX_PENDING_OUTBOX_EVENTS)
    ]

    def seed(registry):
        patch, _ids = queue_events_outbox_patch(registry, events)
        return patch, None

    store.transact_registry(seed)
    before = store.get_registry()
    _decision, request = genesis_material()

    def operation(registry):
        return prepare_poo_durable_commit_patch(registry, request, actor="admin")

    with pytest.raises(EventOutboxError, match="capacity"):
        store.transact_registry(operation)
    after = store.get_registry()
    assert after == before
    assert POO_TECHNICAL_REGISTRY_KEY not in after
