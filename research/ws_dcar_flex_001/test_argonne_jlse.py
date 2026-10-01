import pytest

from argonne_jlse import (
    ArgonneControlAction,
    ArgonneQosSummary,
    ArgonneSweepContext,
    build_argonne_jlse_payload,
)
from model import FlexRequest, Verdict
from partner_bundle import MeasurementBoundary, PartnerEvidenceContext
from replay import replay_payload
from trace import TracePoint


def request() -> FlexRequest:
    return FlexRequest(
        requested_reduction_mw=0.02,
        response_deadline_s=60.0,
        required_duration_s=120.0,
        max_grid_import_mw=0.08,
    )


def points() -> list[TracePoint]:
    return [
        TracePoint(
            timestamp_s=0.0,
            grid_import_mw=0.10,
            configuration_id="anl-cfg-001",
            meter_id="anl-node-power-001",
        ),
        TracePoint(
            timestamp_s=30.0,
            grid_import_mw=0.08,
            workload_pause_mw=0.02,
            configuration_id="anl-cfg-001",
            meter_id="anl-node-power-001",
        ),
        TracePoint(
            timestamp_s=90.0,
            grid_import_mw=0.08,
            workload_pause_mw=0.02,
            configuration_id="anl-cfg-001",
            meter_id="anl-node-power-001",
        ),
        TracePoint(
            timestamp_s=150.0,
            grid_import_mw=0.08,
            workload_pause_mw=0.02,
            configuration_id="anl-cfg-001",
            meter_id="anl-node-power-001",
        ),
    ]


def partner_context(**overrides) -> PartnerEvidenceContext:
    values = dict(
        source_organization="Argonne National Laboratory",
        project_or_dataset_id="jlse-data-center-flexibility/anl-001-segment-001",
        measurement_boundary=MeasurementBoundary.NODE,
        request_id="anl-req-001",
        authorization_record_id="anl-auth-001",
        clock_source="declared-synchronized-lab-clock",
        baseline_method="pre-action node-power mean",
        configuration_id="anl-cfg-001",
        meter_id="anl-node-power-001",
        transformation_history=("watts_to_megawatts: divide by 1e6",),
        limitations=("node-level evidence; no facility/grid-boundary claim",),
    )
    values.update(overrides)
    return PartnerEvidenceContext(**values)


def control(**overrides) -> ArgonneControlAction:
    values = dict(
        action_id="anl-control-001",
        variable="gpu_power_cap",
        before_value=700.0,
        after_value=500.0,
        unit="W",
    )
    values.update(overrides)
    return ArgonneControlAction(**values)


def qos() -> ArgonneQosSummary:
    return ArgonneQosSummary(
        time_to_first_token_ms=110.0,
        latency_ms=900.0,
        tokens_per_second=145.0,
        request_count=256,
        aggregation_method="mean over bounded sweep segment",
    )


def sweep() -> ArgonneSweepContext:
    return ArgonneSweepContext(
        gpu_model="NVIDIA H100",
        power_channels=("gpu_power_w", "cpu_power_w", "dram_power_w"),
        qos_channels=("ttft_ms", "latency_ms", "tokens_per_second"),
        source_object_id="anl-object-001",
        source_sha256="0" * 64,
        raw_or_derived="raw",
    )


def test_argonne_node_bundle_preserves_boundary_and_qos():
    payload = build_argonne_jlse_payload(
        request(), 0.10, points(), partner_context(), control(), qos(), sweep()
    )
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.VERIFIED.value
    assert result["provenance"]["claim_scope"] == "node_only"
    assert result["provenance"]["anl_001_control_variable"] == "gpu_power_cap"
    assert result["auxiliary_evidence"]["anl_001"]["qos_summary"]["request_count"] == 256


def test_argonne_adapter_rejects_facility_claim_promotion():
    with pytest.raises(ValueError, match="device/node/cluster"):
        build_argonne_jlse_payload(
            request(),
            0.10,
            points(),
            partner_context(measurement_boundary=MeasurementBoundary.FACILITY),
            control(),
            qos(),
            sweep(),
        )


def test_argonne_adapter_rejects_unpublished_control_variable():
    with pytest.raises(ValueError, match="unsupported JLSE control variable"):
        build_argonne_jlse_payload(
            request(),
            0.10,
            points(),
            partner_context(),
            control(variable="cooling_setpoint"),
            qos(),
            sweep(),
        )


def test_argonne_source_identity_remains_fail_closed():
    payload = build_argonne_jlse_payload(
        request(),
        0.10,
        points(),
        partner_context(project_or_dataset_id=""),
        control(),
        qos(),
        sweep(),
    )
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "source_identity_invalid" in result["reasons"]
