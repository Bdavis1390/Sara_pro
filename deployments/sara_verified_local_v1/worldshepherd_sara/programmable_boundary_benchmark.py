from __future__ import annotations

import cmath
import math
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


class BoundaryControlMode(str, Enum):
    PASSIVE = "PASSIVE"
    RANDOM_OPEN_LOOP = "RANDOM_OPEN_LOOP"
    COHERENT_TARGET = "COHERENT_TARGET"
    NULL_TARGET = "NULL_TARGET"
    THERMAL_DRIFT = "THERMAL_DRIFT"


class TileState(BaseModel):
    tile_index: int = Field(ge=0)
    position_wavelengths: float
    amplitude: float = Field(ge=0.0)
    phase_radians: float
    normalized_temperature: float = Field(ge=0.0, le=1.0)


class BoundaryScenarioResult(BaseModel):
    scenario_id: str
    purpose: str
    mode: BoundaryControlMode
    target_angle_degrees: float | None
    preserve_angle_degrees: float | None
    tile_states: tuple[TileState, ...]
    total_element_power_proxy: float = Field(ge=0.0)
    target_normalized_field: float | None
    preserve_normalized_field: float | None
    pattern_rms_change_from_passive: float = Field(ge=0.0)
    peak_normalized_field: float = Field(ge=0.0)
    peak_angle_degrees: float
    control_phase_rms_radians: float = Field(ge=0.0)
    claims_boundary: tuple[str, ...]


class BoundaryBenchmarkSummary(BaseModel):
    coherent_gain_over_passive: float
    random_gain_over_passive: float
    null_suppression_ratio_vs_passive: float
    null_preserve_fraction: float
    thermal_target_retention_fraction: float
    equal_power_design_controls: bool
    expected_control_behavior_observed: bool


