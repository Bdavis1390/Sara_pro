from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from worldshepherd_sara.spacelink_adapter import (
    AWS_DIGITAL_TWIN_BOUNDARY,
    AwsGroundStationContactAdapter,
    ContactDisposition,
    ContactReservationProposal,
    SpaceContactStatus,
    SyntheticGroundNetworkAdapter,
    contact_to_mission_event,
)


def test_synthetic_adapter_normalizes_completed_contact():
    contact = SyntheticGroundNetworkAdapter().normalize_contact(
        {
            "provider": "SYNTHETIC_GS",
            "contact_id": "fixture-contact-001",
            "status": "COMPLETED",
            "version_id": 1,
            "ground_station": "fixture-station",
            "start_time": "2026-09-12T12:00:00Z",
            "end_time": "2026-09-12T12:10:00Z",
            "last_updated": "2026-09-12T12:10:30Z",
        }
    )
    assert contact.status == SpaceContactStatus.COMPLETED
    assert contact.disposition == ContactDisposition.SUCCEEDED
    assert contact.attributes["claims_scope"] == "synthetic fixture only"


def test_frozen_synthetic_fixture_normalizes_every_contact():
    fixture_path = (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "spacelink_synthetic_v1.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    adapter = SyntheticGroundNetworkAdapter()
    contacts = [adapter.normalize_contact(item) for item in fixture["contacts"]]
    assert len(contacts) == 7
    assert contacts[0].status == SpaceContactStatus.SCHEDULING
    assert contacts[-2].status == SpaceContactStatus.COMPLETED
    assert contacts[-1].status == SpaceContactStatus.FAILED_TO_SCHEDULE
    assert contacts[-1].disposition == ContactDisposition.FAILED


def test_aws_adapter_normalizes_documented_contact_fields():
    contact = AwsGroundStationContactAdapter().normalize_contact(
        {
            "contactId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "contactStatus": "SCHEDULED",
            "versionId": 2,
            "groundStation": "Digital Twin Hawaii 1",
            "startTime": 1789214400,
            "endTime": 1789215000,
            "lastUpdated": 1789214100,
        }
    )
    assert contact.provider == "AWS_GROUND_STATION"
    assert contact.status == SpaceContactStatus.SCHEDULED
    assert contact.disposition == ContactDisposition.SCHEDULED
    assert contact.version_id == 2
    assert contact.start_time is not None
    assert contact.start_time.tzinfo is not None
    assert contact.attributes["status_field"] == "contactStatus"


def test_aws_adapter_accepts_documented_status_alias_from_list_response():
    contact = AwsGroundStationContactAdapter().normalize_contact(
        {
            "contactId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "status": "FAILED_TO_SCHEDULE",
            "failureCodes": ["RESOURCE_CONFLICT"],
            "failureMessage": "synthetic test failure",
        }
    )
    assert contact.disposition == ContactDisposition.FAILED
    assert contact.failure_codes == ["RESOURCE_CONFLICT"]
    assert contact.attributes["status_field"] == "status"


def test_aws_adapter_normalizes_describe_contact_nested_version_fields():
    contact = AwsGroundStationContactAdapter().normalize_contact(
        {
            "contactId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "contactStatus": "AWS_FAILED",
            "groundStation": "Digital Twin Hawaii 1",
            "startTime": 1789214400,
            "endTime": 1789215000,
            "version": {
                "versionId": 4,
                "lastUpdated": 1789215100,
                "failureCodes": ["INTERNAL_ERROR"],
                "failureMessage": "synthetic describe-contact failure",
                "status": "ACTIVE",
            },
        }
    )
    assert contact.version_id == 4
    assert contact.last_updated is not None
    assert contact.failure_codes == ["INTERNAL_ERROR"]
    assert contact.failure_message == "synthetic describe-contact failure"
    assert contact.attributes["provider_shape"] == "DescribeContact"
    assert contact.authoritative_spec_ref.endswith("API_DescribeContact.html")


def test_unknown_provider_status_fails_closed():
    with pytest.raises(ValueError, match="unrecognized space-contact status"):
        AwsGroundStationContactAdapter().normalize_contact(
            {
                "contactId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "contactStatus": "MAGICALLY_WORKING",
            }
        )


def test_reservation_proposal_is_non_executable_and_has_claims_boundary():
    proposal = ContactReservationProposal(
        proposal_id="WS-SL-001",
        start_time=datetime(2026, 9, 30, 16, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 9, 30, 16, 10, tzinfo=timezone.utc),
        ground_station="Digital Twin Ohio 1",
        mission_profile_ref="arn:aws:groundstation:region:account:mission-profile/example",
        satellite_ref="arn:aws:groundstation:region:account:satellite/example",
        requested_by="SSPADAWANZZ",
        purpose="schema and governance validation",
    )
    assert proposal.execution_allowed is False
    assert proposal.authority_required == "identified-human-authority"
    preview = proposal.provider_request_preview()
    assert set(preview) == {
        "startTime",
        "endTime",
        "groundStation",
        "missionProfileArn",
        "satelliteArn",
    }
    boundary = proposal.claims_boundary()
    assert "no AWS contact reservation" in boundary
    assert "no" in boundary.lower()


def test_digital_twin_boundary_explicitly_excludes_data_and_telemetry_delivery():
    assert AWS_DIGITAL_TWIN_BOUNDARY.scheduling_api_test is True
    assert AWS_DIGITAL_TWIN_BOUNDARY.spectrum_license_required_for_digital_twin_api_test is False
    assert AWS_DIGITAL_TWIN_BOUNDARY.data_delivery_supported is False
    assert AWS_DIGITAL_TWIN_BOUNDARY.telemetry_delivery_supported is False


def test_contact_state_converts_to_replayable_mission_event():
    contact = AwsGroundStationContactAdapter().normalize_contact(
        {
            "contactId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "contactStatus": "AWS_FAILED",
            "versionId": 3,
            "failureMessage": "synthetic provider-side failure",
        }
    )
    event = contact_to_mission_event(contact, sequence=7, t_seconds=42.5)
    assert event.sequence == 7
    assert event.event_type == "spacelink_contact_state"
    assert event.payload["status"] == "AWS_FAILED"
    assert event.payload["disposition"] == "FAILED"
    assert event.payload["contact_id"] == contact.contact_id


def test_reservation_proposal_rejects_naive_or_reversed_times():
    with pytest.raises(ValueError):
        ContactReservationProposal(
            proposal_id="WS-SL-NAIVE",
            start_time=datetime(2026, 9, 30, 16, 0),
            end_time=datetime(2026, 9, 30, 16, 10),
            ground_station="Digital Twin Test",
            mission_profile_ref="mission-profile",
            satellite_ref="satellite",
            requested_by="tester",
            purpose="negative test",
        )

    with pytest.raises(ValueError):
        ContactReservationProposal(
            proposal_id="WS-SL-REVERSED",
            start_time=datetime(2026, 9, 30, 16, 10, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 30, 16, 0, tzinfo=timezone.utc),
            ground_station="Digital Twin Test",
            mission_profile_ref="mission-profile",
            satellite_ref="satellite",
            requested_by="tester",
            purpose="negative test",
        )
