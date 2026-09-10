from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .models import AuditRecord
from .storage import DurableStore


EVENT_OUTBOX_REGISTRY_KEY = "SARA_EVENT_OUTBOX"
EVENT_OUTBOX_SCHEMA = "WS-SARA-EVENT-OUTBOX-V1"
# SARA limits any mapping to 64 keys and the complete validated resource to
# 48 KiB. Keep explicit headroom for future schema growth and other registry
# state; serialized-size validation may reject an outbox before these counts.
MAX_PENDING_OUTBOX_EVENTS = 32
MAX_RETAINED_DELIVERED_EVENTS = 16
_RESERVED_PAYLOAD_KEYS = frozenset({"_outbox_event_id", "_delivery_semantics"})
_VALID_STATUSES = frozenset({"PENDING", "DELIVERED"})


class EventOutboxError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _outbox_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(EVENT_OUTBOX_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise EventOutboxError(f"{EVENT_OUTBOX_REGISTRY_KEY} must be a JSON object")
    return dict(raw)


def _validate_payload(payload: dict[str, Any]) -> None:
    reserved = sorted(_RESERVED_PAYLOAD_KEYS.intersection(payload))
    if reserved:
        raise EventOutboxError(
            f"event payload uses reserved outbox keys: {', '.join(reserved)}"
        )


def _entry_is_valid(event_id: str, entry: Any) -> bool:
    if not isinstance(event_id, str) or not event_id or not isinstance(entry, dict):
        return False
    if entry.get("schema") != EVENT_OUTBOX_SCHEMA:
        return False
    if entry.get("event_id") != event_id:
        return False
    status = entry.get("status")
    if status not in _VALID_STATUSES:
        return False
    event = entry.get("event")
    actor = entry.get("actor")
    payload = entry.get("payload")
    if not isinstance(event, str) or not event:
        return False
    if not isinstance(actor, str) or not actor:
        return False
    if not isinstance(payload, dict):
        return False
    try:
        _validate_payload(payload)
    except EventOutboxError:
        return False
    if not _valid_timestamp(entry.get("created_at")):
        return False
    if entry.get("delivery_semantics") != "AT_LEAST_ONCE":
        return False
    if status == "DELIVERED" and not _valid_timestamp(entry.get("delivered_at")):
        return False
    return True


def _validate_outbox_map(records: dict[str, Any]) -> None:
    malformed = [
        event_id for event_id, entry in records.items() if not _entry_is_valid(event_id, entry)
    ]
    if malformed:
        raise EventOutboxError("event outbox contains malformed records")


def queue_event_outbox_patch(
    registry: dict[str, Any],
    *,
    event: str,
    actor: str,
    payload: dict[str, Any],
    event_id: str | None = None,
) -> tuple[dict[str, Any], str]:
    if not event or not actor:
        raise EventOutboxError("event and actor must be non-empty")
    _validate_payload(payload)

    records = _outbox_map(registry)
    _validate_outbox_map(records)
    pending_count = sum(1 for entry in records.values() if entry["status"] == "PENDING")
    if pending_count >= MAX_PENDING_OUTBOX_EVENTS:
        raise EventOutboxError("pending event outbox capacity exceeded")

    stable_id = event_id or f"SARA-EVENT-{uuid4()}"
    if not isinstance(stable_id, str) or not stable_id:
        raise EventOutboxError("event_id must be a non-empty string")
    if stable_id in records:
        raise EventOutboxError("outbox event_id already exists")

    delivered = [
        (key, value) for key, value in records.items() if value["status"] == "DELIVERED"
    ]
    if len(delivered) >= MAX_RETAINED_DELIVERED_EVENTS:
        delivered.sort(key=lambda item: str(item[1].get("delivered_at", "")))
        remove_count = len(delivered) - MAX_RETAINED_DELIVERED_EVENTS + 1
        for key, _value in delivered[:remove_count]:
            records.pop(key, None)

    records[stable_id] = {
        "schema": EVENT_OUTBOX_SCHEMA,
        "event_id": stable_id,
        "status": "PENDING",
        "event": event,
        "actor": actor,
        "payload": dict(payload),
        "created_at": _utc_now(),
        "delivery_semantics": "AT_LEAST_ONCE",
    }
    return {EVENT_OUTBOX_REGISTRY_KEY: records}, stable_id


def queue_events_outbox_patch(
    registry: dict[str, Any],
    events: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """Queue multiple events against one evolving registry snapshot."""
    working = dict(registry)
    ids: list[str] = []
    patch: dict[str, Any] = {}
    for item in events:
        event_patch, event_id = queue_event_outbox_patch(
            working,
            event=str(item["event"]),
            actor=str(item["actor"]),
            payload=dict(item["payload"]),
            event_id=item.get("event_id"),
        )
        working.update(event_patch)
        patch.update(event_patch)
        ids.append(event_id)
    return patch, ids


def pending_event_ids(registry: dict[str, Any]) -> list[str]:
    records = _outbox_map(registry)
    pending: list[tuple[str, str]] = []
    for event_id, entry in records.items():
        if _entry_is_valid(event_id, entry) and entry["status"] == "PENDING":
            pending.append((entry["created_at"], event_id))
    pending.sort()
    return [event_id for _created_at, event_id in pending]


def outbox_status(registry: dict[str, Any]) -> dict[str, int]:
    records = _outbox_map(registry)
    pending = 0
    delivered = 0
    malformed = 0
    for event_id, entry in records.items():
        if not _entry_is_valid(event_id, entry):
            malformed += 1
        elif entry["status"] == "PENDING":
            pending += 1
        else:
            delivered += 1
    return {"pending": pending, "delivered_retained": delivered, "malformed": malformed}


def _delivery_patch(
    registry: dict[str, Any],
    *,
    event_id: str,
) -> tuple[dict[str, Any], AuditRecord]:
    records = _outbox_map(registry)
    entry = records.get(event_id)
    if not _entry_is_valid(event_id, entry):
        raise EventOutboxError("outbox event is missing or malformed")
    assert isinstance(entry, dict)
    if entry["status"] != "PENDING":
        raise EventOutboxError("outbox event is not pending")

    payload = dict(entry["payload"])
    payload["_outbox_event_id"] = event_id
    payload["_delivery_semantics"] = "AT_LEAST_ONCE"
    record = AuditRecord.create(
        event=entry["event"],
        actor=entry["actor"],
        payload=payload,
    )

    updated = dict(entry)
    updated.update({"status": "DELIVERED", "delivered_at": _utc_now()})
    records[event_id] = updated
    return {EVENT_OUTBOX_REGISTRY_KEY: records}, record


def drain_event_outbox(store: DurableStore, *, limit: int = 100) -> int:
    """Deliver pending events to the SARA audit log with at-least-once semantics.

    The audit append happens before PENDING->DELIVERED is persisted. A failure
    after the append but before the registry write may therefore replay the
    same stable event ID. Consumers must deduplicate on _outbox_event_id.
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")

    delivered = 0
    for _ in range(limit):

        def operation(registry: dict[str, Any]):
            status = outbox_status(registry)
            if status["malformed"]:
                raise EventOutboxError("event outbox contains malformed records")
            ids = pending_event_ids(registry)
            if not ids:
                return None, False
            event_id = ids[0]
            patch, record = _delivery_patch(registry, event_id=event_id)
            # append_audit uses the same re-entrant store lock. If this raises,
            # transact_registry aborts without marking the event delivered.
            store.append_audit(record)
            return patch, True

        did_deliver = store.transact_registry(operation)
        if not did_deliver:
            break
        delivered += 1
    return delivered