class ProgrammableBoundaryBenchmarkReport(BaseModel):
    qualification_id: str = "WS-QE-2026-EMB-001"
    benchmark_version: str = "0.1"
    tile_count: int = Field(ge=4)
    tile_spacing_wavelengths: float = Field(gt=0.0)
    pattern_angles_degrees: tuple[float, ...]
    scenarios: tuple[BoundaryScenarioResult, ...]
    summary: BoundaryBenchmarkSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    full_wave_solver_used: bool = False
    mutual_impedance_modeled: bool = False
    measured_material_properties_used: bool = False
    laboratory_validation_performed: bool = False
    stealth_or_cloaking_validated: bool = False
    broadband_spectrum_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "This is a deterministic synthetic array-factor surrogate, not a full-wave electromagnetic solver.",
        "No measured material property, mutual-impedance model, calibrated scattering result, stealth result, or cloaking result is represented.",
        "Successful execution establishes only bounded SIMULATED_ONLY field-shaping behavior for this exact benchmark.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "ProgrammableBoundaryBenchmarkReport":
        prohibited = (
            self.full_wave_solver_used,
            self.mutual_impedance_modeled,
            self.measured_material_properties_used,
            self.laboratory_validation_performed,
            self.stealth_or_cloaking_validated,
            self.broadband_spectrum_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("v0.1 benchmark cannot promote physical/full-wave/operational claims")
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("v0.1 benchmark must remain SIMULATED_ONLY")
        return self


def _positions(tile_count: int, spacing: float) -> tuple[float, ...]:
    center = (tile_count - 1) / 2.0
    return tuple((index - center) * spacing for index in range(tile_count))


def _steering_vector(
    *,
    angle_degrees: float,
    tile_count: int,
    spacing: float,
) -> tuple[complex, ...]:
    sine = math.sin(math.radians(angle_degrees))
    return tuple(
        cmath.exp(1j * 2.0 * math.pi * position * sine)
        for position in _positions(tile_count, spacing)
    )


def _field(weights: tuple[complex, ...], steering: tuple[complex, ...]) -> complex:
    return sum(weight * response for weight, response in zip(weights, steering, strict=True))


def _power_proxy(weights: tuple[complex, ...]) -> float:
    return sum(abs(weight) ** 2 for weight in weights)


def _normalize_design_power(weights: tuple[complex, ...], tile_count: int) -> tuple[complex, ...]:
    power = _power_proxy(weights)
    if power <= 0.0:
        raise ValueError("control weights must have positive power proxy")
    scale = math.sqrt(tile_count / power)
    return tuple(weight * scale for weight in weights)


def _passive_weights(tile_count: int) -> tuple[complex, ...]:
    return tuple(1.0 + 0.0j for _ in range(tile_count))


def _coherent_weights(*, angle_degrees: float, tile_count: int, spacing: float) -> tuple[complex, ...]:
    steering = _steering_vector(
        angle_degrees=angle_degrees,
        tile_count=tile_count,
        spacing=spacing,
    )
    return _normalize_design_power(tuple(value.conjugate() for value in steering), tile_count)


def _random_open_loop_weights(tile_count: int) -> tuple[complex, ...]:
    # Deterministic irrational phase progression: repeatable and intentionally not target-aware.
    golden_conjugate = (math.sqrt(5.0) - 1.0) / 2.0
    weights = tuple(
        cmath.exp(1j * 2.0 * math.pi * ((index * golden_conjugate) % 1.0))
        for index in range(tile_count)
    )
    return _normalize_design_power(weights, tile_count)


def _null_weights(
    *,
    preserve_angle_degrees: float,
    null_angle_degrees: float,
    tile_count: int,
    spacing: float,
) -> tuple[complex, ...]:
    preserve = _coherent_weights(
        angle_degrees=preserve_angle_degrees,
        tile_count=tile_count,
        spacing=spacing,
    )
    null_steering = _steering_vector(
        angle_degrees=null_angle_degrees,
        tile_count=tile_count,
        spacing=spacing,
    )
    null_conjugate = tuple(value.conjugate() for value in null_steering)
    numerator = _field(preserve, null_steering)
    denominator = _field(null_conjugate, null_steering)
    if abs(denominator) <= 1e-15:
        raise ValueError("degenerate null constraint")
    projected = tuple(
        weight - (numerator / denominator) * null_basis
        for weight, null_basis in zip(preserve, null_conjugate, strict=True)
    )
    return _normalize_design_power(projected, tile_count)


def _apply_thermal_drift(
    weights: tuple[complex, ...],
    *,
    phase_edge_radians: float = 0.8,
    edge_amplitude_derating: float = 0.12,
) -> tuple[complex, ...]:
    if not 0.0 <= edge_amplitude_derating < 1.0:
        raise ValueError("edge amplitude derating must be in [0, 1)")
    center = (len(weights) - 1) / 2.0
    if center <= 0.0:
        raise ValueError("thermal model requires multiple tiles")
    drifted: list[complex] = []
    for index, weight in enumerate(weights):
        normalized_position = (index - center) / center
        phase_error = phase_edge_radians * normalized_position
        amplitude_scale = 1.0 - edge_amplitude_derating * abs(normalized_position)
        drifted.append(weight * amplitude_scale * cmath.exp(1j * phase_error))
    return tuple(drifted)


def _phase_rms(weights: tuple[complex, ...]) -> float:
    phases = tuple(cmath.phase(weight) for weight in weights)
    return math.sqrt(sum(phase * phase for phase in phases) / len(phases))


def _temperature_profile(tile_count: int, *, thermal: bool) -> tuple[float, ...]:
    if not thermal:
        return tuple(0.0 for _ in range(tile_count))
    center = (tile_count - 1) / 2.0
    return tuple(abs((index - center) / center) for index in range(tile_count))


def _states(
    weights: tuple[complex, ...],
    *,
    spacing: float,
    thermal: bool,
) -> tuple[TileState, ...]:
    temperatures = _temperature_profile(len(weights), thermal=thermal)
    return tuple(
        TileState(
            tile_index=index,
            position_wavelengths=position,
            amplitude=abs(weight),
            phase_radians=cmath.phase(weight),
            normalized_temperature=temperatures[index],
        )
        for index, (position, weight) in enumerate(
            zip(_positions(len(weights), spacing), weights, strict=True)
        )
    )


def _pattern(
    weights: tuple[complex, ...],
    *,
    angles: tuple[float, ...],
    spacing: float,
) -> tuple[float, ...]:
    normalization = max(1e-15, sum(abs(weight) for weight in weights))
    return tuple(
        abs(
            _field(
                weights,
                _steering_vector(
                    angle_degrees=angle,
                    tile_count=len(weights),
                    spacing=spacing,
                ),
            )
        )
        / normalization
        for angle in angles
    )


def _at_angle(
    weights: tuple[complex, ...],
    *,
    angle: float,
    spacing: float,
) -> float:
    normalization = max(1e-15, sum(abs(weight) for weight in weights))
    return abs(
        _field(
            weights,
            _steering_vector(
                angle_degrees=angle,
                tile_count=len(weights),
                spacing=spacing,
            ),
        )
    ) / normalization


def _rms_difference(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.sqrt(
        sum((a - b) ** 2 for a, b in zip(left, right, strict=True)) / len(left)
    )


def _scenario_result(
    *,
    scenario_id: str,
    purpose: str,
    mode: BoundaryControlMode,
    weights: tuple[complex, ...],
    passive_pattern: tuple[float, ...],
    pattern_angles: tuple[float, ...],
    spacing: float,
    target_angle: float | None,
    preserve_angle: float | None,
    thermal: bool = False,
) -> BoundaryScenarioResult:
    response = _pattern(weights, angles=pattern_angles, spacing=spacing)
    peak_index = max(range(len(response)), key=response.__getitem__)
    return BoundaryScenarioResult(
        scenario_id=scenario_id,
        purpose=purpose,
        mode=mode,
        target_angle_degrees=target_angle,
        preserve_angle_degrees=preserve_angle,
        tile_states=_states(weights, spacing=spacing, thermal=thermal),
        total_element_power_proxy=_power_proxy(weights),
        target_normalized_field=(
            None if target_angle is None else _at_angle(weights, angle=target_angle, spacing=spacing)
        ),
        preserve_normalized_field=(
            None
            if preserve_angle is None
            else _at_angle(weights, angle=preserve_angle, spacing=spacing)
        ),
        pattern_rms_change_from_passive=_rms_difference(response, passive_pattern),
        peak_normalized_field=response[peak_index],
        peak_angle_degrees=pattern_angles[peak_index],
        control_phase_rms_radians=_phase_rms(weights),
        claims_boundary=(
            "Normalized field values are synthetic array-factor proxies.",
            "No physical scattering cross section or material response is inferred.",
        ),
    )


def run_programmable_boundary_benchmark(
    *,
    tile_count: int = 8,
    tile_spacing_wavelengths: float = 0.5,
    coherent_target_angle_degrees: float = 20.0,
    null_angle_degrees: float = 0.0,
    preserve_angle_degrees: float = 25.0,
) -> ProgrammableBoundaryBenchmarkReport:
    if tile_count < 4:
        raise ValueError("tile_count must be >= 4")
    if not 0.0 < tile_spacing_wavelengths <= 0.5:
        raise ValueError("v0.1 requires tile spacing in (0, 0.5] wavelengths")
    for angle in (
        coherent_target_angle_degrees,
        null_angle_degrees,
        preserve_angle_degrees,
    ):
        if not -60.0 <= angle <= 60.0:
            raise ValueError("benchmark angles must remain within [-60, 60] degrees")

    pattern_angles = tuple(float(angle) for angle in range(-60, 61, 5))
    passive = _passive_weights(tile_count)
    random_weights = _random_open_loop_weights(tile_count)
    coherent = _coherent_weights(
        angle_degrees=coherent_target_angle_degrees,
        tile_count=tile_count,
        spacing=tile_spacing_wavelengths,
    )
    null_control = _null_weights(
        preserve_angle_degrees=preserve_angle_degrees,
        null_angle_degrees=null_angle_degrees,
        tile_count=tile_count,
        spacing=tile_spacing_wavelengths,
    )
    thermal = _apply_thermal_drift(coherent)
    passive_pattern = _pattern(
        passive,
        angles=pattern_angles,
        spacing=tile_spacing_wavelengths,
    )

    scenarios = (
        _scenario_result(
            scenario_id="passive_reference",
            purpose="non-adaptive reference with uniform tile state",
            mode=BoundaryControlMode.PASSIVE,
            weights=passive,
            passive_pattern=passive_pattern,
            pattern_angles=pattern_angles,
            spacing=tile_spacing_wavelengths,
            target_angle=coherent_target_angle_degrees,
            preserve_angle=preserve_angle_degrees,
        ),
        _scenario_result(
            scenario_id="random_open_loop",
            purpose="deterministic target-unaware open-loop control",
            mode=BoundaryControlMode.RANDOM_OPEN_LOOP,
            weights=random_weights,
            passive_pattern=passive_pattern,
            pattern_angles=pattern_angles,
            spacing=tile_spacing_wavelengths,
            target_angle=coherent_target_angle_degrees,
            preserve_angle=preserve_angle_degrees,
        ),
        _scenario_result(
            scenario_id="coherent_target",
            purpose="phase-coherent positive control at a generic observation angle",
            mode=BoundaryControlMode.COHERENT_TARGET,
            weights=coherent,
            passive_pattern=passive_pattern,
            pattern_angles=pattern_angles,
            spacing=tile_spacing_wavelengths,
            target_angle=coherent_target_angle_degrees,
            preserve_angle=preserve_angle_degrees,
        ),
        _scenario_result(
            scenario_id="null_target",
            purpose="constrained generic field minimum while preserving a separate observation angle",
            mode=BoundaryControlMode.NULL_TARGET,
            weights=null_control,
            passive_pattern=passive_pattern,
            pattern_angles=pattern_angles,
            spacing=tile_spacing_wavelengths,
            target_angle=null_angle_degrees,
            preserve_angle=preserve_angle_degrees,
        ),
        _scenario_result(
            scenario_id="thermal_drift",
            purpose="coherent-control sensitivity to deterministic phase drift and edge derating",
            mode=BoundaryControlMode.THERMAL_DRIFT,
            weights=thermal,
            passive_pattern=passive_pattern,
            pattern_angles=pattern_angles,
            spacing=tile_spacing_wavelengths,
            target_angle=coherent_target_angle_degrees,
            preserve_angle=preserve_angle_degrees,
            thermal=True,
        ),
    )
    by_id = {scenario.scenario_id: scenario for scenario in scenarios}
    passive_target = by_id["passive_reference"].target_normalized_field or 0.0
    random_target = by_id["random_open_loop"].target_normalized_field or 0.0
    coherent_target = by_id["coherent_target"].target_normalized_field or 0.0
    passive_null = _at_angle(passive, angle=null_angle_degrees, spacing=tile_spacing_wavelengths)
    controlled_null = by_id["null_target"].target_normalized_field or 0.0
    null_preserve = by_id["null_target"].preserve_normalized_field or 0.0
    coherent_preserve_reference = _at_angle(
        _coherent_weights(
            angle_degrees=preserve_angle_degrees,
            tile_count=tile_count,
            spacing=tile_spacing_wavelengths,
        ),
        angle=preserve_angle_degrees,
        spacing=tile_spacing_wavelengths,
    )
    thermal_target = by_id["thermal_drift"].target_normalized_field or 0.0

    equal_power = all(
        abs(by_id[key].total_element_power_proxy - tile_count) <= 1e-10
        for key in (
            "passive_reference",
            "random_open_loop",
            "coherent_target",
            "null_target",
        )
    )
    coherent_gain = coherent_target / max(passive_target, 1e-15)
    random_gain = random_target / max(passive_target, 1e-15)
    null_suppression = controlled_null / max(passive_null, 1e-15)
    null_preserve_fraction = null_preserve / max(coherent_preserve_reference, 1e-15)
    thermal_retention = thermal_target / max(coherent_target, 1e-15)
    behavior_observed = (
        equal_power
        and coherent_gain > 1.5
        and null_suppression < 1e-6
        and null_preserve_fraction > 0.75
        and thermal_retention < 0.98
    )

    report = ProgrammableBoundaryBenchmarkReport(
        tile_count=tile_count,
        tile_spacing_wavelengths=tile_spacing_wavelengths,
        pattern_angles_degrees=pattern_angles,
        scenarios=scenarios,
        summary=BoundaryBenchmarkSummary(
            coherent_gain_over_passive=coherent_gain,
            random_gain_over_passive=random_gain,
            null_suppression_ratio_vs_passive=null_suppression,
            null_preserve_fraction=null_preserve_fraction,
            thermal_target_retention_fraction=thermal_retention,
            equal_power_design_controls=equal_power,
            expected_control_behavior_observed=behavior_observed,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_programmable_boundary_benchmark_report(
    report: ProgrammableBoundaryBenchmarkReport,
) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
