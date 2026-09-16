from __future__ import annotations

import pytest

from worldshepherd_sara.event_outbox import drain_event_outbox, outbox_status
from worldshepherd_sara.poo_audit_adapter import (
    POO_AUDIT_SCHEMA,
    POO_EVENT_SCHEMA,
    PoOAuditAdapterError,
    poo_outbox_events,
    queue_poo_projection_patch,
)
from worldshepherd_sara.storage import DurableStore


def projection(**overrides):
    value = {
        "schema": POO_AUDIT_SCHEMA,
        "operation": "TRANSFER_READINESS",
        "asset_id": "asset:alpha",
        "source_digest": "source:decision:001",
        "source_status": "READY_FOR_GOVERNED_SUPERSESSION",
        "previous_poo_digest": "prior:001",
        "echo_state": "ECHO_POO_TRANSFER_EVIDENCE_ACCEPTED",
        "prime_state": "PRIME_POO_TRANSFER_READY",
        "sara_state": "SARA_POO_TRANSFER_HUMAN_REVIEW_READY",
        "overwatch_state": "OVERWATCH_POO_TRANSFER_PENDING_SUPERSESSION",
        "technical_attestation_ready": False,
        "coc_valid": False,
        "transfer_ready": True,
        "recovery_ready": False,
        "state_transition_ready": False,
        "registry_consistent": False,
        "state_lineage_checked": False,
        "state_lineage_valid": False,
        "poo_lineage_valid": False,
        "coc_lineage_valid": False,
        "generation_valid": False,
        "fork_detected": False,
        "cycle_detected": False,
        "active_tip_digest": None,
        "lineage_issue_count": 0,
        "registry_commit_ready": False,
        "optimistic_concurrency_checked": False,
        "optimistic_concurrency_match": False,
        "expected_registry_digest": None,
        "current_registry_digest": None,
        "candidate_registry_digest": None,
        "candidate_state_digest": None,
        "human_approval_required": True,
        "ownership_changed": False,
        "transfer_executed": False,
        "live_value_authorized": False,
        "legal_title_established": False,
        "legal_title_transferred": False,
        "control_rotated": False,
        "technical_registry_committed": False,
        "durable_registry_write_authorized": False,
        "conflict_winner_selected": False,
        "lineage_auto_resolved": False,
        "claim_boundary": "INTERNAL_POO_EVIDENCE_NOT_LEGAL_TITLE_OR_EXECUTION_AUTHORITY",
    }
    value.update(overrides)
    return value


def for_operation(operation, readiness_field):
    value = projection(
        operation=operation,
        transfer_ready=False,
        previous_poo_digest=None,
    )
    value[readiness_field] = True
    return value


def valid_lineage_projection(**overrides):
    value = projection(
        operation="STATE_LINEAGE_INTEGRITY",
        transfer_ready=False,
        previous_poo_digest=None,
        source_status="STATE_LINEAGE_INTERNALLY_CONSISTENT:NONE",
        echo_state="ECHO_POO_STATE_LINEAGE_ACCEPTED",
        prime_state="PRIME_POO_STATE_LINEAGE_ELIGIBLE",
        sara_state="SARA_POO_STATE_LINEAGE_MONITORABLE",
        overwatch_state="OVERWATCH_POO_STATE_LINEAGE_HEALTHY",
        state_lineage_checked=True,
        state_lineage_valid=True,
        poo_lineage_valid=True,
        coc_lineage_valid=True,
        generation_valid=True,
        active_tip_digest="poo:tip:001",
        lineage_issue_count=0,
    )
    value.update(overrides)
    return value


def invalid_lineage_projection(**overrides):
    value = valid_lineage_projection(
        source_status="STATE_LINEAGE_REVIEW_REQUIRED:FORK",
        echo_state="ECHO_POO_STATE_LINEAGE_CONFLICT_CUSTODIED",
        prime_state="PRIME_POO_STATE_LINEAGE_BLOCKED",
        sara_state="SARA_POO_STATE_LINEAGE_DISPUTE_BLOCK",
        overwatch_state="OVERWATCH_POO_STATE_LINEAGE_CONFLICT_ACTIVE",
        state_lineage_valid=False,
        poo_lineage_valid=False,
        coc_lineage_valid=True,
        generation_valid=False,
        fork_detected=True,
        active_tip_digest=None,
        lineage_issue_count=2,
    )
    value.update(overrides)
    return value


