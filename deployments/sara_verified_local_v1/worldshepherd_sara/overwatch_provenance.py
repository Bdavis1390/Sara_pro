from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .echo_event_store import EchoEventStore, EchoEventStoreError
from .event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    EVENT_OUTBOX_SCHEMA,
    SINK_ECHO,
    SINK_SARA_AUDIT,
    EventOutboxError,
    deliver_event_outbox_to_echo,
    drain_event_outbox,
    queue_event_outbox_patch,
)
from .overwatch_tripwire import (
    OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY,
    OverwatchContainmentIntent,
)
from .storage import DurableStore


OVERWATCH_PROVENANCE_SCHEMA = "WS-OVERWATCH-PROVENANCE-V1"
OVERWATCH_PROVENANCE_RECEIPT_SCHEMA = "WS-OVERWATCH-PROVENANCE-RECEIPT-V1"


class OverwatchProvenanceError(RuntimeError):
    """Raised when OVERWATCH provenance cannot be bound or verified safely."""


class OverwatchProvenanceReceipt(BaseModel):
    """Non-authorizing evidence that one containment intent reached ECHO.

    This receipt does not authenticate monitor identity, authorize execution,
    promote FASA readiness, or prove that any containment side effect occurred.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal["WS-OVERWATCH-PROVENANCE-RECEIPT-V1"] = (
        OVERWATCH_PROVENANCE_RECEIPT_SCHEMA
    )
    observation_id: str = Field(min_length=1, max_length=160)
    provenance_event_id: str = Field(min_length=1, max_length=200)
    decision_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    echo_semantic_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    echo_delivery_count: int = Field(ge=1)
    authorization_effect: Literal["NONE"] = "NONE"
    execution_effect_applied: Literal[False] = False


def _stable_event_id(intent: OverwatchContainmentIntent) -> str:
    identity = hashlib.sha256(intent.observation_id.encode("utf-8")).hexdigest()
    return f"SARA-EVENT-OVERWATCH-{identity}"


def _payload(intent: OverwatchContainmentIntent) -> dict[str, object]:
    return {
        "schema": OVERWATCH_PROVENANCE_SCHEMA,
        "observation_id": intent.observation_id,
        "action_id": intent.action_id,
        "monitor_id": intent.monitor_id,
        "model_id": intent.model_id,
        "model_version": intent.model_version,
        "observed_at": intent.observed_at.isoformat(),
        "recorded_at": intent.recorded_at.isoformat(),
        "disposition": intent.disposition.value,
        "triggered_signals": [signal.value for signal in intent.triggered_signals],
        "reasons": list(intent.reasons),
        "decision_digest_sha256": intent.decision_digest_sha256,
        "authorization_effect": "NONE",
        "execution_effect_applied": False,
        "monitor_identity_authenticated": False,
    }


def _recorded_intent(
    registry: dict[str, Any],
    intent: OverwatchContainmentIntent,
) -> OverwatchContainmentIntent:
    namespace = registry.get(OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY)
    if not isinstance(namespace, dict):
        raise OverwatchProvenanceError(
            "OVERWATCH containment intent must be durably recorded before provenance"
        )
    raw = namespace.get(intent.observation_id)
    if not isinstance(raw, dict):
        raise OverwatchProvenanceError(
            "OVERWATCH containment intent is not durably recorded"
        )
    try:
        recorded = OverwatchContainmentIntent.model_validate(raw)
    except Exception as exc:
        raise OverwatchProvenanceError(
            "durable OVERWATCH containment intent is malformed"
        ) from exc
    if recorded != intent:
        raise OverwatchProvenanceError(
            "durable OVERWATCH containment intent binding mismatch"
        )
    return recorded


def _existing_outbox_matches(
    entry: Any,
    *,
    event_id: str,
    payload: dict[str, object],
) -> bool:
    if not isinstance(entry, dict):
        return False
    return (
        entry.get("schema") == EVENT_OUTBOX_SCHEMA
        and entry.get("event_id") == event_id
        and entry.get("event") == "overwatch_containment_intent"
        and entry.get("actor") == "OVERWATCH_INDEPENDENT_MONITOR"
        and entry.get("payload") == payload
        and set(entry.get("required_sinks", [])) == {SINK_SARA_AUDIT, SINK_ECHO}
        and isinstance(entry.get("delivered_sinks"), list)
        and set(entry.get("delivered_sinks", [])).issubset(
            {SINK_SARA_AUDIT, SINK_ECHO}
        )
        and entry.get("status") in {"PENDING", "DELIVERED"}
    )


def queue_overwatch_intent_provenance(
    store: DurableStore,
    *,
    intent: OverwatchContainmentIntent,
) -> str:
    """Queue stable SARA/ECHO evidence for an already-recorded containment intent.

    The original containment-intent transaction and this outbox transaction are
    deliberately separate. No cross-record atomicity is claimed. Failure to
    queue provenance never changes the intent into execution authority.
    """

    event_id = _stable_event_id(intent)
    payload = _payload(intent)

    def operation(registry: dict[str, Any]):
        _recorded_intent(registry, intent)
        outbox = registry.get(EVENT_OUTBOX_REGISTRY_KEY, {})
        if not isinstance(outbox, dict):
            raise OverwatchProvenanceError("SARA event outbox is malformed")
        existing = outbox.get(event_id)
        if existing is not None:
            if not _existing_outbox_matches(
                existing,
                event_id=event_id,
                payload=payload,
            ):
                raise OverwatchProvenanceError(
                    "stable OVERWATCH provenance event conflicts with existing outbox state"
                )
            return None, event_id
        try:
            patch, queued_id = queue_event_outbox_patch(
                registry,
                event="overwatch_containment_intent",
                actor="OVERWATCH_INDEPENDENT_MONITOR",
                payload=payload,
                event_id=event_id,
                required_sinks=(SINK_SARA_AUDIT, SINK_ECHO),
            )
        except EventOutboxError as exc:
            raise OverwatchProvenanceError(
                "OVERWATCH provenance obligation could not be queued"
            ) from exc
        return patch, queued_id

    return store.transact_registry(operation)


def deliver_overwatch_intent_provenance(
    store: DurableStore,
    echo_store: EchoEventStore,
    *,
    intent: OverwatchContainmentIntent,
) -> OverwatchProvenanceReceipt:
    """Deliver and verify the exact containment-intent evidence in both sinks.

    This function creates evidence only. It neither authenticates OVERWATCH nor
    applies CONSTRAIN/CONTAIN/TERMINATE side effects.
    """

    event_id = queue_overwatch_intent_provenance(store, intent=intent)
    try:
        drain_event_outbox(store, limit=32)
        deliver_event_outbox_to_echo(store, echo_store, event_id=event_id)
    except (EventOutboxError, EchoEventStoreError, OSError, RuntimeError) as exc:
        raise OverwatchProvenanceError(
            "OVERWATCH provenance delivery failed closed"
        ) from exc

    registry = store.get_registry()
    outbox = registry.get(EVENT_OUTBOX_REGISTRY_KEY)
    if not isinstance(outbox, dict):
        raise OverwatchProvenanceError("SARA event outbox is unavailable")
    entry = outbox.get(event_id)
    if not _existing_outbox_matches(
        entry,
        event_id=event_id,
        payload=_payload(intent),
    ):
        raise OverwatchProvenanceError(
            "delivered OVERWATCH provenance binding is invalid"
        )
    assert isinstance(entry, dict)
    if entry.get("status") != "DELIVERED" or set(entry.get("delivered_sinks", [])) != {
        SINK_SARA_AUDIT,
        SINK_ECHO,
    }:
        raise OverwatchProvenanceError(
            "OVERWATCH provenance has not reached both required sinks"
        )

    try:
        echoed = echo_store.get(event_id)
    except EchoEventStoreError as exc:
        raise OverwatchProvenanceError(
            "unable to verify OVERWATCH evidence in ECHO"
        ) from exc
    if echoed is None:
        raise OverwatchProvenanceError("OVERWATCH evidence is absent from ECHO")
    echoed_payload = echoed.payload()
    expected_payload = _payload(intent)
    if echoed_payload.get("observation_id") != intent.observation_id:
        raise OverwatchProvenanceError("ECHO observation binding mismatch")
    if echoed_payload.get("decision_digest_sha256") != intent.decision_digest_sha256:
        raise OverwatchProvenanceError("ECHO decision-digest binding mismatch")
    for invariant, expected in (
        ("authorization_effect", "NONE"),
        ("execution_effect_applied", False),
        ("monitor_identity_authenticated", False),
    ):
        if echoed_payload.get(invariant) != expected:
            raise OverwatchProvenanceError(
                f"ECHO OVERWATCH safety invariant mismatch: {invariant}"
            )
    if echoed_payload != {
        **expected_payload,
        "_outbox_event_id": event_id,
        "_delivery_semantics": "AT_LEAST_ONCE",
    }:
        raise OverwatchProvenanceError("stored ECHO OVERWATCH payload mismatch")

    return OverwatchProvenanceReceipt(
        observation_id=intent.observation_id,
        provenance_event_id=event_id,
        decision_digest_sha256=intent.decision_digest_sha256,
        echo_semantic_sha256=echoed.semantic_sha256,
        echo_delivery_count=echoed.delivery_count,
    )
