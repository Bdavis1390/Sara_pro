from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

import worldshepherd_sara.overwatch_tripwire as overwatch
from worldshepherd_sara.overwatch_tripwire import (
    OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY,
    OverwatchDisposition,
    OverwatchObservation,
    OverwatchSignal,
    OverwatchTripwireError,
    classify_overwatch_observation,
    record_overwatch_containment_intent,
)
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 9, 11, 22, 30, tzinfo=timezone.utc)


def _observation(
    observation_id: str = "OBS-1",
    *,
    signals: tuple[OverwatchSignal, ...] = (),
    telemetry_complete: bool = True,
    monitor_heartbeat_present: bool = True,
) -> OverwatchObservation:
    return OverwatchObservation(
        observation_id=observation_id,
        action_id=f"ACTION-{observation_id}",
        monitor_id="OVERWATCH-INDEPENDENT-1",
        model_id="MODEL-1",
        model_version="v1",
        observed_at=NOW,
        telemetry_complete=telemetry_complete,
        monitor_heartbeat_present=monitor_heartbeat_present,
        signals=signals,
    )


def test_clean_observation_is_deterministic_continue():
    observation = _observation()

    first = classify_overwatch_observation(observation)
    second = classify_overwatch_observation(observation)

    assert first == second
    assert first.disposition == OverwatchDisposition.CONTINUE
    assert first.authorization_effect == "NONE"
    assert first.triggered_signals == ()
    assert len(first.decision_digest_sha256) == 64


def test_soft_tripwire_constrains_without_claiming_execution():
    decision = classify_overwatch_observation(
        _observation(signals=(OverwatchSignal.TOOL_USE_DIVERGENCE,))
    )

    assert decision.disposition == OverwatchDisposition.CONSTRAIN
    assert decision.authorization_effect == "NONE"


def test_containment_tripwire_contains():
    decision = classify_overwatch_observation(
        _observation(signals=(OverwatchSignal.PRIVILEGE_ESCALATION,))
    )

    assert decision.disposition == OverwatchDisposition.CONTAIN
    assert "unauthorized privilege escalation" in " ".join(decision.reasons)


def test_terminate_tripwire_has_precedence_over_lower_severity_signals():
    decision = classify_overwatch_observation(
        _observation(
            signals=(
                OverwatchSignal.RESOURCE_CEILING_BREACH,
                OverwatchSignal.UNEXPECTED_NETWORK_EGRESS,
                OverwatchSignal.MONITORING_SUPPRESSION,
            )
        )
    )

    assert decision.disposition == OverwatchDisposition.TERMINATE
    assert decision.triggered_signals == tuple(
        sorted(decision.triggered_signals, key=lambda signal: signal.value)
    )


def test_monitoring_integrity_failure_fails_closed_to_contain_not_terminate():
    decision = classify_overwatch_observation(
        _observation(
            telemetry_complete=False,
            monitor_heartbeat_present=False,
        )
    )

    assert decision.disposition == OverwatchDisposition.CONTAIN
    joined = " ".join(decision.reasons)
    assert "heartbeat is absent" in joined
    assert "telemetry is incomplete" in joined


def test_unknown_or_duplicate_signal_input_is_rejected():
    with pytest.raises(ValidationError):
        OverwatchObservation(
            observation_id="OBS-BAD",
            action_id="ACTION-BAD",
            monitor_id="OVERWATCH-1",
            model_id="MODEL-1",
            model_version="v1",
            observed_at=NOW,
            signals=("NOT_A_REAL_SIGNAL",),
        )

    with pytest.raises(ValidationError, match="duplicates"):
        _observation(
            observation_id="OBS-DUP",
            signals=(
                OverwatchSignal.SANDBOX_ESCAPE,
                OverwatchSignal.SANDBOX_ESCAPE,
            ),
        )


def test_containment_intent_is_durable_idempotent_and_non_authorizing(tmp_path):
    root = tmp_path / "sara"
    store = DurableStore(root)
    decision = classify_overwatch_observation(
        _observation(signals=(OverwatchSignal.UNAUTHORIZED_PERSISTENCE,))
    )

    first = record_overwatch_containment_intent(
        store,
        decision=decision,
        now=NOW + timedelta(seconds=1),
    )
    second = record_overwatch_containment_intent(
        DurableStore(root),
        decision=decision,
        now=NOW + timedelta(seconds=10),
    )

    assert first == second
    assert first.execution_effect_applied is False
    assert first.authorization_effect == "NONE"
    registry = DurableStore(root).get_registry()
    raw = registry[OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY]["OBS-1"]
    assert raw["execution_effect_applied"] is False
    assert raw["authorization_effect"] == "NONE"
    assert raw["disposition"] == "CONTAIN"


def test_continue_decision_cannot_create_containment_intent(tmp_path):
    store = DurableStore(tmp_path / "sara")
    decision = classify_overwatch_observation(_observation())

    with pytest.raises(OverwatchTripwireError, match="CONTINUE"):
        record_overwatch_containment_intent(store, decision=decision, now=NOW)

    assert OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY not in store.get_registry()


def test_observation_id_conflict_fails_closed_without_overwrite(tmp_path):
    store = DurableStore(tmp_path / "sara")
    first_decision = classify_overwatch_observation(
        _observation(signals=(OverwatchSignal.PRIVILEGE_ESCALATION,))
    )
    record_overwatch_containment_intent(store, decision=first_decision, now=NOW)

    conflicting = classify_overwatch_observation(
        _observation(signals=(OverwatchSignal.SANDBOX_ESCAPE,))
    )
    before = store.get_registry()

    with pytest.raises(OverwatchTripwireError, match="conflicts"):
        record_overwatch_containment_intent(
            store,
            decision=conflicting,
            now=NOW + timedelta(seconds=1),
        )

    assert store.get_registry() == before


def test_malformed_existing_containment_state_fails_closed(tmp_path):
    store = DurableStore(tmp_path / "sara")
    store.patch_registry(
        {
            OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY: {
                "OBS-BAD": {"schema": "wrong"}
            }
        }
    )
    decision = classify_overwatch_observation(
        _observation(signals=(OverwatchSignal.UNAUTHORIZED_CREDENTIAL_USE,))
    )
    before = store.get_registry()

    with pytest.raises(OverwatchTripwireError, match="invalid records"):
        record_overwatch_containment_intent(store, decision=decision, now=NOW)

    assert store.get_registry() == before


def test_capacity_failure_never_evicts_existing_containment_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(overwatch, "MAX_OVERWATCH_CONTAINMENT_INTENTS", 1)
    store = DurableStore(tmp_path / "sara")
    first = classify_overwatch_observation(
        _observation(
            "OBS-FIRST",
            signals=(OverwatchSignal.UNAUTHORIZED_CHILD_AGENT_CREATION,),
        )
    )
    second = classify_overwatch_observation(
        _observation(
            "OBS-SECOND",
            signals=(OverwatchSignal.UNEXPECTED_NETWORK_EGRESS,),
        )
    )
    record_overwatch_containment_intent(store, decision=first, now=NOW)

    with pytest.raises(OverwatchTripwireError, match="capacity reached"):
        record_overwatch_containment_intent(
            store,
            decision=second,
            now=NOW + timedelta(seconds=1),
        )

    namespace = store.get_registry()[OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY]
    assert set(namespace) == {"OBS-FIRST"}
