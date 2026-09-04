from __future__ import annotations

import json
from pathlib import Path

import pytest

from worldshepherd_sara.hmaa_lattice_contract import (
    LATTICE_PUBLIC_CONTRACT_VERSION,
    LatticeEnvelopeKind,
    LatticeReadTransport,
    LatticeStream,
    parse_entity_stream_message,
    parse_task_stream_message,
    validate_entity_stream_request,
    validate_task_stream_request,
)
from worldshepherd_sara.hmaa_interop import run_public_contract_replay


FIXTURE = Path(__file__).parent.parent / "fixtures" / "hmaa_lattice_public_contract.json"


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_public_contract_fixture_requests_validate():
    fixture = _fixture()
    assert validate_entity_stream_request(fixture["entity_request"])[
        "heartbeatIntervalMS"
    ] == 30000
    assert validate_task_stream_request(fixture["task_request"])["rateLimit"] == 250


def test_task_rate_limit_contract_is_enforced():
    with pytest.raises(ValueError, match="at least 250"):
        validate_task_stream_request({"rateLimit": 249})
    assert validate_task_stream_request({"rateLimit": 0})["rateLimit"] == 0


def test_parent_task_id_contract_rejects_mutually_exclusive_filters():
    with pytest.raises(ValueError, match="mutually exclusive"):
        validate_task_stream_request(
            {"parentTaskId": "PARENT-1", "statusFilter": {"include": ["open"]}}
        )


def test_entity_request_contract_rejects_bad_heartbeat_and_components():
    with pytest.raises(ValueError, match="positive integer"):
        validate_entity_stream_request({"heartbeatIntervalMS": 0})
    with pytest.raises(ValueError, match="non-empty strings"):
        validate_entity_stream_request({"componentsToInclude": [""]})


def test_entity_envelope_requires_exactly_one_variant():
    with pytest.raises(ValueError, match="exactly one"):
        parse_entity_stream_message({}, mission_id="SIM-CONTRACT")
    with pytest.raises(ValueError, match="exactly one"):
        parse_entity_stream_message(
            {
                "heartbeat": {"timestamp": "2026-09-04T22:30:00Z"},
                "entity": {"entity": {"entityId": "E-1"}},
            },
            mission_id="SIM-CONTRACT",
        )


def test_task_envelope_requires_exactly_one_variant():
    with pytest.raises(ValueError, match="exactly one"):
        parse_task_stream_message({}, mission_id="SIM-CONTRACT")


def test_identical_public_stream_envelope_gets_stable_source_event_identity():
    message = {
        "entity": {
            "eventType": "UPDATE",
            "entity": {
                "entityId": "AIRCRAFT-SIM-1",
                "timestamp": "2026-09-04T22:30:01Z",
            },
        }
    }
    first = parse_entity_stream_message(message, mission_id="SIM-CONTRACT")
    second = parse_entity_stream_message(message, mission_id="SIM-CONTRACT")

    assert first.source_event_id == second.source_event_id
    assert first.hmaa_event.event_id == second.hmaa_event.event_id
    assert first.kind == LatticeEnvelopeKind.ENTITY
    assert first.stream == LatticeStream.ENTITIES


def test_fixture_messages_normalize_into_expected_contract_kinds():
    fixture = _fixture()
    items = fixture["stream_items"]
    entity_heartbeat = parse_entity_stream_message(
        items[0]["message"], mission_id="SIM-CONTRACT"
    )
    entity = parse_entity_stream_message(
        items[1]["message"], mission_id="SIM-CONTRACT"
    )
    task_heartbeat = parse_task_stream_message(
        items[2]["message"], mission_id="SIM-CONTRACT"
    )
    task = parse_task_stream_message(
        items[3]["message"], mission_id="SIM-CONTRACT"
    )

    assert entity_heartbeat.kind == LatticeEnvelopeKind.HEARTBEAT
    assert entity.kind == LatticeEnvelopeKind.ENTITY
    assert entity.hmaa_event.entity_id == "AIRCRAFT-SIM-1"
    assert task_heartbeat.kind == LatticeEnvelopeKind.HEARTBEAT
    assert task.kind == LatticeEnvelopeKind.TASK
    assert task.hmaa_event.task_id == "TASK-SIM-1"


def test_public_contract_replay_emits_verifiable_non_live_manifest():
    fixture = _fixture()
    result = run_public_contract_replay(
        mission_id="SIM-LATTICE-CONTRACT-001",
        items=fixture["stream_items"],
    )

    assert result.manifest.contract_version == LATTICE_PUBLIC_CONTRACT_VERSION
    assert result.manifest.live_environment_validated is False
    assert result.manifest.event_count == 4
    assert result.manifest.fixture_sha256.startswith("sha256:")
    assert result.manifest.final_chain_hash == result.evidence_bundle.final_chain_hash
    assert len(result.evidence_bundle.events) == 4
    assert result.manifest.disposition_counts == {"ALLOW": 4}


def test_read_transport_protocol_contains_only_read_stream_methods():
    class FakeReadTransport:
        def stream_entities(self, request):
            return []

        def stream_tasks(self, request):
            return []

    fake = FakeReadTransport()
    assert isinstance(fake, LatticeReadTransport)
    assert not hasattr(fake, "publish_entity")
    assert not hasattr(fake, "create_task")
