from __future__ import annotations

from copy import deepcopy

import pytest

from worldshepherd_sara.discord_connector import DiscordConnectorError
from worldshepherd_sara.discord_event_projection import (
    DISCORD_RECEIPTS_REGISTRY_KEY,
    DiscordEventProjectionError,
    project_delivered_events,
)
from worldshepherd_sara.discord_webhook import DiscordDeliveryResult
from worldshepherd_sara.event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    drain_event_outbox,
    queue_event_outbox_patch,
)
from worldshepherd_sara.storage import DurableStore


class FakeConnector:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.notifications = []

    def notify(self, notification, *, dry_run=False, timeout_seconds=5.0, max_attempts=3):
        del timeout_seconds, max_attempts
        self.notifications.append(notification)
        if self.fail:
            raise DiscordConnectorError("simulated connector failure")
        return DiscordDeliveryResult(
            delivered=not dry_run,
            dry_run=dry_run,
            attempts=0 if dry_run else 1,
            http_status=None if dry_run else 204,
            content_sha256="a" * 64,
            delivered_at=None if dry_run else "2026-09-16T15:00:00+00:00",
        )


def custody_payload(*, prime_id="PRIME-TEST-001", transition_id="PRIME-CUSTODY-TEST-001"):
    return {
        "schema": "WS-ECHO-PRIME-CUSTODY-V1",
        "provenance_channel": "SARA_AUDIT_FOR_ECHO_INGEST",
        "transition_id": transition_id,
        "prime_id": prime_id,
        "action": "MISSION_COMPLETED",
        "previous_state": "READY",
        "new_state": "QUARANTINED_FOR_REQUALIFICATION",
        "evidence_refs": ["PRIVATE-EVIDENCE-REF"],
        "details": {"sensitive": "do-not-project"},
        "claims_boundary": "Software custody/provenance evidence only.",
    }


def queue_event(store, *, event, payload, event_id):
    def operation(registry):
        patch, stable_id = queue_event_outbox_patch(
            registry,
            event=event,
            actor="admin_operator",
            payload=payload,
            event_id=event_id,
        )
        return patch, stable_id

    return store.transact_registry(operation)


def test_pending_event_is_never_projected(tmp_path):
    store = DurableStore(tmp_path / "data")
    queue_event(
        store,
        event="prime_custody_provenance",
        payload=custody_payload(),
        event_id="SARA-EVENT-DISCORD-PENDING-001",
    )
    connector = FakeConnector()

    result = project_delivered_events(store, connector=connector, dry_run=True)

    assert result.scanned_delivered == 0
    assert result.projected == 0
    assert connector.notifications == []
    assert DISCORD_RECEIPTS_REGISTRY_KEY not in store.get_registry()


def test_delivered_unknown_event_is_not_projected(tmp_path):
    store = DurableStore(tmp_path / "data")
    queue_event(
        store,
        event="unmapped_internal_event",
        payload={"value": "private"},
        event_id="SARA-EVENT-DISCORD-UNKNOWN-001",
    )
    assert drain_event_outbox(store, limit=1) == 1
    connector = FakeConnector()

    result = project_delivered_events(store, connector=connector, dry_run=True)

    assert result.scanned_delivered == 1
    assert result.unmapped == 1
    assert result.projected == 0
    assert connector.notifications == []


def test_delivered_custody_event_projects_once_and_writes_receipt(tmp_path):
    store = DurableStore(tmp_path / "data")
    event_id = "SARA-EVENT-DISCORD-CUSTODY-001"
    queue_event(
        store,
        event="prime_custody_provenance",
        payload=custody_payload(),
        event_id=event_id,
    )
    assert drain_event_outbox(store, limit=1) == 1
    outbox_before = deepcopy(store.get_registry()[EVENT_OUTBOX_REGISTRY_KEY])
    connector = FakeConnector()

    first = project_delivered_events(store, connector=connector)

    assert first.projected == 1
    assert first.receipts_written == 1
    assert len(connector.notifications) == 1
    notice = connector.notifications[0]
    assert notice.event_class == "EVIDENCE_STATUS"
    assert notice.source_event_id == event_id
    assert notice.evidence_ref == "PRIME-CUSTODY-TEST-001"
    assert "PRIVATE-EVIDENCE-REF" not in notice.summary
    assert "do-not-project" not in notice.summary
    assert store.get_registry()[EVENT_OUTBOX_REGISTRY_KEY] == outbox_before

    second = project_delivered_events(store, connector=connector)
    assert second.projected == 0
    assert second.already_receipted == 1
    assert len(connector.notifications) == 1


