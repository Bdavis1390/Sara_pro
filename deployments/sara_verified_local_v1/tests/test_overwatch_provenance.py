from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    SINK_ECHO,
    SINK_SARA_AUDIT,
)
from worldshepherd_sara.overwatch_provenance import (
    OverwatchProvenanceError,
    deliver_overwatch_intent_provenance,
    queue_overwatch_intent_provenance,
)
from worldshepherd_sara.overwatch_tripwire import (
    OverwatchObservation,
    OverwatchSignal,
    classify_overwatch_observation,
    record_overwatch_containment_intent,
)
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 12, 0, 45, tzinfo=timezone.utc)


def _intent(store: DurableStore, observation_id: str = "OBS-PROV-1"):
    observation = OverwatchObservation(
        observation_id=observation_id,
        action_id=f"ACTION-{observation_id}",
        monitor_id="OVERWATCH-INDEPENDENT-1",
        model_id="MODEL-1",
        model_version="v1",
        observed_at=NOW,
        signals=(OverwatchSignal.UNAUTHORIZED_PERSISTENCE,),
    )
    decision = classify_overwatch_observation(observation)
    return record_overwatch_containment_intent(
        store,
        decision=decision,
        now=NOW + timedelta(seconds=1),
    )


def test_unrecorded_intent_cannot_queue_provenance(tmp_path):
    source = DurableStore(tmp_path / "source")
    intent = _intent(source)
    empty = DurableStore(tmp_path / "empty")

    with pytest.raises(OverwatchProvenanceError, match="durably recorded"):
        queue_overwatch_intent_provenance(empty, intent=intent)

    assert EVENT_OUTBOX_REGISTRY_KEY not in empty.get_registry()


def test_queue_is_stable_idempotent_and_requires_both_sinks(tmp_path):
    store = DurableStore(tmp_path / "sara")
    intent = _intent(store)

    first = queue_overwatch_intent_provenance(store, intent=intent)
    second = queue_overwatch_intent_provenance(store, intent=intent)

    assert first == second
    registry = store.get_registry()
    entry = registry[EVENT_OUTBOX_REGISTRY_KEY][first]
    assert entry["status"] == "PENDING"
    assert set(entry["required_sinks"]) == {SINK_SARA_AUDIT, SINK_ECHO}
    assert entry["delivered_sinks"] == []
    payload = entry["payload"]
    assert payload["observation_id"] == intent.observation_id
    assert payload["decision_digest_sha256"] == intent.decision_digest_sha256
    assert payload["monitor_identity_authenticated"] is False
    assert payload["authorization_effect"] == "NONE"
    assert payload["execution_effect_applied"] is False


def test_conflicting_stable_outbox_event_fails_closed(tmp_path):
    store = DurableStore(tmp_path / "sara")
    intent = _intent(store)
    event_id = queue_overwatch_intent_provenance(store, intent=intent)

    registry = store.get_registry()
    outbox = dict(registry[EVENT_OUTBOX_REGISTRY_KEY])
    forged = dict(outbox[event_id])
    forged_payload = dict(forged["payload"])
    forged_payload["decision_digest_sha256"] = "f" * 64
    forged["payload"] = forged_payload
    outbox[event_id] = forged
    store.patch_registry({EVENT_OUTBOX_REGISTRY_KEY: outbox})
    before = store.get_registry()

    with pytest.raises(OverwatchProvenanceError, match="conflicts"):
        queue_overwatch_intent_provenance(store, intent=intent)

    assert store.get_registry() == before


def test_delivery_reaches_sara_audit_and_echo_without_authority(tmp_path):
    store = DurableStore(tmp_path / "sara")
    echo = EchoEventStore((tmp_path / "echo").resolve())
    intent = _intent(store)

    receipt = deliver_overwatch_intent_provenance(store, echo, intent=intent)

    assert receipt.observation_id == intent.observation_id
    assert receipt.decision_digest_sha256 == intent.decision_digest_sha256
    assert receipt.authorization_effect == "NONE"
    assert receipt.execution_effect_applied is False
    assert receipt.echo_delivery_count == 1

    registry = store.get_registry()
    entry = registry[EVENT_OUTBOX_REGISTRY_KEY][receipt.provenance_event_id]
    assert entry["status"] == "DELIVERED"
    assert set(entry["delivered_sinks"]) == {SINK_SARA_AUDIT, SINK_ECHO}

    stored = echo.get(receipt.provenance_event_id)
    assert stored is not None
    payload = stored.payload()
    assert payload["monitor_identity_authenticated"] is False
    assert payload["authorization_effect"] == "NONE"
    assert payload["execution_effect_applied"] is False
    assert payload["decision_digest_sha256"] == intent.decision_digest_sha256

    audit = store.read_audit(50)
    matching = [
        record
        for record in audit
        if record.get("event") == "overwatch_containment_intent"
        and record.get("payload", {}).get("_outbox_event_id")
        == receipt.provenance_event_id
    ]
    assert len(matching) == 1


def test_delivery_replay_is_idempotent_and_does_not_reingest_echo(tmp_path):
    store = DurableStore(tmp_path / "sara")
    echo = EchoEventStore((tmp_path / "echo").resolve())
    intent = _intent(store, "OBS-PROV-REPLAY")

    first = deliver_overwatch_intent_provenance(store, echo, intent=intent)
    second = deliver_overwatch_intent_provenance(store, echo, intent=intent)

    assert first.provenance_event_id == second.provenance_event_id
    assert first.echo_semantic_sha256 == second.echo_semantic_sha256
    assert first.echo_delivery_count == 1
    assert second.echo_delivery_count == 1
    stored = echo.get(first.provenance_event_id)
    assert stored is not None
    assert stored.delivery_count == 1
