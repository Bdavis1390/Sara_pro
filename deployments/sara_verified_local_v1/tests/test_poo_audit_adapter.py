from __future__ import annotations

import pytest

from worldshepherd_sara.event_outbox import drain_event_outbox, outbox_status
from worldshepherd_sara.poo_audit_adapter import (
    POO_AUDIT_SCHEMA,
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
        "transfer_ready": True,
        "recovery_ready": False,
        "lineage_checked": False,
        "lineage_valid": False,
        "fork_detected": False,
        "cycle_detected": False,
        "active_tip_digest": None,
        "lineage_issue_count": 0,
        "lineage_conflict_type": "NONE",
        "human_approval_required": True,
        "ownership_changed": False,
        "transfer_executed": False,
        "live_value_authorized": False,
        "legal_title_established": False,
        "legal_title_transferred": False,
        "control_rotated": False,
        "conflict_winner_selected": False,
        "lineage_auto_resolved": False,
        "claim_boundary": "INTERNAL_POO_EVIDENCE_NOT_LEGAL_TITLE_OR_EXECUTION_AUTHORITY",
    }
    value.update(overrides)
    return value


def lineage_projection(*, valid: bool = True, conflict_type: str = "NONE", **overrides):
    value = projection(
        operation="LINEAGE_INTEGRITY",
        source_digest="lineage:decision:001",
        source_status="LINEAGE_INTERNALLY_CONSISTENT" if valid else "LINEAGE_REVIEW_REQUIRED",
        previous_poo_digest=None,
        echo_state=(
            "ECHO_POO_LINEAGE_ACCEPTED"
            if valid
            else "ECHO_POO_LINEAGE_CONFLICT_CUSTODIED"
        ),
        prime_state="PRIME_POO_LINEAGE_ELIGIBLE" if valid else "PRIME_POO_LINEAGE_BLOCKED",
        sara_state="SARA_POO_LINEAGE_MONITORABLE" if valid else "SARA_POO_LINEAGE_DISPUTE_BLOCK",
        overwatch_state=(
            "OVERWATCH_POO_LINEAGE_HEALTHY"
            if valid
            else "OVERWATCH_POO_LINEAGE_CONFLICT_ACTIVE"
        ),
        transfer_ready=False,
        lineage_checked=True,
        lineage_valid=valid,
        fork_detected=(not valid and conflict_type in {"FORK", "MULTIPLE"}),
        cycle_detected=(not valid and conflict_type in {"CYCLE", "MULTIPLE"}),
        active_tip_digest="poo:tip:001" if valid else None,
        lineage_issue_count=0 if valid else 1,
        lineage_conflict_type=conflict_type,
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
    assert outbox_status(store.get_registry())["pending"] == 0

    records = [
        record
        for record in store.read_audit(50)
        if str(record.get("event", "")).startswith("poo_")
    ]
    assert len(records) == 4
    assert {record["payload"]["_outbox_event_id"] for record in records} == set(event_ids)
    assert all(record["payload"]["_delivery_semantics"] == "AT_LEAST_ONCE" for record in records)
    assert all(record["payload"]["ownership_changed"] is False for record in records)
    assert all(record["payload"]["transfer_executed"] is False for record in records)


def test_forked_lineage_persists_as_blocked_dispute_without_winner(tmp_path):
    store = DurableStore(tmp_path / "data")
    fork = lineage_projection(valid=False, conflict_type="FORK")

    def operation(registry):
        patch, ids = queue_poo_projection_patch(registry, fork, actor="SSPADAWANZZ")
        return patch, ids

    event_ids = store.transact_registry(operation)
    assert len(event_ids) == 4
    assert drain_event_outbox(store, limit=4) == 4

    records = [
        record
        for record in store.read_audit(50)
        if record.get("payload", {}).get("operation") == "LINEAGE_INTEGRITY"
    ]
    assert len(records) == 4
    assert {r["payload"]["lineage_conflict_type"] for r in records} == {"FORK"}
    assert all(r["payload"]["lineage_valid"] is False for r in records)
    assert all(r["payload"]["fork_detected"] is True for r in records)
    assert all(r["payload"]["active_tip_digest"] is None for r in records)
    assert all(r["payload"]["conflict_winner_selected"] is False for r in records)
    assert all(r["payload"]["lineage_auto_resolved"] is False for r in records)
    assert all(r["payload"]["transfer_ready"] is False for r in records)
    assert all(r["payload"]["recovery_ready"] is False for r in records)


@pytest.mark.parametrize(
    "field",
    [
        "ownership_changed",
        "transfer_executed",
        "live_value_authorized",
        "legal_title_established",
        "legal_title_transferred",
        "control_rotated",
        "conflict_winner_selected",
        "lineage_auto_resolved",
    ],
)
def test_adapter_rejects_authority_escalation(field):
    with pytest.raises(PoOAuditAdapterError, match=field):
        poo_outbox_events(projection(**{field: True}), actor="SSPADAWANZZ")


def test_adapter_requires_explicit_human_gate():
    with pytest.raises(PoOAuditAdapterError, match="human approval gate"):
        poo_outbox_events(
            projection(human_approval_required=False),
            actor="SSPADAWANZZ",
        )


def test_adapter_rejects_operation_readiness_mismatch():
    with pytest.raises(PoOAuditAdapterError, match="transfer_ready mismatches operation"):
        poo_outbox_events(
            projection(operation="OWNERSHIP_ATTESTATION", transfer_ready=True),
            actor="SSPADAWANZZ",
        )


def test_adapter_rejects_lineage_readiness_promotion():
    with pytest.raises(PoOAuditAdapterError, match="cannot grant ownership/transfer/recovery readiness"):
        poo_outbox_events(
            lineage_projection(valid=True, transfer_ready=True),
            actor="SSPADAWANZZ",
        )


def test_adapter_rejects_valid_lineage_without_active_tip():
    with pytest.raises(PoOAuditAdapterError, match="active_tip_digest"):
        poo_outbox_events(
            lineage_projection(valid=True, active_tip_digest=None),
            actor="SSPADAWANZZ",
        )


def test_adapter_rejects_invalid_lineage_without_issue():
    with pytest.raises(PoOAuditAdapterError, match="at least one issue"):
        poo_outbox_events(
            lineage_projection(valid=False, conflict_type="STRUCTURAL", lineage_issue_count=0),
            actor="SSPADAWANZZ",
        )


def test_adapter_rejects_fork_with_inconsistent_conflict_type():
    with pytest.raises(PoOAuditAdapterError, match="fork_detected conflicts"):
        poo_outbox_events(
            lineage_projection(
                valid=False,
                conflict_type="STRUCTURAL",
                fork_detected=True,
            ),
            actor="SSPADAWANZZ",
        )


def test_adapter_requires_actor():
    with pytest.raises(PoOAuditAdapterError, match="actor"):
        poo_outbox_events(projection(), actor="")
