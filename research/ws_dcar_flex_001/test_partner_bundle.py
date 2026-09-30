from model import FlexRequest, Verdict
from partner_bundle import (
    MeasurementBoundary,
    PartnerEvidenceContext,
    build_partner_replay_payload,
)
from replay import replay_payload
from trace import TracePoint


def request() -> FlexRequest:
    return FlexRequest(
        requested_reduction_mw=20.0,
        response_deadline_s=300.0,
        required_duration_s=600.0,
        max_grid_import_mw=80.0,
    )


def points(*, meter_valid: bool = True) -> list[TracePoint]:
    return [
        TracePoint(
            timestamp_s=0.0,
            grid_import_mw=100.0,
            meter_provenance_valid=meter_valid,
            configuration_id="cfg-partner-001",
            meter_id="meter-partner-001",
        ),
        TracePoint(
            timestamp_s=120.0,
            grid_import_mw=80.0,
            workload_pause_mw=20.0,
            meter_provenance_valid=meter_valid,
            configuration_id="cfg-partner-001",
            meter_id="meter-partner-001",
        ),
        TracePoint(
            timestamp_s=720.0,
            grid_import_mw=80.0,
            workload_pause_mw=20.0,
            meter_provenance_valid=meter_valid,
            configuration_id="cfg-partner-001",
            meter_id="meter-partner-001",
        ),
    ]


def context(**overrides) -> PartnerEvidenceContext:
    values = dict(
        source_organization="Partner Lab",
        project_or_dataset_id="event-001",
        measurement_boundary=MeasurementBoundary.CLUSTER,
        request_id="request-001",
        authorization_record_id="auth-001",
        clock_source="ptp-domain-001",
        baseline_method="pre-event mean, 10 min",
        configuration_id="cfg-partner-001",
        meter_id="meter-partner-001",
        transformation_history=("none",),
    )
    values.update(overrides)
    return PartnerEvidenceContext(**values)


def test_complete_cluster_bundle_verifies_only_at_cluster_scope():
    payload = build_partner_replay_payload(request(), 100.0, points(), context())
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.VERIFIED.value
    assert result["provenance"]["claim_scope"] == "cluster_only"
    assert result["provenance"]["measurement_boundary"] == "cluster"


def test_missing_request_identifier_fails_closed():
    payload = build_partner_replay_payload(
        request(), 100.0, points(), context(request_id=None)
    )
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "request_provenance_invalid" in result["reasons"]


def test_missing_authorization_record_fails_closed():
    payload = build_partner_replay_payload(
        request(), 100.0, points(), context(authorization_record_id=None)
    )
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "authorization_evidence_invalid" in result["reasons"]


def test_missing_clock_source_fails_closed():
    payload = build_partner_replay_payload(
        request(), 100.0, points(), context(clock_source=None)
    )
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "clock_sync_failed" in result["reasons"]


def test_missing_baseline_method_fails_closed():
    payload = build_partner_replay_payload(
        request(), 100.0, points(), context(baseline_method=None)
    )
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "baseline_invalid" in result["reasons"]


def test_missing_configuration_identifier_fails_closed():
    payload = build_partner_replay_payload(
        request(), 100.0, points(), context(configuration_id=None)
    )
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "configuration_custody_invalid" in result["reasons"]


def test_grid_boundary_label_does_not_override_bad_meter_provenance():
    grid_context = context(measurement_boundary=MeasurementBoundary.GRID_BOUNDARY)
    payload = build_partner_replay_payload(
        request(), 100.0, points(meter_valid=False), grid_context
    )
    result = replay_payload(payload)
    assert result["provenance"]["claim_scope"] == "grid_boundary"
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "meter_provenance_invalid" in result["reasons"]


def test_known_unauthorized_action_is_noncompliant_when_evidence_is_complete():
    payload = build_partner_replay_payload(
        request(), 100.0, points(), context(authorized=False)
    )
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.NONCOMPLIANT.value
    assert result["reasons"] == ["unauthorized_control_action"]
