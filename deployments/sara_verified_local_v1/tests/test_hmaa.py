from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worldshepherd_sara.hmaa import (
    AssuranceDisposition,
    HMAAEvent,
    build_evidence_bundle,
    evaluate_event_assurance,
    seal_event,
    verify_chain,
)
from worldshepherd_sara.hmaa_adapter import (
    normalize_entity_event,
    normalize_task_event,
    reconnect_event,
)


def _event(event_id: str, mission_id: str = "SIM-001") -> HMAAEvent:
    return HMAAEvent(
        event_id=event_id,
        mission_id=mission_id,
        event_type="TASK_STATUS_CHANGE",
        source_timestamp=datetime(2026, 9, 4, 20, 0, tzinfo=timezone.utc),
        payload={"status": "IN_PROGRESS"},
    )


def test_hash_chain_verifies_and_bundle_carries_final_hash():
    first = seal_event(_event("E1"))
    second = seal_event(_event("E2"), first.event_hash)

    ok, errors = verify_chain([first, second])
    assert ok is True
    assert errors == []

    bundle = build_evidence_bundle("SIM-001", [first, second])
    assert bundle.final_chain_hash == second.event_hash


def test_hash_chain_detects_payload_tampering():
    event = seal_event(_event("E1"))
    tampered = event.model_copy(update={"payload": {"status": "COMPLETE"}})

    ok, errors = verify_chain([tampered])
    assert ok is False
    assert any("event_hash" in error for error in errors)


def test_policy_engine_outage_never_implies_approval():
    assessment = evaluate_event_assurance(policy_engine_available=False)
    assert assessment.disposition == AssuranceDisposition.INDETERMINATE
    assert any("must not be inferred" in reason for reason in assessment.reasons)


def test_checksum_failure_requires_review():
    assessment = evaluate_event_assurance(checksum_valid=False)
    assert assessment.disposition == AssuranceDisposition.REVIEW


def test_degraded_heartbeat_warns_without_becoming_flight_control():
    assessment = evaluate_event_assurance(connection_healthy=False)
    assert assessment.disposition == AssuranceDisposition.WARN
    assert any("heartbeat" in reason for reason in assessment.reasons)


def test_adapter_normalizes_entity_and_task_payloads():
    entity = normalize_entity_event(
        {
            "entityId": "AIRCRAFT-SIM-1",
            "eventType": "update",
            "timestamp": "2026-09-04T20:00:00Z",
        },
        mission_id="SIM-001",
    )
    task = normalize_task_event(
        {
            "taskId": "TASK-1",
            "agentId": "AIRCRAFT-SIM-1",
            "status": "in_progress",
            "timestamp": "2026-09-04T20:00:01Z",
        },
        mission_id="SIM-001",
    )

    assert entity.entity_id == "AIRCRAFT-SIM-1"
    assert entity.event_type == "ENTITY_UPDATE"
    assert task.task_id == "TASK-1"
    assert task.entity_id == "AIRCRAFT-SIM-1"
    assert task.event_type == "TASK_IN_PROGRESS"


def test_bundle_rejects_cross_mission_evidence():
    first = seal_event(_event("E1", mission_id="SIM-001"))
    second = seal_event(_event("E2", mission_id="SIM-002"), first.event_hash)

    with pytest.raises(ValueError, match="mission_id"):
        build_evidence_bundle("SIM-001", [first, second])


def test_reconnect_attempt_must_be_positive():
    with pytest.raises(ValueError, match="at least 1"):
        reconnect_event(mission_id="SIM-001", stream="entities", attempt=0)
