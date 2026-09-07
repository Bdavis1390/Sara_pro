from __future__ import annotations

import cmath
import hashlib
import math
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .programmable_boundary_benchmark import (
    _apply_thermal_drift,
    _at_angle,
    _coherent_weights,
    _normalize_design_power,
    _power_proxy,
    run_programmable_boundary_benchmark,
)
from .qualification import CapabilityStatus, canonical_digest


class RobustnessOutcome(str, Enum):
    ROBUSTNESS_SUPPORTED_WITHIN_SURROGATE = "ROBUSTNESS_SUPPORTED_WITHIN_SURROGATE"
    NO_ROBUSTNESS_PROMOTION = "NO_ROBUSTNESS_PROMOTION"
    INCONCLUSIVE = "INCONCLUSIVE"


class NominalRobustnessCase(BaseModel):
    case_id: str
    tile_count: int = Field(ge=4)
    tile_spacing_wavelengths: float = Field(gt=0.0, le=0.5)
    target_angle_degrees: float
    preserve_angle_degrees: float
    passive_reference_field: float = Field(ge=0.0)
    coherent_gain_over_passive: float = Field(ge=0.0)
    null_suppression_ratio_vs_passive: float = Field(ge=0.0)
    null_preserve_fraction: float = Field(ge=0.0)
    thermal_target_retention_fraction: float = Field(ge=0.0)
    equal_power_design_controls: bool
    embedded_benchmark_behavior_observed: bool
    ratio_degenerate_reference: bool
    case_passed: bool
    failure_reasons: tuple[str, ...]


class PerturbationRobustnessCase(BaseModel):
    case_id: str
    seed: int
    phase_error_limit_degrees: float = Field(ge=0.0)
    amplitude_error_fraction: float = Field(ge=0.0, lt=1.0)
    target_retention_fraction: float = Field(ge=0.0)
    total_element_power_proxy: float = Field(gt=0.0)
    equal_power_after_normalization: bool


class ThermalSeverityCase(BaseModel):
    severity: float = Field(gt=0.0)
    target_retention_fraction: float = Field(ge=0.0)
    total_element_power_proxy: float = Field(gt=0.0)


class RobustnessGate(BaseModel):
    minimum_nominal_pass_fraction: float = 0.90
    maximum_ratio_degenerate_fraction: float = 0.05
    minimum_perturbation_retention_fraction: float = 0.90
    require_monotonic_thermal_degradation: bool = True


class RobustnessSummary(BaseModel):
    nominal_case_count: int = Field(gt=0)
    nominal_pass_count: int = Field(ge=0)
    nominal_pass_fraction: float = Field(ge=0.0, le=1.0)
    ratio_degenerate_count: int = Field(ge=0)
    ratio_degenerate_fraction: float = Field(ge=0.0, le=1.0)
    perturbation_case_count: int = Field(gt=0)
    perturbation_minimum_retention_fraction: float = Field(ge=0.0)
    thermal_case_count: int = Field(gt=0)
    thermal_retention_monotonic_nonincreasing: bool
    failed_gate_conditions: tuple[str, ...]
    outcome: RobustnessOutcome


