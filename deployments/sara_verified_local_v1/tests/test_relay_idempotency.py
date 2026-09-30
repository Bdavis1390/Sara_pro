from __future__ import annotations

import pytest

from worldshepherd_sara.event_outbox import drain_event_outbox, outbox_status
from worldshepherd_sara.relay_idempotency import (
    MAX_RELAY_IDEMPOTENCY_RECEIPTS,
    RELAY_IDEMPOTENCY_REGISTRY_KEY,
    RelayIdempotencyConflict,
    queue_relay_once_patch,
)
from worldshepherd_sara.storage import DurableStore


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def relay_body(correlation_id: str, value: str = "one") -> dict[str, object]:
    return {
        "target": "SSPADAWANZZ",
        "action": "status_check",
        "payload": {"value": value},
        "correlation_id": correlation_id,
    }


def relay_records(store: DurableStore, correlation_id: str) -> list[dict[str, object]]:
    return [
        record
        for record in store.read_audit(500)
        if record.get("event") == "relay_recorded"
        and record.get("payload", {}).get("correlation_id") == correlation_id
    ]


def test_identical_relay_retry_is_suppressed(client, tokens):
    relay, _admin = tokens
    correlation_id = "RELAY-IDEMPOTENT-001"
    body = relay_body(correlation_id)

    first = client.post("/v1/relay", headers=auth(relay), json=body)
    assert first.status_code == 200
    assert first.json()["status"] == "recorded_local_only"
    assert len(relay_records(client.app.state.store, correlation_id)) == 1

    second = client.post("/v1/relay", headers=auth(relay), json=body)
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate_replay_suppressed"
    assert second.json()["correlation_id"] == correlation_id
    assert len(relay_records(client.app.state.store, correlation_id)) == 1

    state = client.app.state.store.get_registry()[RELAY_IDEMPOTENCY_REGISTRY_KEY]
    assert state["order"] == [correlation_id]
    assert state["receipts"][correlation_id]["actor"] == "relay"


def test_same_correlation_id_with_different_request_fails_closed(client, tokens):
    relay, _admin = tokens
    correlation_id = "RELAY-IDEMPOTENT-CONFLICT"

    first = client.post(
        "/v1/relay",
        headers=auth(relay),
        json=relay_body(correlation_id, "one"),
    )
    assert first.status_code == 200
    registry_before = client.app.state.store.registry_path.read_bytes()
    audit_before = client.app.state.store.audit_path.read_bytes()

    conflict = client.post(
        "/v1/relay",
        headers=auth(relay),
        json=relay_body(correlation_id, "different"),
    )
    assert conflict.status_code == 409
    assert "different relay request" in conflict.json()["detail"]
    assert client.app.state.store.registry_path.read_bytes() == registry_before
    assert client.app.state.store.audit_path.read_bytes() == audit_before


def test_same_correlation_id_cannot_cross_actor_boundary(client, tokens):
    relay, admin = tokens
    correlation_id = "RELAY-IDEMPOTENT-ACTOR"
    body = relay_body(correlation_id)

    assert client.post("/v1/relay", headers=auth(relay), json=body).status_code == 200
    conflict = client.post("/v1/relay", headers=auth(admin), json=body)
    assert conflict.status_code == 409
    assert len(relay_records(client.app.state.store, correlation_id)) == 1


