from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from model import FlexRequest
from partner_bundle import (
    MeasurementBoundary,
    PartnerEvidenceContext,
    build_partner_replay_payload,
)
from trace import TracePoint


ALLOWED_CONTROL_VARIABLES = {
    "gpu_clock_frequency",
    "gpu_power_cap",
    "cpu_power_cap",
    "batch_size",
    "request_concurrency",
}


@dataclass(frozen=True)
class ArgonneControlAction:
    """One bounded control action or sweep segment selected for ANL-001."""

    action_id: str
    variable: str
    before_value: float
    after_value: float
    unit: str


@dataclass(frozen=True)
class ArgonneQosSummary:
    """QoS context carried alongside the power evidence.

    Values may be aggregated for a bounded sweep segment, but the aggregation
    method must be declared so that replay does not silently treat a summary as
    raw per-request evidence.
    """

    time_to_first_token_ms: float
    latency_ms: float
    tokens_per_second: float
    request_count: int
    aggregation_method: str


@dataclass(frozen=True)
class ArgonneSweepContext:
    """Argonne/JLSE-specific metadata that must remain outside claim inflation."""

    gpu_model: str
    power_channels: tuple[str, ...]
    qos_channels: tuple[str, ...]
    source_object_id: str
    source_sha256: str | None = None
    raw_or_derived: str = "raw"


def _nonempty(value: str) -> bool:
    return bool(value.strip())


def build_argonne_jlse_payload(
    request: FlexRequest,
    baseline_mw: float,
    points: Sequence[TracePoint],
    partner_context: PartnerEvidenceContext,
    control: ArgonneControlAction,
    qos: ArgonneQosSummary,
    sweep: ArgonneSweepContext,
    *,
    max_gap_s: float = 300.0,
    energy_mismatch_tolerance_mwh: float = 0.25,
) -> dict:
    """Build an ANL-001 replay payload without promoting node data to grid data.

    The currently published JLSE project scope is device/node oriented. This
    adapter therefore accepts DEVICE, NODE, or CLUSTER evidence only. If a
    future partner bundle contains authoritative PDU/facility/grid evidence,
    the generic partner-bundle path should be used with that explicit boundary.
    """

    if control.variable not in ALLOWED_CONTROL_VARIABLES:
        raise ValueError(f"unsupported JLSE control variable: {control.variable}")
    if partner_context.measurement_boundary not in {
        MeasurementBoundary.DEVICE,
        MeasurementBoundary.NODE,
        MeasurementBoundary.CLUSTER,
    }:
        raise ValueError(
            "ANL-001 adapter is intentionally limited to device/node/cluster evidence"
        )
    if not _nonempty(control.action_id):
        raise ValueError("control action_id is required")
    if not _nonempty(control.unit):
        raise ValueError("control unit is required")
    if not _nonempty(qos.aggregation_method):
        raise ValueError("QoS aggregation method is required")
    if qos.request_count <= 0:
        raise ValueError("QoS request_count must be positive")
    if not _nonempty(sweep.gpu_model):
        raise ValueError("declared GPU model is required")
    if not sweep.power_channels:
        raise ValueError("at least one power channel is required")
    if not sweep.qos_channels:
        raise ValueError("at least one QoS channel is required")
    if not _nonempty(sweep.source_object_id):
        raise ValueError("source object identity is required")
    if sweep.raw_or_derived not in {"raw", "derived"}:
        raise ValueError("raw_or_derived must be 'raw' or 'derived'")

    payload = build_partner_replay_payload(
        request,
        baseline_mw,
        points,
        partner_context,
        max_gap_s=max_gap_s,
        energy_mismatch_tolerance_mwh=energy_mismatch_tolerance_mwh,
    )

    payload["auxiliary_evidence"] = {
        "anl_001": {
            "control_action": asdict(control),
            "qos_summary": asdict(qos),
            "sweep_context": {
                **asdict(sweep),
                "power_channels": list(sweep.power_channels),
                "qos_channels": list(sweep.qos_channels),
            },
            "project_context": {
                "organization": "Argonne National Laboratory",
                "laboratory": "Joint Laboratory for System Evaluation",
                "project": "Data Center Flexibility Dataset",
                "pi": "Wei Gao",
                "published_testbed_context": ["NVIDIA B200", "NVIDIA H100"],
                "evidence_policy": "anl_001_measurement_boundary_preserved",
            },
        }
    }

    provenance = payload.setdefault("provenance", {})
    provenance["anl_001_control_variable"] = control.variable
    provenance["anl_001_control_action_id"] = control.action_id
    provenance["anl_001_gpu_model"] = sweep.gpu_model
    provenance["anl_001_source_object_id"] = sweep.source_object_id
    provenance["anl_001_source_sha256"] = sweep.source_sha256
    provenance["anl_001_raw_or_derived"] = sweep.raw_or_derived
    provenance["anl_001_qos_present"] = True

    return payload
