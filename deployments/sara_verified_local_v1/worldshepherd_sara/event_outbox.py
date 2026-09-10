from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .models import AuditRecord
from .storage import DurableStore


EVENT_OUTBOX_REGISTRY_KEY = "SARA_EVENT_OUTBOX"
EVENT_OUTBOX_SCHEMA = "WS-SARA-EVENT-OUTBOX-V1"
MAX_PENDING_OUTBOX_EVENTS = 2048
MAX_RETAINED_DELIVERED_EVENTS = 512
_RESERVED_PAYLOAD_KEYS = frozenset({"_outbox_event_id", "_delivery_semantics"})


class EventOutboxError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    pending_count = sum(
        1
        for entry in records.values()
        if isinstance(entry, dict) and entry.get("status") == "PENDING"
    )
    if pending_count >= MAX_PENDING_OUTBOX_EVENTS:
        raise EventOutboxError("pending event outbox capacity exceeded")

    stable_id = event_id or f"SARA-EVENT-{uuid4()}"
    if stable_id in records:
        raise EventOutboxError("outbox event_id already exists")

    delivered = [
        (key, value)
        for key, value in records.items()
        if isinstance(value, dict) and value.get("status") == "DELIVERED"
    ]
    if len(delivered) >= MAX_RETAINED_DELIVERED_EVENTS:
        delivered.sort(key=lambda item: str(item[1].get("delivered_at", "")))
        for key, _value in delivered[: len(delivered) - MAX_RETAINED_DELIVERED_EVENTS + 1]:
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


def pending_event_ids(registry: dict[str, Any]) -> list[str]:
    records = _outbox_map(registry)
    pending: list[tuple[str, str]] = []
    for event_id, entry in records.items():
        if isinstance(entry, dict) and entry.get("status") == "PENDING":
            pending.append((str(entry.get("created_at", "")), event_id))
    pending.sort()
    return [event_id for _created_at, event_id in pending]


def outbox_status(registry: dict[str, Any]) -> dict[str, int]:
    records = _outbox_map(registry)
    pending = 0
    delivered = 0
    malformed = 0
    for entry in records.values():
        if not isinstance(entry, dict):
            malformed += 1
        elif entry.get("status") == "PENDING":
            pending += 1
        elif entry.get("status") == "DELIVERED":
            delivered += 1
        else:
            malformed += 1
    return {"pending": pending, "delivered_retained": delivered, "malformed": malformed}


def _delivery_patch(
    registry: dict[str, Any],
    *,
    event_id: str,
) -> tuple[dict[str, Any], AuditRecord]:
    records = _outbox_map(registry)
    entry = records.get(event_id)
    if not isinstance(entry, dict):
        raise EventOutboxError("outbox event is missing or malformed")
    if entry.get("status") != "PENDING":
        raise EventOutboxError("outbox event is not pending")
    if entry.get("schema") != EVENT_OUTBOX_SCHEMA:
        raise EventOutboxError("outbox event schema is invalid")

    event = entry.get("event")
    actor = entry.get("actor")
    payload = entry.get("payload")
    if not isinstance(event, str) or not event:
        raise EventOutboxError("outbox event name is invalid")
    if not isinstance(actor, str) or not actor:
        raise EventOutboxError("outbox actor is invalid")
    if not isinstance(payload, dict):
        raise EventOutboxError("outbox payload is invalid")
    _validate_payload(payload)

    audit_payload = dict(payload)
    audit_payload["_outbox_event_id"] = event_id
    audit_payload["_delivery_semantics"] = "AT_LEAST_ONCE"
    record = AuditRecord.create(event=event, actor=actor, payload=audit_payload)

    updated = dict(entry)
    updated.update({"status": "DELIVERED", "delivered_at": _utc_now()})
    records[event_id] = updated
    return {EVENT_OUTBOX_REGISTRY_KEY: records}, record


def drain_event_outbox(store: DurableStore, *, limit: int = 100) -> int:
    """Deliver pending events to the SARA audit log with at-least-once semantics.

    Each delivery is serialized through DurableStore.transact_registry(). The
    audit append occurs before the PENDING->DELIVERED registry write. A process
    or filesystem failure in that narrow window can therefore cause replay of
    the same stable event_id. Consumers must deduplicate on _outbox_event_id.
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")

    delivered = 0
    for _ in range(limit):
        def operation(registry: dict[str, Any]):
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
