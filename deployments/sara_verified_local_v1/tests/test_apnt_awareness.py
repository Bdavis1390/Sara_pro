from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from worldshepherd_sara.apnt_awareness import (
    APNTEvent,
    ActionState,
    OperatorInput,
    run_scenario,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict:
    return json.loads((ROOT / "fixtures" / "apnt_operator_awareness_synthetic_v1.json").read_text())


def _run():
    fixture = _fixture()
    events = [APNTEvent.model_validate(item) for item in fixture["events"]]
    decisions = [OperatorInput.model_validate(item) for item in fixture["operator_inputs"]]
    return fixture, run_scenario(
        scenario_id=fixture["scenario_id"],
        events=events,
        operator_inputs=decisions,
    )


def test_six_state_scenario_preserves_trace_and_expected_operator_states():
    fixture, result = _run()
    expected = fixture["expected"]

    assert len(result.alerts) == expected["event_count"]
    assert len(result.recommendations) == expected["recommendation_count"]
    assert result.final_integrity_state.value == expected["final_integrity_state"]
    assert result.trace_complete is expected["trace_complete"]
    assert result.action_states[2].value == expected["event_2_action_state"]
    assert result.action_states[5].value == expected["event_5_action_state"]
    assert result.execution_attempted is False


def test_replay_is_deterministic_for_identical_inputs():
    fixture = _fixture()
    events = [APNTEvent.model_validate(item) for item in fixture["events"]]
    decisions = [OperatorInput.model_validate(item) for item in fixture["operator_inputs"]]

    first = run_scenario(scenario_id=fixture["scenario_id"], events=events, operator_inputs=decisions)
    second = run_scenario(scenario_id=fixture["scenario_id"], events=list(reversed(events)), operator_inputs=decisions)

    assert first.deterministic_digest == second.deterministic_digest
    assert first.audit_steps == second.audit_steps


def test_no_operator_response_never_creates_execution_stage():
    fixture = _fixture()
    events = [APNTEvent.model_validate(item) for item in fixture["events"]]
    result = run_scenario(scenario_id=fixture["scenario_id"], events=events, operator_inputs=[])

    for recommendation in result.recommendations:
        assert result.action_states[recommendation.event_sequence] == ActionState.DEFERRED
    assert result.execution_attempted is False
    assert all(step.stage != "SIMULATED_ACTION" for step in result.audit_steps)


def test_approved_operator_response_remains_informational_only():
    fixture, result = _run()
    assert result.action_states[2] == ActionState.APPROVED
    assert result.execution_attempted is False
    assert all(step.stage != "SIMULATED_ACTION" for step in result.audit_steps)
    decision_steps = [
        step for step in result.audit_steps
        if step.event_sequence == 2 and step.stage == "OPERATOR_EVALUATION_RESPONSE"
    ]
    assert len(decision_steps) == 1
    assert decision_steps[0].detail["execution_permitted"] is False


def test_rejected_recovery_stays_informational():
    fixture = _fixture()
    events = [APNTEvent.model_validate(item) for item in fixture["events"]]
    decision = OperatorInput(
        event_sequence=3,
        recommendation_id="REC:3:SUSPECT:KINEMATIC_RESIDUAL_EXCEEDED:ISOLATE_PRIMARY_SOURCE",
        operator_id="TEST-OPERATOR",
        decision="REJECT",
        reason="Synthetic rejection path.",
    )
    result = run_scenario(scenario_id="REJECT-CASE", events=events, operator_inputs=[decision])

    assert result.action_states[3] == ActionState.REJECTED
    assert result.execution_attempted is False


def test_duplicate_sequence_fails_closed():
    fixture = _fixture()
    events = [APNTEvent.model_validate(item) for item in fixture["events"]]
    events.append(events[0].model_copy())

    with pytest.raises(ValueError, match="duplicate event sequence"):
        run_scenario(scenario_id="DUPLICATE", events=events, operator_inputs=[])


def test_unknown_operator_decision_target_fails_closed():
    fixture = _fixture()
    events = [APNTEvent.model_validate(item) for item in fixture["events"]]
    decision = OperatorInput(
        event_sequence=999,
        recommendation_id="REC:999:INVALID",
        operator_id="TEST-OPERATOR",
        decision="APPROVE",
        reason="Invalid synthetic target.",
    )

    with pytest.raises(ValueError, match="unknown events"):
        run_scenario(scenario_id="UNKNOWN-DECISION", events=events, operator_inputs=[decision])


def test_operator_decision_for_no_recommendation_event_fails_closed():
    fixture = _fixture()
    events = [APNTEvent.model_validate(item) for item in fixture["events"]]
    decision = OperatorInput(
        event_sequence=1,
        recommendation_id="REC:1:NONE",
        operator_id="TEST-OPERATOR",
        decision="APPROVE",
        reason="Should not be accepted for a nominal no-recommendation event.",
    )

    with pytest.raises(ValueError, match="without informational recommendations"):
        run_scenario(scenario_id="NO-RECOMMENDATION-DECISION", events=events, operator_inputs=[decision])


def test_operator_response_is_bound_to_exact_recommendation_id():
    fixture = _fixture()
    events = [APNTEvent.model_validate(item) for item in fixture["events"]]
    decision = OperatorInput(
        event_sequence=2,
        recommendation_id="REC:2:DEGRADED:INTEGRITY_MARGIN_REDUCED:DIFFERENT_CANDIDATE",
        operator_id="TEST-OPERATOR",
        decision="APPROVE",
        reason="Mismatched candidate must not inherit the operator response.",
    )

    with pytest.raises(ValueError, match="recommendation mismatch"):
        run_scenario(scenario_id="MISMATCHED-RECOMMENDATION", events=events, operator_inputs=[decision])


def test_hash_chain_links_every_audit_step():
    _, result = _run()
    assert result.audit_steps[0].previous_hash is None
    for prior, current in zip(result.audit_steps, result.audit_steps[1:]):
        assert current.previous_hash == prior.step_hash


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize(
    ("field_path", "bad_value_key"),
    [
        (("position",), "x_m"),
        (("position",), "y_m"),
        (("position",), "z_m"),
        ((), "timestamp_s"),
        ((), "confidence"),
        ((), "integrity_indicator"),
    ],
)
def test_non_finite_replay_evidence_is_rejected(field_path, bad_value_key, bad_value):
    fixture = _fixture()
    payload = dict(fixture["events"][0])
    payload["position"] = dict(payload["position"])

    target = payload
    for key in field_path:
        target = target[key]
    target[bad_value_key] = bad_value

    with pytest.raises(ValueError):
        APNTEvent.model_validate(payload)
