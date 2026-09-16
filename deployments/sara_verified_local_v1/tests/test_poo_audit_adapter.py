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
        "human_approval_required": True,
        "ownership_changed": False,
        "transfer_executed": False,
        "live_value_authorized": False,
        "legal_title_established": False,
        "legal_title_transferred": False,
        "control_rotated": False,
        "claim_boundary": "INTERNAL_POO_EVIDENCE_NOT_LEGAL_TITLE_OR_EXECUTION_AUTHORITY",
    }
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


@pytest.mark.parametrize(
    "field",
    [
        "ownership_changed",
        "transfer_executed",
        "live_value_authorized",
        "legal_title_established",
        "legal_title_transferred",
        "control_rotated",
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


def test_adapter_requires_actor():
    with pytest.raises(PoOAuditAdapterError, match="actor"):
        poo_outbox_events(projection(), actor="")