def governed_state_projection(**overrides):
    value = projection(
        operation="GOVERNED_STATE_TRANSITION",
        transfer_ready=False,
        previous_poo_digest="poo:tip:001",
        source_status="STATE_TRANSFER_READY_WITH_LINEAGE_GUARD",
        echo_state="ECHO_POO_GOVERNED_STATE_CANDIDATE_ACCEPTED",
        prime_state="PRIME_POO_GOVERNED_STATE_TRANSITION_READY",
        sara_state="SARA_POO_GOVERNED_STATE_HUMAN_REVIEW_READY",
        overwatch_state="OVERWATCH_POO_GOVERNED_STATE_PENDING_COMMIT",
        state_transition_ready=True,
        state_lineage_checked=True,
        state_lineage_valid=True,
        poo_lineage_valid=True,
        coc_lineage_valid=True,
        generation_valid=True,
        active_tip_digest="poo:tip:001",
        lineage_issue_count=0,
        candidate_state_digest="state:candidate:001",
    )
    value.update(overrides)
    return value


def commit_projection(**overrides):
    value = projection(
        operation="REGISTRY_COMMIT_READINESS",
        transfer_ready=False,
        previous_poo_digest="poo:tip:001",
        source_status="REGISTRY_COMMIT_READY_WITH_FULL_GOVERNANCE",
        echo_state="ECHO_POO_REGISTRY_COMMIT_EVIDENCE_ACCEPTED",
        prime_state="PRIME_POO_REGISTRY_COMMIT_CANDIDATE_READY",
        sara_state="SARA_POO_REGISTRY_COMMIT_HUMAN_REVIEW_READY",
        overwatch_state="OVERWATCH_POO_REGISTRY_COMMIT_PENDING",
        state_lineage_checked=True,
        state_lineage_valid=True,
        poo_lineage_valid=True,
        coc_lineage_valid=True,
        generation_valid=True,
        active_tip_digest="poo:tip:001",
        lineage_issue_count=0,
        registry_commit_ready=True,
        optimistic_concurrency_checked=True,
        optimistic_concurrency_match=True,
        expected_registry_digest="registry:current:001",
        current_registry_digest="registry:current:001",
        candidate_registry_digest="registry:candidate:002",
        candidate_state_digest="state:candidate:002",
    )
    value.update(overrides)
    return value


def stale_commit_projection(**overrides):
    value = commit_projection(
        source_status="REGISTRY_COMMIT_BLOCKED_STALE_SNAPSHOT",
        echo_state="ECHO_POO_REGISTRY_STALE_SNAPSHOT_RECORDED",
        prime_state="PRIME_POO_REGISTRY_COMMIT_BLOCKED_STALE",
        sara_state="SARA_POO_REGISTRY_COMMIT_REEVALUATION_REQUIRED",
        overwatch_state="OVERWATCH_POO_REGISTRY_STALE_SNAPSHOT_ALERT",
        registry_commit_ready=False,
        optimistic_concurrency_match=False,
        expected_registry_digest="registry:old",
        current_registry_digest="registry:new",
        candidate_registry_digest=None,
    )
    value.update(overrides)
    return value


def test_projection_maps_to_four_native_sara_events():
    events = poo_outbox_events(projection(), actor="SSPADAWANZZ")
    assert [item["event"] for item in events] == [
        "poo_echo_state",
        "poo_prime_state",
        "poo_sara_state",
        "poo_overwatch_state",
    ]
    assert [item["payload"]["stage"] for item in events] == [
        "ECHO",
        "PRIME",
        "SARA",
        "OVERWATCH",
    ]
    assert {item["payload"]["schema"] for item in events} == {POO_EVENT_SCHEMA}
    instance_ids = {item["payload"]["audit_instance_id"] for item in events}
    assert len(instance_ids) == 1
    for item in events:
        payload = item["payload"]
        assert payload["human_approval_required"] is True
        assert payload["ownership_changed"] is False
        assert payload["transfer_executed"] is False
        assert payload["live_value_authorized"] is False
        assert payload["legal_title_established"] is False
        assert payload["legal_title_transferred"] is False
        assert payload["control_rotated"] is False
        assert payload["technical_registry_committed"] is False
        assert payload["durable_registry_write_authorized"] is False
        assert payload["conflict_winner_selected"] is False
        assert payload["lineage_auto_resolved"] is False