def test_receipt_and_pending_event_survive_delivery_failure(client, tokens, monkeypatch):
    relay, _admin = tokens
    durable_store = client.app.state.store
    correlation_id = "RELAY-IDEMPOTENT-RECOVERY"
    original_append = durable_store.append_audit

    def fail_append(_record):
        raise OSError("simulated audit delivery failure")

    monkeypatch.setattr(durable_store, "append_audit", fail_append)
    first = client.post(
        "/v1/relay",
        headers=auth(relay),
        json=relay_body(correlation_id),
    )
    assert first.status_code == 200
    assert first.json()["status"] == "recorded_local_pending_replay"
    registry = durable_store.get_registry()
    assert correlation_id in registry[RELAY_IDEMPOTENCY_REGISTRY_KEY]["receipts"]
    assert outbox_status(registry)["pending"] == 1

    duplicate = client.post(
        "/v1/relay",
        headers=auth(relay),
        json=relay_body(correlation_id),
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "duplicate_replay_pending"
    assert outbox_status(durable_store.get_registry())["pending"] == 1

    monkeypatch.setattr(durable_store, "append_audit", original_append)
    recovered = client.post(
        "/v1/relay",
        headers=auth(relay),
        json=relay_body(correlation_id),
    )
    assert recovered.status_code == 200
    assert recovered.json()["status"] == "duplicate_replay_suppressed"
    assert outbox_status(durable_store.get_registry())["pending"] == 0
    assert len(relay_records(durable_store, correlation_id)) == 1


def test_relay_idempotency_namespace_is_protected(client, tokens):
    _relay, admin = tokens
    response = client.patch(
        "/admin/registry",
        headers=auth(admin),
        json={"values": {RELAY_IDEMPOTENCY_REGISTRY_KEY: {}}},
    )
    assert response.status_code == 403


def test_receipt_state_survives_store_reopen(tmp_path):
    store = DurableStore(tmp_path / "data")
    correlation_id = "RELAY-IDEMPOTENT-PERSISTED"

    def queue(registry):
        return queue_relay_once_patch(
            registry,
            correlation_id=correlation_id,
            actor="relay",
            target="SSPADAWANZZ",
            action="status_check",
            payload={"scope": "local"},
        )

    admission = store.transact_registry(queue)
    assert admission.is_new is True
    assert drain_event_outbox(store, limit=1) == 1

    reopened = DurableStore(store.root)
    replay = reopened.transact_registry(queue)
    assert replay.is_new is False
    assert replay.event_id == admission.event_id
    assert outbox_status(reopened.get_registry())["pending"] == 0


def test_receipt_window_is_bounded_and_fifo(tmp_path):
    store = DurableStore(tmp_path / "data")
    ids = [
        f"RELAY-IDEMPOTENT-{index:03d}"
        for index in range(MAX_RELAY_IDEMPOTENCY_RECEIPTS + 1)
    ]

    for correlation_id in ids:
        admission = store.transact_registry(
            lambda registry, cid=correlation_id: queue_relay_once_patch(
                registry,
                correlation_id=cid,
                actor="relay",
                target="SSPADAWANZZ",
                action="status_check",
                payload={"id": cid},
            )
        )
        assert admission.is_new is True
        drain_event_outbox(store, limit=1)

    state = store.get_registry()[RELAY_IDEMPOTENCY_REGISTRY_KEY]
    assert len(state["order"]) == MAX_RELAY_IDEMPOTENCY_RECEIPTS
    assert ids[0] not in state["receipts"]
    assert state["order"][0] == ids[1]
    assert state["order"][-1] == ids[-1]


def test_helper_conflict_aborts_transaction_without_mutation(tmp_path):
    store = DurableStore(tmp_path / "data")
    correlation_id = "RELAY-IDEMPOTENT-ABORT"

    def first(registry):
        return queue_relay_once_patch(
            registry,
            correlation_id=correlation_id,
            actor="relay",
            target="SSPADAWANZZ",
            action="status_check",
            payload={"value": 1},
        )

    store.transact_registry(first)
    registry_before = store.registry_path.read_bytes()

    def conflict(registry):
        return queue_relay_once_patch(
            registry,
            correlation_id=correlation_id,
            actor="relay",
            target="SSPADAWANZZ",
            action="status_check",
            payload={"value": 2},
        )

    with pytest.raises(RelayIdempotencyConflict):
        store.transact_registry(conflict)
    assert store.registry_path.read_bytes() == registry_before
