from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.autonomy_policy import (
    AutonomousActionCandidate,
    ExecutionDisposition,
)
from worldshepherd_sara.wmaf import (
    MobilityAsset,
    MobilitySource,
    WmafDisposition,
    WmafEvent,
    assess_event,
)


def _event(**overrides) -> WmafEvent:
    payload = {
        "event_id": "WMAF-EVT-001",
        "observed_utc": "2026-09-04T23:59:00Z",
        "asset": MobilityAsset(asset_id="SIM-VEH-001", asset_type="synthetic_vehicle"),
        "source": MobilitySource(
            vendor="synthetic",
            device="fixture-v1",
            firmware="fixture",
            interface="simulation",
        ),
        "pnt_payload": {
            "source_id": "PNT-001",
            "source_kind": "synthetic_gnss",
            "health": "nominal",
            "confidence": 0.99,
            "observed_utc": "2026-09-04T23:59:00Z",
        },
        "vehicle_state": {
            "telemetry_connected": True,
            "telemetry_age_seconds": 0.1,
        },
        "cyber_state": {"software_version_authorized": True},
    }
    payload.update(overrides)
    return WmafEvent(**payload)


def test_nominal_event_is_observe_only_and_digest_bound():
    assessment = assess_event(_event())

    assert assessment.disposition is WmafDisposition.OBSERVE
    assert assessment.risk_flags == []
    assert assessment.execution_performed is False
    assert assessment.evidence_digest.startswith("sha256:")
    assert len(assessment.evidence_digest) == len("sha256:") + 64


def test_degraded_pnt_is_flagged_without_execution():
    event = _event(
        pnt_payload={
            "source_id": "PNT-002",
            "source_kind": "synthetic_gnss",
            "health": "degraded",
            "confidence": 0.50,
        }
    )
    assessment = assess_event(event)

    assert assessment.disposition is WmafDisposition.FLAG
    assert "PNT_DEGRADED" in assessment.risk_flags
    assert assessment.execution_performed is False


def test_contradictory_vehicle_state_escalates():
    event = _event(
        vehicle_state={
            "telemetry_connected": True,
            "telemetry_age_seconds": 0.1,
            "contradictory_state": True,
        }
    )
    assessment = assess_event(event)

    assert assessment.disposition is WmafDisposition.ESCALATE
    assert "CONTRADICTORY_VEHICLE_STATE" in assessment.risk_flags


def test_unauthorized_software_version_escalates():
    assessment = assess_event(
        _event(cyber_state={"software_version_authorized": False})
    )

    assert assessment.disposition is WmafDisposition.ESCALATE
    assert "UNAUTHORIZED_SOFTWARE_VERSION" in assessment.risk_flags


def test_telemetry_loss_and_staleness_are_flagged():
    lost = assess_event(
        _event(vehicle_state={"telemetry_connected": False})
    )
    stale = assess_event(
        _event(
            event_id="WMAF-EVT-STALE",
            vehicle_state={
                "telemetry_connected": True,
                "telemetry_age_seconds": 6.0,
            },
        )
    )

    assert lost.disposition is WmafDisposition.FLAG
    assert "TELEMETRY_LOSS" in lost.risk_flags
    assert stale.disposition is WmafDisposition.FLAG
    assert "TELEMETRY_STALE" in stale.risk_flags


def test_malformed_or_negative_telemetry_age_fails_closed_to_flag():
    malformed = assess_event(
        _event(
            event_id="WMAF-EVT-BAD-AGE",
            vehicle_state={
                "telemetry_connected": True,
                "telemetry_age_seconds": "not-a-number",
            },
        )
    )
    negative = assess_event(
        _event(
            event_id="WMAF-EVT-NEG-AGE",
            vehicle_state={
                "telemetry_connected": True,
                "telemetry_age_seconds": -1,
            },
        )
    )

    assert malformed.disposition is WmafDisposition.FLAG
    assert "TELEMETRY_AGE_INVALID" in malformed.risk_flags
    assert negative.disposition is WmafDisposition.FLAG
    assert "TELEMETRY_AGE_INVALID" in negative.risk_flags


def test_denied_vehicle_control_action_is_denied_but_never_executed():
    event = _event(
        requested_action=AutonomousActionCandidate(
            action_id="ACT-STEER",
            action_type="steering",
            confidence=1.0,
            requested_authority=0,
            reversible=True,
        )
    )
    assessment = assess_event(event)

    assert assessment.action_disposition is ExecutionDisposition.DENIED
    assert assessment.disposition is WmafDisposition.DENY
    assert assessment.execution_performed is False


def test_non_allowlisted_action_requires_human_review():
    event = _event(
        requested_action=AutonomousActionCandidate(
            action_id="ACT-UNKNOWN",
            action_type="modify_route_plan",
            confidence=1.0,
            requested_authority=0,
            reversible=True,
        )
    )
    assessment = assess_event(event)

    assert assessment.action_disposition is ExecutionDisposition.HUMAN_REVIEW_REQUIRED
    assert assessment.disposition is WmafDisposition.ESCALATE
    assert assessment.execution_performed is False


def test_allowlisted_record_action_can_be_policy_eligible_but_is_not_executed():
    event = _event(
        requested_action=AutonomousActionCandidate(
            action_id="ACT-RECORD",
            action_type="record_evidence",
            confidence=1.0,
            requested_authority=0,
            reversible=True,
        )
    )
    assessment = assess_event(event)

    assert assessment.action_disposition is ExecutionDisposition.AUTO_ELIGIBLE
    assert assessment.disposition is WmafDisposition.OBSERVE
    assert assessment.execution_performed is False
    assert any("must not be interpreted as execution authority" in item for item in assessment.claims_boundary)


def test_schema_identifier_cannot_be_overridden():
    with pytest.raises(ValidationError):
        _event(schema_id="WS-WMAF-EVENT-V9")


def test_claims_boundary_explicitly_excludes_vendor_and_field_validation():
    assessment = assess_event(_event())
    boundary = "\n".join(assessment.claims_boundary).lower()

    assert "no nxp" in boundary
    assert "no physical or field validation" in boundary
    assert "no steering" in boundary
    assert "operational validation remain required" in boundary