def test_projection_persists_through_native_outbox_and_audit_log(tmp_path):
    store = DurableStore(tmp_path / "data")

    def operation(registry):
        patch, ids = queue_poo_projection_patch(
            registry,
            projection(),
            actor="SSPADAWANZZ",
        )
        return patch, ids

    event_ids = store.transact_registry(operation)
    assert len(event_ids) == 4
    assert len(set(event_ids)) == 4
    assert outbox_status(store.get_registry()) == {
        "pending": 4,
        "delivered_retained": 0,
        "malformed": 0,
    }
    assert drain_event_outbox(store, limit=4) == 4
    records = [r for r in store.read_audit(50) if str(r.get("event", "")).startswith("poo_")]
    assert len(records) == 4
    assert {record["payload"]["_outbox_event_id"] for record in records} == set(event_ids)
    assert all(record["payload"]["_delivery_semantics"] == "AT_LEAST_ONCE" for record in records)
    assert all(record["payload"]["technical_registry_committed"] is False for record in records)


@pytest.mark.parametrize(
    "operation,field",
    [
        ("OWNERSHIP_ATTESTATION", "technical_attestation_ready"),
        ("COC_ATTESTATION", "coc_valid"),
        ("TRANSFER_READINESS", "transfer_ready"),
        ("RECOVERY_READINESS", "recovery_ready"),
        ("TECHNICAL_STATE_TRANSITION", "state_transition_ready"),
        ("REGISTRY_HEALTH", "registry_consistent"),
    ],
)
def test_non_lineage_operations_accept_only_their_own_primary_readiness_flag(operation, field):
    value = for_operation(operation, field)
    if operation == "TECHNICAL_STATE_TRANSITION":
        value["candidate_state_digest"] = "state:candidate"
    events = poo_outbox_events(value, actor="SSPADAWANZZ")
    assert len(events) == 4
    assert all(item["payload"][field] is True for item in events)
    assert all(item["payload"]["state_lineage_checked"] is False for item in events)


def test_valid_state_lineage_is_auditable_without_granting_transition_readiness():
    events = poo_outbox_events(valid_lineage_projection(), actor="SSPADAWANZZ")
    assert len(events) == 4
    assert all(item["payload"]["state_lineage_valid"] is True for item in events)
    assert all(item["payload"]["state_transition_ready"] is False for item in events)
    assert all(item["payload"]["registry_commit_ready"] is False for item in events)


def test_invalid_lineage_persists_as_dispute_without_active_tip_or_winner(tmp_path):
    store = DurableStore(tmp_path / "data")
    value = invalid_lineage_projection()

    def operation(registry):
        return queue_poo_projection_patch(registry, value, actor="SSPADAWANZZ")

    ids = store.transact_registry(operation)
    assert len(ids) == 4
    assert drain_event_outbox(store, limit=4) == 4
    records = [r for r in store.read_audit(50) if r.get("payload", {}).get("operation") == "STATE_LINEAGE_INTEGRITY"]
    assert len(records) == 4
    assert all(r["payload"]["state_lineage_valid"] is False for r in records)
    assert all(r["payload"]["active_tip_digest"] is None for r in records)
    assert all(r["payload"]["conflict_winner_selected"] is False for r in records)
    assert all(r["payload"]["lineage_auto_resolved"] is False for r in records)


def test_governed_state_ready_requires_active_tip_binding():
    events = poo_outbox_events(governed_state_projection(), actor="SSPADAWANZZ")
    assert len(events) == 4
    assert all(item["payload"]["state_transition_ready"] is True for item in events)
    assert all(item["payload"]["state_lineage_valid"] is True for item in events)
    assert all(item["payload"]["previous_poo_digest"] == item["payload"]["active_tip_digest"] for item in events)


def test_registry_commit_readiness_persists_full_governance_evidence_without_commit(tmp_path):
    store = DurableStore(tmp_path / "data")
    value = commit_projection()

    def operation(registry):
        return queue_poo_projection_patch(registry, value, actor="SSPADAWANZZ")

    ids = store.transact_registry(operation)
    assert len(ids) == 4
    assert drain_event_outbox(store, limit=4) == 4
    records = [r for r in store.read_audit(50) if r.get("payload", {}).get("operation") == "REGISTRY_COMMIT_READINESS"]
    assert len(records) == 4
    assert all(r["payload"]["registry_commit_ready"] is True for r in records)
    assert all(r["payload"]["optimistic_concurrency_checked"] is True for r in records)
    assert all(r["payload"]["optimistic_concurrency_match"] is True for r in records)
    assert all(r["payload"]["technical_registry_committed"] is False for r in records)
    assert all(r["payload"]["durable_registry_write_authorized"] is False for r in records)


