from __future__ import annotations

import pytest

from worldshepherd_sara.event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    MAX_PENDING_OUTBOX_EVENTS,
    EventOutboxError,
    drain_event_outbox,
    outbox_status,
    pending_event_ids,
    queue_event_outbox_patch,
    queue_events_outbox_patch,
)
from worldshepherd_sara.storage import DurableStore


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def queue_fixed_event(store: DurableStore, event_id: str = "SARA-EVENT-TEST-001") -> str:
    def operation(registry):
        patch, stable_id = queue_event_outbox_patch(
            registry,
            event="test_provenance",
            actor="test",
            payload={"step": "queued"},
            event_id=event_id,
        )
        return patch, stable_id

    return store.transact_registry(operation)


def test_queue_and_drain_preserves_stable_event_id(tmp_path):
    store = DurableStore(tmp_path / "data")
    event_id = queue_fixed_event(store)

    assert outbox_status(store.get_registry()) == {
        "pending": 1,
        "delivered_retained": 0,
        "malformed": 0,
    }
    assert drain_event_outbox(store, limit=1) == 1
    assert outbox_status(store.get_registry()) == {
        "pending": 0,
        "delivered_retained": 1,
        "malformed": 0,
    }

    matching = [
        record
        for record in store.read_audit(50)
        if record.get("event") == "test_provenance"
    ]
    assert len(matching) == 1
    assert matching[0]["payload"]["_outbox_event_id"] == event_id
    assert matching[0]["payload"]["_delivery_semantics"] == "AT_LEAST_ONCE"


def test_audit_append_failure_leaves_event_pending(tmp_path, monkeypatch):
    store = DurableStore(tmp_path / "data")
    event_id = queue_fixed_event(store)

    def fail_append(_record):
        raise OSError("simulated audit failure")

    monkeypatch.setattr(store, "append_audit", fail_append)
    with pytest.raises(OSError, match="simulated audit failure"):
        drain_event_outbox(store, limit=1)

    assert pending_event_ids(store.get_registry()) == [event_id]
    assert store.read_audit(50) == []


def test_delivery_mark_failure_replays_same_event_id_at_least_once(tmp_path, monkeypatch):
    store = DurableStore(tmp_path / "data")
    event_id = queue_fixed_event(store)
    original_atomic_write = store._atomic_write_json

    def fail_delivery_mark(_path, _value):
        raise OSError("simulated delivery-mark failure")

    monkeypatch.setattr(store, "_atomic_write_json", fail_delivery_mark)
    with pytest.raises(OSError, match="simulated delivery-mark failure"):
        drain_event_outbox(store, limit=1)

    first_records = [
        record
        for record in store.read_audit(50)
        if record.get("event") == "test_provenance"
    ]
    assert len(first_records) == 1
    assert first_records[0]["payload"]["_outbox_event_id"] == event_id
    assert pending_event_ids(store.get_registry()) == [event_id]

    monkeypatch.setattr(store, "_atomic_write_json", original_atomic_write)
    recovered = DurableStore(store.root)
    assert drain_event_outbox(recovered, limit=1) == 1

    replayed = [
        record
        for record in recovered.read_audit(50)
        if record.get("event") == "test_provenance"
    ]
    assert len(replayed) == 2
    assert {record["payload"]["_outbox_event_id"] for record in replayed} == {event_id}
    assert all(
        record["payload"]["_delivery_semantics"] == "AT_LEAST_ONCE"
        for record in replayed
    )
    assert outbox_status(recovered.get_registry())["pending"] == 0


def test_multiple_events_share_one_atomic_outbox_patch(tmp_path):
    store = DurableStore(tmp_path / "data")

    def operation(registry):
        patch, ids = queue_events_outbox_patch(
            registry,
            [
                {"event": "first", "actor": "test", "payload": {"order": 1}},
                {"event": "second", "actor": "test", "payload": {"order": 2}},
            ],
        )
        return patch, ids

    ids = store.transact_registry(operation)
    assert len(ids) == 2
    assert len(set(ids)) == 2
    assert outbox_status(store.get_registry())["pending"] == 2
    assert set(pending_event_ids(store.get_registry())) == set(ids)


def test_malformed_outbox_record_is_reported_and_not_delivered(tmp_path):
    store = DurableStore(tmp_path / "data")
    store.patch_registry(
        {
            EVENT_OUTBOX_REGISTRY_KEY: {
                "SARA-EVENT-BAD": {
                    "status": "PENDING",
                    "event_id": "different-id",
                }
            }
        }
    )

    status = outbox_status(store.get_registry())
    assert status["malformed"] == 1
    assert status["pending"] == 0
    assert pending_event_ids(store.get_registry()) == []
    with pytest.raises(EventOutboxError, match="malformed"):
        drain_event_outbox(store, limit=1)


def test_reserved_delivery_metadata_cannot_be_spoofed():
    with pytest.raises(EventOutboxError, match="reserved outbox keys"):
        queue_event_outbox_patch(
            {},
            event="test",
            actor="test",
            payload={"_outbox_event_id": "spoofed"},
        )


