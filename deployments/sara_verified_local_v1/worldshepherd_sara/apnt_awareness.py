from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


CLAIMS_BOUNDARY = "SIMULATED_ONLY / SYNTHETIC APNT OPERATOR-AWARENESS DEMONSTRATOR / INFORMATIONAL DECISION AID ONLY"


class IntegrityState(str, Enum):
    NOMINAL = "NOMINAL"
    DEGRADED = "DEGRADED"
    SUSPECT = "SUSPECT"
    DISAGREEMENT = "DISAGREEMENT"
    RECOVERING = "RECOVERING"
    RESTORED = "RESTORED"


class OperatorDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    DEFER = "DEFER"


class ActionState(str, Enum):
    """Operator evaluation state only; never represents platform execution."""

    NONE = "NONE"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class PositionEstimate(BaseModel):
    x_m: float = Field(allow_inf_nan=False)
    y_m: float = Field(allow_inf_nan=False)
    z_m: float = Field(allow_inf_nan=False)


class APNTEvent(BaseModel):
    sequence: int = Field(ge=1)
    timestamp_s: float = Field(ge=0, allow_inf_nan=False)
    source: str = Field(min_length=1)
    integrity_state: IntegrityState
    position: PositionEstimate
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    integrity_indicator: float = Field(ge=0, le=1, allow_inf_nan=False)
    anomaly_code: str | None = None
    reason_code: str = Field(min_length=1)
    recommended_recovery_candidate: str | None = None


class OperatorInput(BaseModel):
    event_sequence: int = Field(ge=1)
    recommendation_id: str = Field(min_length=1)
    operator_id: str = Field(min_length=1)
    decision: OperatorDecision
    reason: str = Field(min_length=1)


class AwarenessAlert(BaseModel):
    event_sequence: int
    severity: str
    summary: str
    evidence_refs: list[str]


class RecoveryRecommendation(BaseModel):
    recommendation_id: str
    event_sequence: int
    candidate: str
    rationale: str
    action_state: ActionState = ActionState.PROPOSED
    informational_only: bool = True


class AuditStep(BaseModel):
    step_index: int = Field(ge=1)
    event_sequence: int
    stage: str
    detail: dict[str, Any]
    previous_hash: str | None
    step_hash: str


class APNTReplayResult(BaseModel):
    scenario_id: str
    alerts: list[AwarenessAlert]
    recommendations: list[RecoveryRecommendation]
    action_states: dict[int, ActionState]
    audit_steps: list[AuditStep]
    final_integrity_state: IntegrityState
    trace_complete: bool
    execution_attempted: bool = False
    deterministic_digest: str
    claims_boundary: str = CLAIMS_BOUNDARY


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def replay_events(events: list[APNTEvent]) -> tuple[APNTEvent, ...]:
    ordered = tuple(sorted(events, key=lambda item: (item.sequence, item.timestamp_s)))
    seen: set[int] = set()
    last_time = -1.0
    for event in ordered:
        if event.sequence in seen:
            raise ValueError(f"duplicate event sequence: {event.sequence}")
        if event.timestamp_s < last_time:
            raise ValueError("event timestamps must be monotonic after sequence ordering")
        seen.add(event.sequence)
        last_time = event.timestamp_s
    return ordered


def alert_for_event(event: APNTEvent) -> AwarenessAlert:
    severity = {
        IntegrityState.NOMINAL: "INFO",
        IntegrityState.DEGRADED: "CAUTION",
        IntegrityState.SUSPECT: "WARNING",
        IntegrityState.DISAGREEMENT: "WARNING",
        IntegrityState.RECOVERING: "CAUTION",
        IntegrityState.RESTORED: "INFO",
    }[event.integrity_state]
    return AwarenessAlert(
        event_sequence=event.sequence,
        severity=severity,
        summary=(
            f"{event.source}: {event.integrity_state.value}; reason={event.reason_code}; "
            f"confidence={event.confidence:.3f}; integrity={event.integrity_indicator:.3f}"
        ),
        evidence_refs=[
            f"event:{event.sequence}",
            f"source:{event.source}",
            f"reason:{event.reason_code}",
        ],
    )


def recommendation_for_event(event: APNTEvent) -> RecoveryRecommendation | None:
    if event.recommended_recovery_candidate is None:
        return None
    if event.integrity_state not in {
        IntegrityState.DEGRADED,
        IntegrityState.SUSPECT,
        IntegrityState.DISAGREEMENT,
        IntegrityState.RECOVERING,
    }:
        return None
    recommendation_id = (
        f"REC:{event.sequence}:{event.integrity_state.value}:{event.reason_code}:"
        f"{event.recommended_recovery_candidate}"
    )
    return RecoveryRecommendation(
        recommendation_id=recommendation_id,
        event_sequence=event.sequence,
        candidate=event.recommended_recovery_candidate,
        rationale=(
            f"Informational candidate supplied by synthetic upstream integrity event after "
            f"{event.integrity_state.value}: {event.reason_code}. Worldshepherd does not "
            "independently validate the navigation estimator and this POC cannot execute recovery actions."
        ),
    )


def _append_audit(
    audit_steps: list[AuditStep],
    *,
    event_sequence: int,
    stage: str,
    detail: dict[str, Any],
) -> None:
    previous = audit_steps[-1].step_hash if audit_steps else None
    payload = {
        "step_index": len(audit_steps) + 1,
        "event_sequence": event_sequence,
        "stage": stage,
        "detail": detail,
        "previous_hash": previous,
    }
    audit_steps.append(AuditStep(step_hash=_sha256(payload), **payload))


