from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Iterable


class Verdict(str, Enum):
    VERIFIED = "VERIFIED"
    VERIFIED_WITH_EXCEPTIONS = "VERIFIED_WITH_EXCEPTIONS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NONCOMPLIANT = "NONCOMPLIANT"


@dataclass(frozen=True)
class FlexRequest:
    requested_reduction_mw: float
    response_deadline_s: float
    required_duration_s: float
    max_grid_import_mw: float


@dataclass(frozen=True)
class FlexObservation:
    baseline_mw: float
    grid_import_mw: float
    duration_s: float
    response_latency_s: float
    workload_pause_mw: float = 0.0
    workload_migration_mw: float = 0.0
    battery_discharge_mw: float = 0.0
    onsite_generation_mw: float = 0.0
    hvac_reduction_mw: float = 0.0
    rebound_energy_mwh: float = 0.0
    evidence_complete: bool = True
    telemetry_fresh: bool = True
    authorized: bool = True
    clocks_synchronized: bool = True
    baseline_valid: bool = True
    meter_provenance_valid: bool = True
    configuration_custody_valid: bool = True
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def measured_reduction_mw(self) -> float:
        return self.baseline_mw - self.grid_import_mw

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
class VerificationResult:
    verdict: Verdict
    reasons: tuple[str, ...]
    measured_reduction_mw: float
    decomposed_reduction_mw: float
    source_mismatch_mw: float
    rebound_energy_mwh: float


def _finite_nonnegative(values: Iterable[float]) -> bool:
    return all(isfinite(v) and v >= 0 for v in values)


def verify_event(
    request: FlexRequest,
    obs: FlexObservation,
    *,
    decomposition_tolerance_mw: float = 0.5,
    rebound_exception_mwh: float = 0.25,
) -> VerificationResult:
    """Adversarial verifier for a synthetic data-center flexibility event.

    Separates grid-boundary compliance, evidence sufficiency, mechanism
    decomposition, and rebound. This is a reference model only; field claims
    require partner validation.
    """

    numeric = [
        request.requested_reduction_mw,
        request.response_deadline_s,
        request.required_duration_s,
        request.max_grid_import_mw,
        obs.baseline_mw,
        obs.grid_import_mw,
        obs.duration_s,
        obs.response_latency_s,
        obs.workload_pause_mw,
        obs.workload_migration_mw,
        obs.battery_discharge_mw,
        obs.onsite_generation_mw,
        obs.hvac_reduction_mw,
        obs.rebound_energy_mwh,
        decomposition_tolerance_mw,
        rebound_exception_mwh,
    ]
    if not _finite_nonnegative(numeric):
        return VerificationResult(
            Verdict.INSUFFICIENT_EVIDENCE,
            ("invalid_or_negative_numeric_input",),
            obs.measured_reduction_mw,
            obs.decomposed_reduction_mw,
            abs(obs.measured_reduction_mw - obs.decomposed_reduction_mw),
            obs.rebound_energy_mwh,
        )

    evidence_failures = []
    if not obs.evidence_complete:
        evidence_failures.append("evidence_incomplete")
    if not obs.telemetry_fresh:
        evidence_failures.append("stale_telemetry")
    if not obs.clocks_synchronized:
        evidence_failures.append("clock_sync_failed")
    if not obs.baseline_valid:
        evidence_failures.append("baseline_invalid")
    if not obs.meter_provenance_valid:
        evidence_failures.append("meter_provenance_invalid")
    if not obs.configuration_custody_valid:
        evidence_failures.append("configuration_custody_invalid")

    if evidence_failures:
        return VerificationResult(
            Verdict.INSUFFICIENT_EVIDENCE,
            tuple(evidence_failures),
            obs.measured_reduction_mw,
            obs.decomposed_reduction_mw,
            abs(obs.measured_reduction_mw - obs.decomposed_reduction_mw),
            obs.rebound_energy_mwh,
        )

    if not obs.authorized:
        return VerificationResult(
            Verdict.NONCOMPLIANT,
            ("unauthorized_control_action",),
            obs.measured_reduction_mw,
            obs.decomposed_reduction_mw,
            abs(obs.measured_reduction_mw - obs.decomposed_reduction_mw),
            obs.rebound_energy_mwh,
        )

    compliance_failures = []
    if obs.grid_import_mw > request.max_grid_import_mw:
        compliance_failures.append("grid_import_limit_exceeded")
    if obs.measured_reduction_mw < request.requested_reduction_mw:
        compliance_failures.append("requested_reduction_not_met")
    if obs.response_latency_s > request.response_deadline_s:
        compliance_failures.append("response_deadline_missed")
    if obs.duration_s < request.required_duration_s:
        compliance_failures.append("minimum_duration_not_met")

    if compliance_failures:
        return VerificationResult(
            Verdict.NONCOMPLIANT,
            tuple(compliance_failures),
            obs.measured_reduction_mw,
            obs.decomposed_reduction_mw,
            abs(obs.measured_reduction_mw - obs.decomposed_reduction_mw),
            obs.rebound_energy_mwh,
        )

    mismatch = abs(obs.measured_reduction_mw - obs.decomposed_reduction_mw)
    exceptions = []
    if mismatch > decomposition_tolerance_mw:
        exceptions.append("mechanism_decomposition_mismatch")
    if obs.rebound_energy_mwh > rebound_exception_mwh:
        exceptions.append("material_rebound_energy")
    if obs.onsite_generation_mw > 0:
        exceptions.append("onsite_generation_substitution")

    verdict = Verdict.VERIFIED_WITH_EXCEPTIONS if exceptions else Verdict.VERIFIED
    return VerificationResult(
        verdict,
        tuple(exceptions),
        obs.measured_reduction_mw,
        obs.decomposed_reduction_mw,
        mismatch,
        obs.rebound_energy_mwh,
    )


def default_scenario() -> tuple[FlexRequest, FlexObservation]:
    request = FlexRequest(
        requested_reduction_mw=20.0,
        response_deadline_s=300.0,
        required_duration_s=1800.0,
        max_grid_import_mw=80.0,
    )
    obs = FlexObservation(
        baseline_mw=100.0,
        grid_import_mw=80.0,
        duration_s=1800.0,
        response_latency_s=180.0,
        workload_pause_mw=8.0,
        workload_migration_mw=4.0,
        battery_discharge_mw=5.0,
        hvac_reduction_mw=3.0,
    )
    return request, obs
