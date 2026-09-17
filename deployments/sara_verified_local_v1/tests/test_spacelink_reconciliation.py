from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worldshepherd_sara.spacelink_eventbridge import (
    AwsGroundStationEventBridgeAdapter,
    apply_contact_event,
)
from worldshepherd_sara.spacelink_reconciliation import (
    AwsGroundStationReadReconciler,
    ReconciliationState,
    reconciliation_to_mission_event,
)


def _event(status: str = "PASS", event_time: str = "2026-09-12T18:00:00Z") -> dict:
    return {
        "version": "0",
        "id": f"event-{status.lower()}",
        "account": "123456789012",
        "time": event_time,
        "region": "us-west-2",
        "source": "aws.groundstation",
        "resources": [],
        "detail-type": "Ground Station Contact State Change",
        "detail": {
            "contactId": "11111111-1111-1111-1111-111111111111",
            "groundstationId": "Digital Twin Hawaii 1",
            "missionProfileArn": "mission-profile",
            "satelliteArn": "satellite",
            "contactStatus": status,
        },
    }


def _provider(status: str = "PASS", last_updated: str = "2026-09-12T18:00:05Z") -> dict:
    return {
        "contactId": "11111111-1111-1111-1111-111111111111",
        "contactStatus": status,
        "groundStation": "Digital Twin Hawaii 1",
        "lastUpdated": last_updated,
    }


def _projection(status: str = "PASS", event_time: str = "2026-09-12T18:00:00Z"):
    event = AwsGroundStationEventBridgeAdapter().normalize_event(_event(status, event_time))
    return apply_contact_event(None, event)


def test_matching_provider_read_requires_no_attention():
    record = AwsGroundStationReadReconciler().reconcile(
        reconciliation_id="REC-001",
        projection=_projection(),
        provider_payload=_provider(),
        observed_at=datetime(2026, 9, 12, 18, 0, 10, tzinfo=timezone.utc),
    )
    assert record.state == ReconciliationState.MATCH
    assert record.requires_attention() is False
    assert record.automatic_mutation_allowed is False


def test_missing_projection_is_visible_and_read_only():
    record = AwsGroundStationReadReconciler().reconcile(
        reconciliation_id="REC-002",
        projection=None,
        provider_payload=_provider(status="SCHEDULED"),
        observed_at=datetime(2026, 9, 12, 18, 0, 10, tzinfo=timezone.utc),
    )
    assert record.state == ReconciliationState.PROJECTION_MISSING
    assert record.requires_attention() is True
    assert record.automatic_mutation_allowed is False


def test_stale_provider_read_cannot_overwrite_newer_event_projection():
    record = AwsGroundStationReadReconciler().reconcile(
        reconciliation_id="REC-003",
        projection=_projection(status="PASS", event_time="2026-09-12T18:05:00Z"),
        provider_payload=_provider(status="PREPASS", last_updated="2026-09-12T18:04:59Z"),
        observed_at=datetime(2026, 9, 12, 18, 5, 10, tzinfo=timezone.utc),
    )
    assert record.state == ReconciliationState.STALE_PROVIDER_READ
    assert record.automatic_mutation_allowed is False


def test_nonterminal_status_divergence_is_flagged_for_reconciliation():
    record = AwsGroundStationReadReconciler().reconcile(
        reconciliation_id="REC-004",
        projection=_projection(status="PREPASS"),
        provider_payload=_provider(status="PASS"),
        observed_at=datetime(2026, 9, 12, 18, 0, 10, tzinfo=timezone.utc),
    )
    assert record.state == ReconciliationState.STATUS_DIVERGENCE
    assert "best-effort" in record.rationale[0]


def test_different_terminal_states_are_never_silently_reconciled():
    record = AwsGroundStationReadReconciler().reconcile(
        reconciliation_id="REC-005",
        projection=_projection(status="COMPLETED"),
        provider_payload=_provider(status="AWS_FAILED"),
        observed_at=datetime(2026, 9, 12, 18, 0, 10, tzinfo=timezone.utc),
    )
    assert record.state == ReconciliationState.TERMINAL_CONFLICT
    assert record.automatic_mutation_allowed is False


def test_contact_identity_mismatch_fails_closed():
    provider = _provider()
    provider["contactId"] = "22222222-2222-2222-2222-222222222222"
    with pytest.raises(ValueError, match="different contacts"):
        AwsGroundStationReadReconciler().reconcile(
            reconciliation_id="REC-006",
            projection=_projection(),
            provider_payload=provider,
            observed_at=datetime(2026, 9, 12, 18, 0, 10, tzinfo=timezone.utc),
        )


def test_unknown_provider_status_fails_through_authoritative_adapter():
    provider = _provider(status="IMPOSSIBLE")
    with pytest.raises(ValueError, match="unrecognized space-contact status"):
        AwsGroundStationReadReconciler().reconcile(
            reconciliation_id="REC-007",
            projection=_projection(),
            provider_payload=provider,
            observed_at=datetime(2026, 9, 12, 18, 0, 10, tzinfo=timezone.utc),
        )


def test_reconciliation_converts_to_replayable_mission_evidence():
    record = AwsGroundStationReadReconciler().reconcile(
        reconciliation_id="REC-008",
        projection=_projection(status="PREPASS"),
        provider_payload=_provider(status="PASS"),
        observed_at=datetime(2026, 9, 12, 18, 0, 10, tzinfo=timezone.utc),
    )
    event = reconciliation_to_mission_event(record, sequence=12, t_seconds=20.0)
    assert event.event_type == "spacelink_provider_reconciliation"
    assert event.payload["state"] == "STATUS_DIVERGENCE"
    assert event.payload["requires_attention"] is True
    assert event.payload["automatic_mutation_allowed"] is False
