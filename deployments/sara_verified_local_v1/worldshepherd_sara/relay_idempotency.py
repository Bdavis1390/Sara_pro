from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .event_outbox import EVENT_OUTBOX_REGISTRY_KEY, queue_event_outbox_patch


RELAY_IDEMPOTENCY_REGISTRY_KEY = "SARA_RELAY_IDEMPOTENCY"
RELAY_IDEMPOTENCY_SCHEMA = "WS-SARA-RELAY-IDEMPOTENCY-V1"
MAX_RELAY_IDEMPOTENCY_RECEIPTS = 32


class RelayIdempotencyError(ValueError):
    pass


class RelayIdempotencyConflict(RelayIdempotencyError):
    pass


@dataclass(frozen=True)
class RelayAdmission:
    correlation_id: str
    request_digest: str
    event_id: str
    is_new: bool


def relay_request_digest(
    *,
    actor: str,
    target: str,
    action: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "actor": actor,
            "target": target,
            "action": action,
            "payload": payload,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def stable_relay_event_id(correlation_id: str, request_digest: str) -> str:
    material = f"{correlation_id}\0{request_digest}".encode("utf-8")
    suffix = hashlib.sha256(material).hexdigest()[:32]
    return f"SARA-RELAY-{suffix}"


def _empty_state() -> dict[str, Any]:
    return {
        "schema": RELAY_IDEMPOTENCY_SCHEMA,
        "order": [],
        "receipts": {},
    }


def _validated_state(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(RELAY_IDEMPOTENCY_REGISTRY_KEY)
    if raw is None:
        return _empty_state()
    if not isinstance(raw, dict):
        raise RelayIdempotencyError(
            f"{RELAY_IDEMPOTENCY_REGISTRY_KEY} must be a JSON object"
        )
    if raw.get("schema") != RELAY_IDEMPOTENCY_SCHEMA:
        raise RelayIdempotencyError("relay idempotency state has invalid schema")

    order = raw.get("order")
    receipts = raw.get("receipts")
    if not isinstance(order, list) or not isinstance(receipts, dict):
        raise RelayIdempotencyError("relay idempotency state is malformed")
    if len(order) != len(set(order)):
        raise RelayIdempotencyError("relay idempotency order contains duplicates")
    if len(order) > MAX_RELAY_IDEMPOTENCY_RECEIPTS:
        raise RelayIdempotencyError("relay idempotency receipt capacity exceeded")
    if set(order) != set(receipts):
        raise RelayIdempotencyError("relay idempotency receipt index is inconsistent")

    for correlation_id in order:
        receipt = receipts.get(correlation_id)
        if not isinstance(correlation_id, str) or not correlation_id:
            raise RelayIdempotencyError("relay idempotency key is invalid")
        if not isinstance(receipt, dict):
            raise RelayIdempotencyError("relay idempotency receipt is malformed")
        if receipt.get("correlation_id") != correlation_id:
            raise RelayIdempotencyError("relay idempotency correlation mismatch")
        request_digest = receipt.get("request_digest")
        if (
            not isinstance(request_digest, str)
            or len(request_digest) != 64
            or any(ch not in "0123456789abcdef" for ch in request_digest)
        ):
            raise RelayIdempotencyError("relay idempotency digest is invalid")
        if not isinstance(receipt.get("event_id"), str) or not receipt["event_id"]:
            raise RelayIdempotencyError("relay idempotency event id is invalid")
        if not isinstance(receipt.get("actor"), str) or not receipt["actor"]:
            raise RelayIdempotencyError("relay idempotency actor is invalid")

    return {
        "schema": RELAY_IDEMPOTENCY_SCHEMA,
        "order": list(order),
        "receipts": {key: dict(value) for key, value in receipts.items()},
    }


def queue_relay_once_patch(
    registry: dict[str, Any],
    *,
    correlation_id: str,
    actor: str,
    target: str,
    action: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any] | None, RelayAdmission]:
    if not correlation_id or len(correlation_id) > 128:
        raise RelayIdempotencyError(
            "relay correlation_id must be between 1 and 128 characters"
        )
    if not actor or not target or not action:
        raise RelayIdempotencyError("actor, target, and action must be non-empty")

    digest = relay_request_digest(
        actor=actor,
        target=target,
        action=action,
        payload=payload,
    )
    state = _validated_state(registry)
    receipts = state["receipts"]
    order = state["order"]
    existing = receipts.get(correlation_id)

    if existing is not None:
        if existing["request_digest"] != digest or existing["actor"] != actor:
            raise RelayIdempotencyConflict(
                "correlation_id was already used for a different relay request"
            )
        return None, RelayAdmission(
            correlation_id=correlation_id,
            request_digest=digest,
            event_id=str(existing["event_id"]),
            is_new=False,
        )

    event_id = stable_relay_event_id(correlation_id, digest)
    outbox_patch, stable_id = queue_event_outbox_patch(
        registry,
        event="relay_recorded",
        actor=actor,
        payload={
            "target": target,
            "action": action,
            "correlation_id": correlation_id,
            "payload_keys": sorted(payload.keys()),
            "request_digest": digest,
            "idempotency": "SARA_OWNED_BOUNDED_RECEIPT",
        },
        event_id=event_id,
    )

    if len(order) >= MAX_RELAY_IDEMPOTENCY_RECEIPTS:
        evicted = order.pop(0)
        receipts.pop(evicted, None)

    order.append(correlation_id)
    receipts[correlation_id] = {
        "correlation_id": correlation_id,
        "request_digest": digest,
        "event_id": stable_id,
        "actor": actor,
        "target": target,
        "action": action,
    }

    state_patch = {
        RELAY_IDEMPOTENCY_REGISTRY_KEY: {
            "schema": RELAY_IDEMPOTENCY_SCHEMA,
            "order": order,
            "receipts": receipts,
        },
        EVENT_OUTBOX_REGISTRY_KEY: outbox_patch[EVENT_OUTBOX_REGISTRY_KEY],
    }
    return state_patch, RelayAdmission(
        correlation_id=correlation_id,
        request_digest=digest,
        event_id=stable_id,
        is_new=True,
    )
