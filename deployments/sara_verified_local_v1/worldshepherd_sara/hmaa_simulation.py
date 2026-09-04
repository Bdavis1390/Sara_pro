from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from .hmaa import (
    AssuranceAssessment,
    AssuranceDisposition,
    HMAAEvidenceBundle,
    HMAAEvent,
    build_evidence_bundle,
    evaluate_event_assurance,
    seal_event,
)
from .hmaa_adapter import (
    heartbeat_event,
    normalize_entity_event,
    normalize_task_event,
    reconnect_event,
)


class SILStep(BaseModel):
    kind: Literal["entity", "task", "heartbeat", "reconnect", "observation"]
    payload: dict[str, Any] = Field(default_factory=dict)
    connection_healthy: bool = True
    policy_engine_available: bool = True
    duplicate_event: bool = False
    out_of_order_event: bool = False
    checksum_valid: bool = True


class SILStepResult(BaseModel):
    index: int = Field(ge=0)
    event: HMAAEvent
    assessment: AssuranceAssessment


class SILScenarioResult(BaseModel):
    mission_id: str = Field(min_length=1)
    steps: list[SILStepResult]
    evidence_bundle: HMAAEvidenceBundle
    disposition_counts: dict[str, int]


def _observation_event(payload: dict[str, Any], mission_id: str) -> HMAAEvent:
    return HMAAEvent(
        event_id=str(uuid4()),
        mission_id=mission_id,
        event_type="ASSURANCE_OBSERVATION",
        source_timestamp=datetime.now(timezone.utc),
        payload=payload,
    )


def _event_from_step(step: SILStep, mission_id: str) -> HMAAEvent:
    if step.kind == "entity":
        return normalize_entity_event(step.payload, mission_id=mission_id)
    if step.kind == "task":
        return normalize_task_event(step.payload, mission_id=mission_id)
    if step.kind == "heartbeat":
        stream = str(step.payload.get("stream", "entities"))
        return heartbeat_event(mission_id=mission_id, stream=stream)
    if step.kind == "reconnect":
        stream = str(step.payload.get("stream", "entities"))
        attempt = int(step.payload.get("attempt", 1))
        return reconnect_event(
            mission_id=mission_id,
            stream=stream,
            attempt=attempt,
        )
    return _observation_event(step.payload, mission_id)


def run_sil_scenario(
    *, mission_id: str, steps: list[SILStep]
) -> SILScenarioResult:
    if not mission_id:
        raise ValueError("mission_id must not be empty")
    if not steps:
        raise ValueError("SIL scenario must contain at least one step")

    results: list[SILStepResult] = []
    sealed_events: list[HMAAEvent] = []
    previous_hash: str | None = None

    for index, step in enumerate(steps):
        event = _event_from_step(step, mission_id)
        sealed = seal_event(event, previous_hash)
        assessment = evaluate_event_assurance(
            connection_healthy=step.connection_healthy,
            policy_engine_available=step.policy_engine_available,
            duplicate_event=step.duplicate_event,
            out_of_order_event=step.out_of_order_event,
            checksum_valid=step.checksum_valid,
        )
        results.append(
            SILStepResult(index=index, event=sealed, assessment=assessment)
        )
        sealed_events.append(sealed)
        previous_hash = sealed.event_hash

    bundle = build_evidence_bundle(mission_id, sealed_events)
    counts = Counter(result.assessment.disposition.value for result in results)
    normalized_counts = {
        disposition.value: counts.get(disposition.value, 0)
        for disposition in AssuranceDisposition
    }
    return SILScenarioResult(
        mission_id=mission_id,
        steps=results,
        evidence_bundle=bundle,
        disposition_counts=normalized_counts,
    )


def load_sil_steps(value: list[dict[str, Any]]) -> list[SILStep]:
    return [SILStep.model_validate(item) for item in value]