def test_outbox_namespace_is_protected_from_generic_admin_patch(client, tokens):
    _, admin = tokens
    response = client.patch(
        "/admin/registry",
        headers=auth(admin),
        json={"values": {EVENT_OUTBOX_REGISTRY_KEY: {}}},
    )
    assert response.status_code == 403


def test_prime_state_and_outbox_survive_immediate_audit_delivery_failure(
    client, tokens, monkeypatch
):
    _, admin = tokens
    store = client.app.state.store
    original_append = store.append_audit

    def fail_append(_record):
        raise OSError("simulated immediate audit delivery failure")

    monkeypatch.setattr(store, "append_audit", fail_append)
    response = client.post(
        "/admin/prime/PRIME-OUTBOX-001/passport",
        headers=auth(admin),
        json={
            "hardware_revision": "HW-1",
            "software_revision": "SW-1",
            "evidence_refs": ["TEST-EVIDENCE-1"],
        },
    )
    assert response.status_code == 201
    assert response.json()["provenance_delivery"] == "PENDING_REPLAY"

    registry = store.get_registry()
    assert "PRIME-OUTBOX-001" in registry["PRIME_DIGITAL_PASSPORTS"]
    assert outbox_status(registry)["pending"] == 1

    monkeypatch.setattr(store, "append_audit", original_append)
    assert drain_event_outbox(store, limit=1) == 1
    assert outbox_status(store.get_registry())["pending"] == 0


def test_mission_completion_quarantines_even_when_outbox_is_saturated(client, tokens):
    _, admin = tokens
    store = client.app.state.store
    created = client.post(
        "/admin/prime/PRIME-OUTBOX-SAFE/passport",
        headers=auth(admin),
        json={
            "hardware_revision": "HW-1",
            "software_revision": "SW-1",
            "evidence_refs": ["TEST-EVIDENCE-1"],
        },
    )
    assert created.status_code == 201
    assert created.json()["passport"]["custody"]["state"] == "READY"

    def saturate(registry):
        events = [
            {
                "event": "synthetic_pending",
                "actor": "test",
                "payload": {"index": index},
                "event_id": f"SARA-EVENT-SAT-{index:02d}",
            }
            for index in range(MAX_PENDING_OUTBOX_EVENTS)
        ]
        patch, _ids = queue_events_outbox_patch(registry, events)
        return patch, None

    store.transact_registry(saturate)
    assert outbox_status(store.get_registry())["pending"] == MAX_PENDING_OUTBOX_EVENTS

    mission = client.post(
        "/admin/prime/PRIME-OUTBOX-SAFE/mission-complete",
        headers=auth(admin),
        json={
            "environment": "HADAL",
            "evidence_refs": ["TEST-MISSION-HADAL-1"],
        },
    )
    assert mission.status_code == 200
    body = mission.json()
    assert body["passport"]["custody"]["state"] == "QUARANTINED_FOR_REQUALIFICATION"
    assert body["provenance_delivery"] == "DEGRADED_DIRECT_AUDIT"
    assert body["provenance_event_ids"] == []
    assert body["provenance"]["details"]["provenance_outbox"] == (
        "BYPASSED_FAIL_SAFE_QUARANTINE"
    )

    persisted = client.get(
        "/admin/prime/PRIME-OUTBOX-SAFE/passport",
        headers=auth(admin),
    )
    assert persisted.status_code == 200
    assert persisted.json()["passport"]["custody"]["state"] == (
        "QUARANTINED_FOR_REQUALIFICATION"
    )



def test_replay_after_partial_audit_tail_preserves_a_valid_event(tmp_path):
    store = DurableStore(tmp_path / "data")
    event_id = queue_fixed_event(store, "SARA-EVENT-PARTIAL-001")
    store.audit_path.write_bytes(b'{"event":"interrupted"')
    assert drain_event_outbox(store, limit=1) == 1
    records = store.read_audit(50)
    assert records[0] == {"event": "audit_corruption_detected", "reason": "invalid_line"}
    delivered = [item for item in records if item.get("event") == "test_provenance"]
    assert len(delivered) == 1
    assert delivered[0]["payload"]["_outbox_event_id"] == event_id
    assert outbox_status(store.get_registry())["pending"] == 0
    assert store.audit_path.read_bytes().endswith(b"\n")



def test_failed_tail_separator_write_keeps_outbox_pending(tmp_path, monkeypatch):
    from worldshepherd_sara import storage as storage_module

    store = DurableStore(tmp_path / "data")
    event_id = queue_fixed_event(store, "SARA-EVENT-SEPARATOR-001")
    store.audit_path.write_bytes(b'{"event":"interrupted"')
    original_write = storage_module.os.write

    def fail_separator(descriptor, data):
        if data == b"\\n":
            return 0
        return original_write(descriptor, data)

    with monkeypatch.context() as patch:
        patch.setattr(storage_module.os, "write", fail_separator)
        with pytest.raises(OSError, match="separator write made no progress"):
            drain_event_outbox(store, limit=1)

    assert pending_event_ids(store.get_registry()) == [event_id]
    assert not any(
        record.get("event") == "test_provenance"
        for record in store.read_audit(50)
    )