class ProgrammableBoundaryRobustnessReport(BaseModel):
    qualification_id: str = "WS-QE-2026-EMB-002"
    robustness_version: str = "0.1"
    nominal_cases: tuple[NominalRobustnessCase, ...]
    perturbation_cases: tuple[PerturbationRobustnessCase, ...]
    thermal_cases: tuple[ThermalSeverityCase, ...]
    gate: RobustnessGate
    summary: RobustnessSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    laboratory_validation_performed: bool = False
    full_wave_validation_performed: bool = False
    measured_material_properties_used: bool = False
    broadband_validation_performed: bool = False
    stealth_or_cloaking_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "This robustness gate reuses the EMB-001 synthetic scalar array-factor surrogate only.",
        "Sweep success or failure does not establish Maxwell/full-wave, measured-material, scattering, broadband, stealth, cloaking, flight, or operational performance.",
        "Ratio-degenerate passive references are recorded as failures rather than converted into evidence of improvement.",
        "NO_ROBUSTNESS_PROMOTION is a valid scientific outcome and must not be relaxed by changing thresholds after observation.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "ProgrammableBoundaryRobustnessReport":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("EMB-002 must remain SIMULATED_ONLY")
        prohibited = (
            self.laboratory_validation_performed,
            self.full_wave_validation_performed,
            self.measured_material_properties_used,
            self.broadband_validation_performed,
            self.stealth_or_cloaking_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("EMB-002 cannot promote physical/full-wave/operational claims")
        return self


def _unit_interval(seed: int, tile_index: int, channel: str) -> float:
    payload = f"{seed}:{tile_index}:{channel}".encode("utf-8")
    raw = hashlib.sha256(payload).digest()
    return int.from_bytes(raw[:8], "big") / float((1 << 64) - 1)


def _perturb_equal_power(
    weights: tuple[complex, ...],
    *,
    seed: int,
    phase_error_limit_degrees: float,
    amplitude_error_fraction: float,
) -> tuple[complex, ...]:
    perturbed: list[complex] = []
    phase_limit = math.radians(phase_error_limit_degrees)
    for index, weight in enumerate(weights):
        phase_error = (2.0 * _unit_interval(seed, index, "phase") - 1.0) * phase_limit
        amplitude_error = (
            (2.0 * _unit_interval(seed, index, "amplitude") - 1.0)
            * amplitude_error_fraction
        )
        perturbed.append(weight * (1.0 + amplitude_error) * cmath.exp(1j * phase_error))
    return _normalize_design_power(tuple(perturbed), len(weights))


def _nominal_cases() -> tuple[NominalRobustnessCase, ...]:
    geometry_pairs = (
        (-30.0, 20.0),
        (-10.0, 30.0),
        (20.0, -20.0),
        (40.0, -10.0),
    )
    cases: list[NominalRobustnessCase] = []
    for tile_count in (6, 8, 12):
        for spacing in (0.25, 0.35, 0.50):
            for target_angle, preserve_angle in geometry_pairs:
                benchmark = run_programmable_boundary_benchmark(
                    tile_count=tile_count,
                    tile_spacing_wavelengths=spacing,
                    coherent_target_angle_degrees=target_angle,
                    null_angle_degrees=target_angle,
                    preserve_angle_degrees=preserve_angle,
                )
                by_id = {scenario.scenario_id: scenario for scenario in benchmark.scenarios}
                passive_reference = by_id["passive_reference"].target_normalized_field or 0.0
                ratio_degenerate = passive_reference < 1e-6
                summary = benchmark.summary
                reasons: list[str] = []
                if ratio_degenerate:
                    reasons.append("PASSIVE_RATIO_DEGENERATE")
                if not summary.equal_power_design_controls:
                    reasons.append("UNEQUAL_DESIGN_POWER")
                if summary.coherent_gain_over_passive <= 1.5:
                    reasons.append("COHERENT_GAIN_THRESHOLD")
                if summary.null_suppression_ratio_vs_passive >= 1e-6:
                    reasons.append("NULL_SUPPRESSION_THRESHOLD")
                if summary.null_preserve_fraction <= 0.75:
                    reasons.append("PRESERVE_FRACTION_THRESHOLD")
                if summary.thermal_target_retention_fraction >= 0.98:
                    reasons.append("THERMAL_SENSITIVITY_THRESHOLD")
                case_passed = summary.expected_control_behavior_observed and not ratio_degenerate
                cases.append(
                    NominalRobustnessCase(
                        case_id=(
                            f"n{tile_count}-d{spacing:.2f}-t{target_angle:+.0f}"
                            f"-p{preserve_angle:+.0f}"
                        ),
                        tile_count=tile_count,
                        tile_spacing_wavelengths=spacing,
                        target_angle_degrees=target_angle,
                        preserve_angle_degrees=preserve_angle,
                        passive_reference_field=passive_reference,
                        coherent_gain_over_passive=summary.coherent_gain_over_passive,
                        null_suppression_ratio_vs_passive=(
                            summary.null_suppression_ratio_vs_passive
                        ),
                        null_preserve_fraction=summary.null_preserve_fraction,
                        thermal_target_retention_fraction=(
                            summary.thermal_target_retention_fraction
                        ),
                        equal_power_design_controls=summary.equal_power_design_controls,
                        embedded_benchmark_behavior_observed=(
                            summary.expected_control_behavior_observed
                        ),
                        ratio_degenerate_reference=ratio_degenerate,
                        case_passed=case_passed,
                        failure_reasons=tuple(reasons),
                    )
                )
    return tuple(cases)


def _perturbation_cases() -> tuple[PerturbationRobustnessCase, ...]:
    tile_count = 8
    spacing = 0.5
    target_angle = 20.0
    reference = _coherent_weights(
        angle_degrees=target_angle,
        tile_count=tile_count,
        spacing=spacing,
    )
    reference_field = _at_angle(reference, angle=target_angle, spacing=spacing)
    cases: list[PerturbationRobustnessCase] = []
    for seed in (7, 19, 43):
        for phase_limit in (5.0, 15.0, 30.0):
            for amplitude_fraction in (0.05, 0.15):
                perturbed = _perturb_equal_power(
                    reference,
                    seed=seed,
                    phase_error_limit_degrees=phase_limit,
                    amplitude_error_fraction=amplitude_fraction,
                )
                power = _power_proxy(perturbed)
                target_field = _at_angle(perturbed, angle=target_angle, spacing=spacing)
                cases.append(
                    PerturbationRobustnessCase(
                        case_id=(
                            f"seed{seed}-phase{phase_limit:.0f}"
                            f"-amp{amplitude_fraction:.2f}"
                        ),
                        seed=seed,
                        phase_error_limit_degrees=phase_limit,
                        amplitude_error_fraction=amplitude_fraction,
                        target_retention_fraction=(
                            target_field / max(reference_field, 1e-15)
                        ),
                        total_element_power_proxy=power,
                        equal_power_after_normalization=abs(power - tile_count) <= 1e-10,
                    )
                )
    return tuple(cases)


def _thermal_cases() -> tuple[ThermalSeverityCase, ...]:
    tile_count = 8
    spacing = 0.5
    target_angle = 20.0
    reference = _coherent_weights(
        angle_degrees=target_angle,
        tile_count=tile_count,
        spacing=spacing,
    )
    reference_field = _at_angle(reference, angle=target_angle, spacing=spacing)
    cases: list[ThermalSeverityCase] = []
    for severity in (0.25, 0.50, 1.00, 1.50):
        drifted = _apply_thermal_drift(
            reference,
            phase_edge_radians=0.8 * severity,
            edge_amplitude_derating=0.12 * severity,
        )
        cases.append(
            ThermalSeverityCase(
                severity=severity,
                target_retention_fraction=(
                    _at_angle(drifted, angle=target_angle, spacing=spacing)
                    / max(reference_field, 1e-15)
                ),
                total_element_power_proxy=_power_proxy(drifted),
            )
        )
    return tuple(cases)


def run_programmable_boundary_robustness() -> ProgrammableBoundaryRobustnessReport:
    gate = RobustnessGate()
    nominal = _nominal_cases()
    perturbations = _perturbation_cases()
    thermal = _thermal_cases()

    nominal_pass_count = sum(case.case_passed for case in nominal)
    nominal_pass_fraction = nominal_pass_count / len(nominal)
    ratio_degenerate_count = sum(case.ratio_degenerate_reference for case in nominal)
    ratio_degenerate_fraction = ratio_degenerate_count / len(nominal)
    perturbation_minimum_retention = min(
        case.target_retention_fraction for case in perturbations
    )
    thermal_retentions = tuple(case.target_retention_fraction for case in thermal)
    thermal_monotonic = all(
        later <= earlier + 1e-12
        for earlier, later in zip(thermal_retentions, thermal_retentions[1:])
    )

    failed: list[str] = []
    if nominal_pass_fraction < gate.minimum_nominal_pass_fraction:
        failed.append("NOMINAL_PASS_FRACTION")
    if ratio_degenerate_fraction > gate.maximum_ratio_degenerate_fraction:
        failed.append("RATIO_DEGENERATE_FRACTION")
    if perturbation_minimum_retention < gate.minimum_perturbation_retention_fraction:
        failed.append("PERTURBATION_RETENTION")
    if gate.require_monotonic_thermal_degradation and not thermal_monotonic:
        failed.append("THERMAL_MONOTONICITY")
    if not all(case.equal_power_after_normalization for case in perturbations):
        failed.append("PERTURBATION_POWER_NORMALIZATION")

    outcome = (
        RobustnessOutcome.ROBUSTNESS_SUPPORTED_WITHIN_SURROGATE
        if not failed
        else RobustnessOutcome.NO_ROBUSTNESS_PROMOTION
    )
    report = ProgrammableBoundaryRobustnessReport(
        nominal_cases=nominal,
        perturbation_cases=perturbations,
        thermal_cases=thermal,
        gate=gate,
        summary=RobustnessSummary(
            nominal_case_count=len(nominal),
            nominal_pass_count=nominal_pass_count,
            nominal_pass_fraction=nominal_pass_fraction,
            ratio_degenerate_count=ratio_degenerate_count,
            ratio_degenerate_fraction=ratio_degenerate_fraction,
            perturbation_case_count=len(perturbations),
            perturbation_minimum_retention_fraction=perturbation_minimum_retention,
            thermal_case_count=len(thermal),
            thermal_retention_monotonic_nonincreasing=thermal_monotonic,
            failed_gate_conditions=tuple(failed),
            outcome=outcome,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_programmable_boundary_robustness_report(
    report: ProgrammableBoundaryRobustnessReport,
) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
