from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Sequence

from model import FlexRequest, Verdict


@dataclass(frozen=True)
class TracePoint:
    timestamp_s: float
    grid_import_mw: float
    workload_pause_mw: float = 0.0
    workload_migration_mw: float = 0.0
    battery_discharge_mw: float = 0.0
    onsite_generation_mw: float = 0.0
    hvac_reduction_mw: float = 0.0
    telemetry_fresh: bool = True
    meter_provenance_valid: bool = True
    configuration_id: str = "cfg-001"
    meter_id: str = "grid-meter-001"

    @property
    def decomposed_reduction_mw(self) -> float:
        return (
            self.workload_pause_mw
            + self.workload_migration_mw
            + self.battery_discharge_mw
            + self.onsite_generation_mw
            + self.hvac_reduction_mw
        )


@dataclass(frozen=True)
class TraceVerificationResult:
    verdict: Verdict
    reasons: tuple[str, ...]
    response_latency_s: float | None
    maintained_duration_s: float
    event_grid_energy_reduction_mwh: float
    decomposed_energy_reduction_mwh: float
    source_mismatch_mwh: float
    min_grid_import_mw: float | None
    sample_count: int


def _finite_nonnegative(values: Iterable[float]) -> bool:
    return all(isfinite(value) and value >= 0 for value in values)


def _integrate(points: Sequence[TracePoint], values: Sequence[float]) -> float:
    total_mw_s = 0.0
    for left, right, left_value, right_value in zip(
        points, points[1:], values, values[1:]
    ):
        dt = right.timestamp_s - left.timestamp_s
        total_mw_s += 0.5 * (left_value + right_value) * dt
    return total_mw_s / 3600.0