def run_scenario(
    *,
    scenario_id: str,
    events: list[APNTEvent],
    operator_inputs: list[OperatorInput],
) -> APNTReplayResult:
    ordered = replay_events(events)
    recommendations_by_event = {
        event.sequence: recommendation
        for event in ordered
        if (recommendation := recommendation_for_event(event)) is not None
    }

    decisions: dict[int, OperatorInput] = {}
    for decision in operator_inputs:
        if decision.event_sequence in decisions:
            raise ValueError(f"duplicate operator decision for event {decision.event_sequence}")
        decisions[decision.event_sequence] = decision

    event_sequences = {event.sequence for event in ordered}
    unknown_decisions = sorted(set(decisions) - event_sequences)
    if unknown_decisions:
        raise ValueError(f"operator decision references unknown events: {unknown_decisions}")

    non_actionable_decisions = sorted(set(decisions) - set(recommendations_by_event))
    if non_actionable_decisions:
        raise ValueError(
            f"operator decision references events without informational recommendations: {non_actionable_decisions}"
        )

    for event_sequence, operator in decisions.items():
        expected = recommendations_by_event[event_sequence]
        if operator.recommendation_id != expected.recommendation_id:
            raise ValueError(
                f"operator decision recommendation mismatch for event {event_sequence}: "
                f"expected {expected.recommendation_id}"
            )

    alerts: list[AwarenessAlert] = []
    recommendations: list[RecoveryRecommendation] = []
    action_states: dict[int, ActionState] = {}
    audit_steps: list[AuditStep] = []

    for event in ordered:
        _append_audit(
            audit_steps,
            event_sequence=event.sequence,
            stage="INGEST",
            detail={"event": event.model_dump(mode="json")},
        )
        alert = alert_for_event(event)
        alerts.append(alert)
        _append_audit(
            audit_steps,
            event_sequence=event.sequence,
            stage="ALERT",
            detail={"alert": alert.model_dump(mode="json")},
        )

        recommendation = recommendations_by_event.get(event.sequence)
        if recommendation is None:
            action_states[event.sequence] = ActionState.NONE
            _append_audit(
                audit_steps,
                event_sequence=event.sequence,
                stage="NO_RECOMMENDATION",
                detail={"operator_response_state": ActionState.NONE.value},
            )
            continue

        recommendations.append(recommendation)
        action_states[event.sequence] = ActionState.PROPOSED
        _append_audit(
            audit_steps,
            event_sequence=event.sequence,
            stage="INFORMATIONAL_RECOMMENDATION",
            detail={"recommendation": recommendation.model_dump(mode="json")},
        )

        operator = decisions.get(event.sequence)
        if operator is None:
            action_states[event.sequence] = ActionState.DEFERRED
            _append_audit(
                audit_steps,
                event_sequence=event.sequence,
                stage="OPERATOR_EVALUATION_RESPONSE",
                detail={
                    "recommendation_id": recommendation.recommendation_id,
                    "decision": OperatorDecision.DEFER.value,
                    "operator_id": "NO_DECISION_RECORDED",
                    "reason": "No operator evaluation response supplied.",
                    "operator_response_state": ActionState.DEFERRED.value,
                    "execution_permitted": False,
                },
            )
            continue

        if operator.decision == OperatorDecision.APPROVE:
            action_states[event.sequence] = ActionState.APPROVED
        elif operator.decision == OperatorDecision.REJECT:
            action_states[event.sequence] = ActionState.REJECTED
        else:
            action_states[event.sequence] = ActionState.DEFERRED

        _append_audit(
            audit_steps,
            event_sequence=event.sequence,
            stage="OPERATOR_EVALUATION_RESPONSE",
            detail={
                "recommendation_id": operator.recommendation_id,
                "decision": operator.decision.value,
                "operator_id": operator.operator_id,
                "reason": operator.reason,
                "operator_response_state": action_states[event.sequence].value,
                "execution_permitted": False,
                "boundary": "Phase-I POC is an informational decision aid only; no action routing or platform command exists.",
            },
        )

    expected_trace_events = {event.sequence for event in ordered}
    audited_ingest_events = {
        item.event_sequence for item in audit_steps if item.stage == "INGEST"
    }
    alert_events = {alert.event_sequence for alert in alerts}
    trace_complete = (
        expected_trace_events == audited_ingest_events == alert_events
        and all(
            item.previous_hash == (audit_steps[index - 1].step_hash if index else None)
            for index, item in enumerate(audit_steps)
        )
    )

    result_payload = {
        "scenario_id": scenario_id,
        "alerts": [item.model_dump(mode="json") for item in alerts],
        "recommendations": [item.model_dump(mode="json") for item in recommendations],
        "action_states": {str(key): value.value for key, value in sorted(action_states.items())},
        "audit_steps": [item.model_dump(mode="json") for item in audit_steps],
        "final_integrity_state": ordered[-1].integrity_state.value,
        "trace_complete": trace_complete,
        "execution_attempted": False,
        "claims_boundary": CLAIMS_BOUNDARY,
    }
    return APNTReplayResult(
        deterministic_digest=_sha256(result_payload),
        **result_payload,
    )
