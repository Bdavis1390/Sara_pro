from __future__ import annotations

from worldshepherd_sara.hmaa_lattice_capture import (
    SandboxReadCapturePlan,
    capture_readonly_stream_evidence,
)
from worldshepherd_sara.hmaa_lattice_contract import LatticeReadTransport


class FakeReadTransport:
    def __init__(self) -> None:
        self.entity_closed = False
        self.task_closed = False

    def stream_entities(self, request):
        try:
            yield {
                "heartbeat": {
                    "timestamp": "2026-09-04T22:45:00Z",
                    "sequence": 1,
                }
            }
            yield {
                "entity": {
                    "eventType": "UPDATE",
                    "entity": {
                        "entityId": "AIRCRAFT-SIM-1",
                        "timestamp": "2026-09-04T22:45:01Z",
                    },
                }
            }
            yield {
                "entity": {
                    "eventType": "UPDATE",
                    "entity": {
                        "entityId": "SHOULD-NOT-BE-CAPTURED",
                        "timestamp": "2026-09-04T22:45:02Z",
                    },
                }
            }
        finally:
            self.entity_closed = True

    def stream_tasks(self, request):
        try:
            yield {
                "heartbeat": {
                    "timestamp": "2026-09-04T22:45:03Z",
                    "sequence": 1,
                }
            }
            yield {
                "task_event": {
                    "eventType": "UPDATE",
                    "task": {
                        "taskId": "TASK-SIM-1",
                        "agentId": "AIRCRAFT-SIM-1",
                        "status": "in_progress",
                        "updateTime": "2026-09-04T22:45:04Z",
                    },
                }
            }
        finally:
            self.task_closed = True


def test_capture_runner_is_finite_closes_streams_and_builds_evidence():
    transport = FakeReadTransport()
    assert isinstance(transport, LatticeReadTransport)

    result = capture_readonly_stream_evidence(
        transport=transport,
        mission_id="SIM-SANDBOX-CANDIDATE-001",
        plan=SandboxReadCapturePlan(
            entity_request={"heartbeatIntervalMS": 30000},
            task_request={"heartbeatIntervalMs": 30000, "rateLimit": 250},
            max_entity_messages=2,
            max_task_messages=2,
        ),
    )

    assert result.live_environment_validated is False
    assert result.captured_entity_messages == 2
    assert result.captured_task_messages == 2
    assert result.interop.manifest.event_count == 4
    assert result.interop.manifest.live_environment_validated is False
    assert result.interop.manifest.disposition_counts == {"ALLOW": 4}
    assert result.interop.evidence_bundle.final_chain_hash is not None
    assert transport.entity_closed is True
    assert transport.task_closed is True
    assert all(
        event.entity_id != "SHOULD-NOT-BE-CAPTURED"
        for event in result.interop.evidence_bundle.events
    )


def test_capture_runner_can_sample_only_one_stream():
    transport = FakeReadTransport()
    result = capture_readonly_stream_evidence(
        transport=transport,
        mission_id="SIM-SANDBOX-CANDIDATE-002",
        plan=SandboxReadCapturePlan(
            max_entity_messages=1,
            max_task_messages=0,
        ),
    )

    assert result.captured_entity_messages == 1
    assert result.captured_task_messages == 0
    assert result.interop.manifest.event_count == 1


def test_capture_runner_rejects_zero_message_plan():
    transport = FakeReadTransport()
    try:
        capture_readonly_stream_evidence(
            transport=transport,
            mission_id="SIM-SANDBOX-CANDIDATE-003",
            plan=SandboxReadCapturePlan(
                max_entity_messages=0,
                max_task_messages=0,
            ),
        )
    except ValueError as exc:
        assert "at least one" in str(exc)
    else:
        raise AssertionError("zero-message capture plan should fail")