def verify_trace(
    request: FlexRequest,
    baseline_mw: float,
    points: Sequence[TracePoint],
    *,
    authorized: bool = True,
    source_identity_valid: bool = True,
    authorization_evidence_valid: bool = True,
    request_provenance_valid: bool = True,
    baseline_valid: bool = True,
    clocks_synchronized: bool = True,
    configuration_custody_valid: bool = True,
    max_gap_s: float = 300.0,
    energy_mismatch_tolerance_mwh: float = 0.25,
) -> TraceVerificationResult:
    """Verify a time-series flexibility event without hiding evidence defects.

    The trace gate separates evidence sufficiency, authorization, contract
    compliance, and mechanism decomposition. It is reference software only;
    utility-grade field claims require partner validation.

    `authorized=False` means the action is known to be unauthorized and is a
    compliance failure. `authorization_evidence_valid=False` means the evidence
    is insufficient to determine authorization and therefore cannot be treated
    as a pass or as a known unauthorized action.
    """

    pts = tuple(points)

    def build_result(
        verdict: Verdict,
        reasons: tuple[str, ...],
        response_latency_s: float | None = None,
        maintained_duration_s: float = 0.0,
    ) -> TraceVerificationResult:
        if len(pts) >= 2 and all(
            isfinite(point.timestamp_s) and isfinite(point.grid_import_mw)
            for point in pts
        ):
            measured = [max(0.0, baseline_mw - point.grid_import_mw) for point in pts]
            decomposed = [point.decomposed_reduction_mw for point in pts]
            grid_energy = _integrate(pts, measured)
            decomposed_energy = _integrate(pts, decomposed)
            mismatch = abs(grid_energy - decomposed_energy)
            minimum = min(point.grid_import_mw for point in pts)
        else:
            grid_energy = 0.0
            decomposed_energy = 0.0
            mismatch = 0.0
            minimum = None
        return TraceVerificationResult(
            verdict=verdict,
            reasons=reasons,
            response_latency_s=response_latency_s,
            maintained_duration_s=maintained_duration_s,
            event_grid_energy_reduction_mwh=grid_energy,
            decomposed_energy_reduction_mwh=decomposed_energy,
            source_mismatch_mwh=mismatch,
            min_grid_import_mw=minimum,
            sample_count=len(pts),
        )

    if len(pts) < 2:
        return build_result(
            Verdict.INSUFFICIENT_EVIDENCE,
            ("insufficient_trace_samples",),
        )

    numeric = [
        baseline_mw,
        request.requested_reduction_mw,
        request.response_deadline_s,
        request.required_duration_s,
        request.max_grid_import_mw,
        max_gap_s,
        energy_mismatch_tolerance_mwh,
    ]
    for point in pts:
        numeric.extend(
            [
                point.timestamp_s,
                point.grid_import_mw,
                point.workload_pause_mw,
                point.workload_migration_mw,
                point.battery_discharge_mw,
                point.onsite_generation_mw,
                point.hvac_reduction_mw,
            ]
        )
    if not _finite_nonnegative(numeric):
        return build_result(
            Verdict.INSUFFICIENT_EVIDENCE,
            ("invalid_or_negative_numeric_input",),
        )

    timestamps = [point.timestamp_s for point in pts]
    evidence_failures: list[str] = []
    if not source_identity_valid:
        evidence_failures.append("source_identity_invalid")
    if not request_provenance_valid:
        evidence_failures.append("request_provenance_invalid")
    if not authorization_evidence_valid:
        evidence_failures.append("authorization_evidence_invalid")
    if not configuration_custody_valid:
        evidence_failures.append("configuration_custody_invalid")
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        evidence_failures.append("timestamps_not_strictly_increasing")
    if any(
        (right - left) > max_gap_s
        for left, right in zip(timestamps, timestamps[1:])
    ):
        evidence_failures.append("telemetry_gap_exceeded")
    if not clocks_synchronized:
        evidence_failures.append("clock_sync_failed")
    if not baseline_valid:
        evidence_failures.append("baseline_invalid")
    if any(not point.telemetry_fresh for point in pts):
        evidence_failures.append("stale_telemetry")
    if any(not point.meter_provenance_valid for point in pts):
        evidence_failures.append("meter_provenance_invalid")
    if len({point.configuration_id for point in pts}) != 1:
        evidence_failures.append("configuration_drift_detected")
    if len({point.meter_id for point in pts}) != 1:
        evidence_failures.append("meter_identity_changed")
    if evidence_failures:
        return build_result(
            Verdict.INSUFFICIENT_EVIDENCE,
            tuple(evidence_failures),
        )

    if not authorized:
        return build_result(
            Verdict.NONCOMPLIANT,
            ("unauthorized_control_action",),
        )

    def instant_compliant(point: TracePoint) -> bool:
        measured_reduction_mw = baseline_mw - point.grid_import_mw
        return (
            point.grid_import_mw <= request.max_grid_import_mw
            and measured_reduction_mw >= request.requested_reduction_mw
        )

    response_index = next(
        (index for index, point in enumerate(pts) if instant_compliant(point)),
        None,
    )
    if response_index is None:
        return build_result(
            Verdict.NONCOMPLIANT,
            ("requested_reduction_not_reached", "grid_import_limit_not_reached"),
        )

    response_latency_s = pts[response_index].timestamp_s
    end_index = response_index
    for index in range(response_index + 1, len(pts)):
        if not instant_compliant(pts[index]):
            break
        end_index = index
    maintained_duration_s = pts[end_index].timestamp_s - pts[response_index].timestamp_s

    compliance_failures: list[str] = []
    if response_latency_s > request.response_deadline_s:
        compliance_failures.append("response_deadline_missed")
    if maintained_duration_s < request.required_duration_s:
        compliance_failures.append("minimum_duration_not_met")
    if compliance_failures:
        return build_result(
            Verdict.NONCOMPLIANT,
            tuple(compliance_failures),
            response_latency_s,
            maintained_duration_s,
        )

    measured = [max(0.0, baseline_mw - point.grid_import_mw) for point in pts]
    decomposed = [point.decomposed_reduction_mw for point in pts]
    mismatch = abs(_integrate(pts, measured) - _integrate(pts, decomposed))

    exceptions: list[str] = []
    if mismatch > energy_mismatch_tolerance_mwh:
        exceptions.append("energy_decomposition_mismatch")
    if any(point.onsite_generation_mw > 0 for point in pts):
        exceptions.append("onsite_generation_substitution")

    verdict = Verdict.VERIFIED_WITH_EXCEPTIONS if exceptions else Verdict.VERIFIED
    return build_result(
        verdict,
        tuple(exceptions),
        response_latency_s,
        maintained_duration_s,
    )