def test_rejection_projection_does_not_forward_reason_or_authorization_context(tmp_path):
    store = DurableStore(tmp_path / "data")
    event_id = "SARA-EVENT-DISCORD-REJECT-001"
    queue_event(
        store,
        event="prime_sentinel_authorization_rejected",
        payload={
            "prime_id": "PRIME-REJECT-001",
            "authorization_id": "AUTH-PRIVATE-123",
            "reason": "password=super-secret-value",
            "claims_boundary": "Software authorization decision only.",
        },
        event_id=event_id,
    )
    assert drain_event_outbox(store, limit=1) == 1
    connector = FakeConnector()

    result = project_delivered_events(store, connector=connector)

    assert result.projected == 1
    notice = connector.notifications[0]
    rendered_fields = " ".join(
        value or ""
        for value in (notice.title, notice.summary, notice.status, notice.evidence_ref)
    )
    assert "super-secret-value" not in rendered_fields
    assert "AUTH-PRIVATE-123" not in rendered_fields
    assert notice.event_class == "SYSTEM_ALERT"
    assert notice.priority == "P1"
    assert notice.source_event_id == event_id


def test_live_connector_failure_leaves_no_receipt(tmp_path):
    store = DurableStore(tmp_path / "data")
    event_id = "SARA-EVENT-DISCORD-FAIL-001"
    queue_event(
        store,
        event="prime_custody_provenance",
        payload=custody_payload(transition_id="PRIME-CUSTODY-FAIL-001"),
        event_id=event_id,
    )
    assert drain_event_outbox(store, limit=1) == 1

    with pytest.raises(DiscordEventProjectionError, match="simulated connector failure"):
        project_delivered_events(store, connector=FakeConnector(fail=True))

    assert DISCORD_RECEIPTS_REGISTRY_KEY not in store.get_registry()
    assert store.get_registry()[EVENT_OUTBOX_REGISTRY_KEY][event_id]["status"] == "DELIVERED"


def test_dry_run_requires_no_webhook_and_writes_no_receipt(tmp_path):
    store = DurableStore(tmp_path / "data")
    event_id = "SARA-EVENT-DISCORD-DRY-001"
    queue_event(
        store,
        event="prime_custody_provenance",
        payload=custody_payload(transition_id="PRIME-CUSTODY-DRY-001"),
        event_id=event_id,
    )
    assert drain_event_outbox(store, limit=1) == 1
    connector = FakeConnector()

    result = project_delivered_events(store, connector=connector, dry_run=True)

    assert result.projected == 1
    assert result.receipts_written == 0
    assert result.results[0].dry_run is True
    assert result.results[0].delivered is False
    assert DISCORD_RECEIPTS_REGISTRY_KEY not in store.get_registry()


def test_receipt_write_failure_allows_stable_id_replay(tmp_path, monkeypatch):
    store = DurableStore(tmp_path / "data")
    event_id = "SARA-EVENT-DISCORD-REPLAY-001"
    queue_event(
        store,
        event="prime_custody_provenance",
        payload=custody_payload(transition_id="PRIME-CUSTODY-REPLAY-001"),
        event_id=event_id,
    )
    assert drain_event_outbox(store, limit=1) == 1
    connector = FakeConnector()
    original_atomic_write = store._atomic_write_json

    def fail_receipt_write(_path, _value):
        raise RuntimeError("simulated receipt persistence failure")

    monkeypatch.setattr(store, "_atomic_write_json", fail_receipt_write)
    with pytest.raises(
        DiscordEventProjectionError,
        match="delivery succeeded but receipt persistence failed",
    ):
        project_delivered_events(store, connector=connector)
    assert len(connector.notifications) == 1
    assert connector.notifications[0].source_event_id == event_id

    monkeypatch.setattr(store, "_atomic_write_json", original_atomic_write)
    recovered = DurableStore(store.root)
    replay_connector = FakeConnector()
    replay = project_delivered_events(recovered, connector=replay_connector)

    assert replay.projected == 1
    assert replay.receipts_written == 1
    assert replay_connector.notifications[0].source_event_id == event_id


def test_malformed_receipt_registry_fails_closed(tmp_path):
    store = DurableStore(tmp_path / "data")
    store.patch_registry(
        {
            DISCORD_RECEIPTS_REGISTRY_KEY: {
                "schema": "WRONG",
                "receipts": {},
            }
        }
    )

    with pytest.raises(DiscordEventProjectionError, match="receipt registry is malformed"):
        project_delivered_events(store, connector=FakeConnector(), dry_run=True)


def test_forged_delivered_event_without_audit_confirmation_fails_closed(tmp_path):
    store = DurableStore(tmp_path / "data")
    event_id = "SARA-EVENT-DISCORD-FORGED-001"
    queue_event(
        store,
        event="prime_custody_provenance",
        payload=custody_payload(transition_id="PRIME-CUSTODY-FORGED-001"),
        event_id=event_id,
    )
    registry = store.get_registry()
    outbox = deepcopy(registry[EVENT_OUTBOX_REGISTRY_KEY])
    outbox[event_id]["status"] = "DELIVERED"
    outbox[event_id]["delivered_at"] = "2026-09-16T15:00:00+00:00"
    store.patch_registry({EVENT_OUTBOX_REGISTRY_KEY: outbox})

    with pytest.raises(DiscordEventProjectionError, match="lacks matching recent SARA audit"):
        project_delivered_events(store, connector=FakeConnector(), dry_run=True)