def test_stale_snapshot_is_auditable_but_not_commit_ready():
    events = poo_outbox_events(stale_commit_projection(), actor="SSPADAWANZZ")
    assert len(events) == 4
    assert all(item["payload"]["registry_commit_ready"] is False for item in events)
    assert all(item["payload"]["optimistic_concurrency_match"] is False for item in events)
    assert all(item["payload"]["candidate_registry_digest"] is None for item in events)


@pytest.mark.parametrize(
    "field",
    [
        "ownership_changed",
        "transfer_executed",
        "live_value_authorized",
        "legal_title_established",
        "legal_title_transferred",
        "control_rotated",
        "technical_registry_committed",
        "durable_registry_write_authorized",
        "conflict_winner_selected",
        "lineage_auto_resolved",
    ],
)
def test_adapter_rejects_authority_escalation(field):
    with pytest.raises(PoOAuditAdapterError, match=field):
        poo_outbox_events(projection(**{field: True}), actor="SSPADAWANZZ")


def test_adapter_requires_explicit_human_gate():
    with pytest.raises(PoOAuditAdapterError, match="human approval gate"):
        poo_outbox_events(projection(human_approval_required=False), actor="SSPADAWANZZ")


def test_state_transition_cannot_smuggle_transfer_readiness():
    value = for_operation("TECHNICAL_STATE_TRANSITION", "state_transition_ready")
    value["candidate_state_digest"] = "state:candidate"
    value["transfer_ready"] = True
    with pytest.raises(PoOAuditAdapterError, match="transfer_ready mismatches operation"):
        poo_outbox_events(value, actor="SSPADAWANZZ")


def test_governed_state_ready_rejects_stale_predecessor():
    with pytest.raises(PoOAuditAdapterError, match="previous_poo_digest to equal active_tip_digest"):
        poo_outbox_events(
            governed_state_projection(previous_poo_digest="poo:stale"),
            actor="SSPADAWANZZ",
        )


def test_valid_lineage_cannot_claim_issues():
    with pytest.raises(PoOAuditAdapterError, match="zero lineage issues"):
        poo_outbox_events(
            valid_lineage_projection(lineage_issue_count=1),
            actor="SSPADAWANZZ",
        )


def test_invalid_lineage_cannot_expose_active_tip():
    with pytest.raises(PoOAuditAdapterError, match="cannot expose active_tip_digest"):
        poo_outbox_events(
            invalid_lineage_projection(active_tip_digest="poo:fake-tip"),
            actor="SSPADAWANZZ",
        )


def test_commit_ready_rejects_stale_snapshot_claim():
    with pytest.raises(PoOAuditAdapterError, match="conflicts with registry digests"):
        poo_outbox_events(
            commit_projection(current_registry_digest="registry:new"),
            actor="SSPADAWANZZ",
        )


def test_commit_ready_requires_candidate_digests():
    with pytest.raises(PoOAuditAdapterError, match="candidate registry/state digests"):
        poo_outbox_events(
            commit_projection(candidate_registry_digest=None),
            actor="SSPADAWANZZ",
        )


def test_registry_health_persists_as_evidence_not_authority(tmp_path):
    store = DurableStore(tmp_path / "data")
    value = for_operation("REGISTRY_HEALTH", "registry_consistent")
    value.update(
        asset_id="registry:technical-ownership",
        source_status="TECHNICAL_REGISTRY_INTERNALLY_CONSISTENT",
        echo_state="ECHO_POO_REGISTRY_SNAPSHOT_ACCEPTED",
        prime_state="PRIME_POO_REGISTRY_CONSISTENT",
        sara_state="SARA_POO_REGISTRY_REVIEW_READY",
        overwatch_state="OVERWATCH_POO_REGISTRY_HEALTHY",
    )

    def operation(registry):
        return queue_poo_projection_patch(registry, value, actor="SSPADAWANZZ")

    ids = store.transact_registry(operation)
    assert len(ids) == 4
    assert drain_event_outbox(store, limit=4) == 4
    records = [r for r in store.read_audit(50) if str(r.get("event", "")).startswith("poo_")]
    assert len(records) == 4
    assert all(r["payload"]["registry_consistent"] is True for r in records)
    assert all(r["payload"]["legal_title_established"] is False for r in records)


def test_adapter_requires_actor():
    with pytest.raises(PoOAuditAdapterError, match="actor"):
        poo_outbox_events(projection(), actor="")
