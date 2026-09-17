from __future__ import annotations

from copy import deepcopy

import pytest

from worldshepherd_sara.spacelink_adapter import ContactDisposition, SpaceContactStatus
from worldshepherd_sara.spacelink_eventbridge import (
    AwsGroundStationEventBridgeAdapter,
    apply_contact_event,
    digital_twin_event_claims_boundary,
    event_to_mission_event,
)


def _event(
    *,
    event_id: str = "01234567-0123-0123-0123-012345678901",
    event_time: str = "2026-09-12T17:50:00Z",
    contact_status: str = "PASS",
    ground_station: str = "Digital Twin Hawaii 1",
) -> dict:
    return {
        "version": "0",
        "id": event_id,
        "account": "123456789012",
        "time": event_time,
        "region": "us-west-2",
        "source": "aws.groundstation",
        "resources": [
            "arn:aws:groundstation:us-west-2:123456789012:contact/11111111-1111-1111-1111-111111111111"
        ],
        "detail-type": "Ground Station Contact State Change",
        "detail": {
            "contactId": "11111111-1111-1111-1111-111111111111",
            "groundstationId": ground_station,
            "missionProfileArn": "arn:aws:groundstation:us-west-2:123456789012:mission-profile/22222222-2222-2222-2222-222222222222",
            "satelliteArn": "arn:aws:groundstation::123456789012:satellite/33333333-3333-3333-3333-333333333333",
            "contactStatus": contact_status,
        },
    }


def test_documented_contact_event_normalizes_to_active_projection():
    adapter = AwsGroundStationEventBridgeAdapter()
    event = adapter.normalize_event(_event())
    state = apply_contact_event(None, event)

    assert event.delivery_semantics == "BEST_EFFORT"
    assert event.contact.status == SpaceContactStatus.PASS
    assert event.contact.disposition == ContactDisposition.ACTIVE
    assert state.current_status == SpaceContactStatus.PASS
    assert state.event_count == 1
    assert state.terminal is False
    assert state.overwatch_snapshot()["claims_scope"].startswith("provider-event projection only")


def test_eventbridge_ingestion_rejects_wrong_source_and_detail_type():
    adapter = AwsGroundStationEventBridgeAdapter()

    wrong_source = _event()
    wrong_source["source"] = "aws.ec2"
    with pytest.raises(ValueError, match="unexpected EventBridge source"):
        adapter.normalize_event(wrong_source)

    wrong_type = _event()
    wrong_type["detail-type"] = "Ground Station Ephemeris Status Change"
    with pytest.raises(ValueError, match="unexpected EventBridge detail type"):
        adapter.normalize_event(wrong_type)


def test_duplicate_provider_event_id_is_idempotent():
    adapter = AwsGroundStationEventBridgeAdapter()
    event = adapter.normalize_event(_event())
    first = apply_contact_event(None, event)
    second = apply_contact_event(first, event)

    assert second == first
    assert second.event_count == 1
    assert second.applied_event_ids == [event.provider_event_id]


def test_out_of_order_provider_event_fails_closed():
    adapter = AwsGroundStationEventBridgeAdapter()
    later = adapter.normalize_event(
        _event(event_id="later", event_time="2026-09-12T18:00:00Z", contact_status="PASS")
    )
    state = apply_contact_event(None, later)

    earlier = adapter.normalize_event(
        _event(event_id="earlier", event_time="2026-09-12T17:59:59Z", contact_status="PREPASS")
    )
    with pytest.raises(ValueError, match="out-of-order provider event"):
        apply_contact_event(state, earlier)


def test_terminal_contact_state_cannot_transition_to_different_state():
    adapter = AwsGroundStationEventBridgeAdapter()
    completed = adapter.normalize_event(
        _event(event_id="completed", event_time="2026-09-12T18:10:00Z", contact_status="COMPLETED")
    )
    state = apply_contact_event(None, completed)
    assert state.terminal is True

    impossible = adapter.normalize_event(
        _event(event_id="post-terminal", event_time="2026-09-12T18:11:00Z", contact_status="PASS")
    )
    with pytest.raises(ValueError, match="terminal contact state"):
        apply_contact_event(state, impossible)


def test_lifecycle_projection_advances_to_terminal_state():
    adapter = AwsGroundStationEventBridgeAdapter()
    statuses = ["SCHEDULED", "PREPASS", "PASS", "POSTPASS", "COMPLETED"]
    state = None
    for index, status in enumerate(statuses, start=1):
        state = apply_contact_event(
            state,
            adapter.normalize_event(
                _event(
                    event_id=f"event-{index}",
                    event_time=f"2026-09-12T18:{index:02d}:00Z",
                    contact_status=status,
                )
            ),
        )

    assert state is not None
    assert state.current_status == SpaceContactStatus.COMPLETED
    assert state.disposition == ContactDisposition.SUCCEEDED
    assert state.event_count == len(statuses)
    assert state.terminal is True


def test_event_converts_to_replayable_mission_evidence():
    event = AwsGroundStationEventBridgeAdapter().normalize_event(_event())
    mission_event = event_to_mission_event(event, sequence=9, t_seconds=12.5)

    assert mission_event.sequence == 9
    assert mission_event.event_type == "spacelink_provider_contact_event"
    assert mission_event.payload["provider_event_id"] == event.provider_event_id
    assert mission_event.payload["delivery_semantics"] == "BEST_EFFORT"
    assert mission_event.payload["contact_status"] == "PASS"


def test_digital_twin_claims_boundary_excludes_telemetry_and_rf():
    event = AwsGroundStationEventBridgeAdapter().normalize_event(_event())
    boundary = digital_twin_event_claims_boundary(event)
    assert "do not currently support data delivery or telemetry delivery" in boundary
    assert "No RF" in boundary

    production = AwsGroundStationEventBridgeAdapter().normalize_event(
        _event(ground_station="Hawaii 1")
    )
    with pytest.raises(ValueError, match="not identified as an AWS Ground Station digital-twin"):
        digital_twin_event_claims_boundary(production)


def test_detail_type_alias_is_accepted_but_missing_time_is_rejected():
    adapter = AwsGroundStationEventBridgeAdapter()
    payload = _event()
    payload["detailType"] = payload.pop("detail-type")
    assert adapter.normalize_event(payload).contact.status == SpaceContactStatus.PASS

    missing_time = deepcopy(payload)
    missing_time.pop("time")
    with pytest.raises(ValueError, match="EventBridge time"):
        adapter.normalize_event(missing_time)
