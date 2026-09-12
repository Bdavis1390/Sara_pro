from __future__ import annotations

from datetime import datetime, timedelta, timezone

from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_checkpoint_verify import verify_bundle
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.overwatch_provenance import deliver_overwatch_intent_provenance
from worldshepherd_sara.overwatch_tripwire import (
    OverwatchObservation,
    OverwatchSignal,
    classify_overwatch_observation,
    record_overwatch_containment_intent,
)
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 12, 0, 55, tzinfo=timezone.utc)


def test_overwatch_provenance_is_in_signed_echo_checkpoint(
    tmp_path,
    echo_checkpoint_key,
):
    key, _path = echo_checkpoint_key
    sara_store = DurableStore(tmp_path / "sara")
    echo_store = EchoEventStore((tmp_path / "echo").resolve())

    observation = OverwatchObservation(
        observation_id="OBS-CHECKPOINT-1",
        action_id="ACTION-CHECKPOINT-1",
        monitor_id="OVERWATCH-INDEPENDENT-1",
        model_id="MODEL-1",
        model_version="v1",
        observed_at=NOW,
        signals=(OverwatchSignal.MONITOR_INTERFERENCE,),
    )
    decision = classify_overwatch_observation(observation)
    intent = record_overwatch_containment_intent(
        sara_store,
        decision=decision,
        now=NOW + timedelta(seconds=1),
    )
    receipt = deliver_overwatch_intent_provenance(
        sara_store,
        echo_store,
        intent=intent,
    )

    checkpoints = EchoCheckpointManager(
        echo_store,
        private_key=key,
        key_id="ECHO-CHECKPOINT-OVERWATCH-TEST-V1",
    )
    bundle = checkpoints.create_checkpoint()
    verified = verify_bundle(bundle, checkpoints.fingerprint_sha256)

    assert verified["event_count"] >= 1
    membership = {
        entry["event_id"]: entry["semantic_sha256"]
        for entry in bundle["manifest"]["events"]
    }
    assert receipt.provenance_event_id in membership
    assert membership[receipt.provenance_event_id] == receipt.echo_semantic_sha256

    stored = echo_store.get(receipt.provenance_event_id)
    assert stored is not None
    assert stored.semantic_sha256 == receipt.echo_semantic_sha256
    payload = stored.payload()
    assert payload["monitor_identity_authenticated"] is False
    assert payload["authorization_effect"] == "NONE"
    assert payload["execution_effect_applied"] is False
