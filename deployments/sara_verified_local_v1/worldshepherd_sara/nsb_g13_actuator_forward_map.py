from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .nsb_g3_solver import _spectral_divergence_rms, _velocity_and_streamfunction
from .nsb_g10_nonlinear_mhd import _magnetic_state, _mixed_initial
from .nsb_g12_adaptive_lorentz_control import (
    _basis_fields,
    _commands,
    _controlled_midpoint_step,
    _enstrophy,
    _source_from_commands,
    _target_modal_energy,
    integrate_feedback_control,
)
from .qualification import CapabilityStatus, canonical_digest


class G13AllocationCase(BaseModel):
    tile_count: int = Field(ge=4)
    target_commands: tuple[float, float, float]
    realized_commands: tuple[float, float, float]
    actuator_commands: tuple[float, ...]
    actuator_limit: float = Field(gt=0.0)
    max_abs_actuator_command: float = Field(ge=0.0)
    power_proxy: float = Field(ge=0.0)
    relative_residual: float = Field(ge=0.0)
    transfer_condition_number: float = Field(ge=1.0)
    effective_rank: int = Field(ge=0, le=3)
    saturated_actuators: int = Field(ge=0)


class G13CalibrationCase(BaseModel):
    gain_profile: tuple[float, ...]
    uncalibrated_relative_residual: float = Field(ge=0.0)
    calibrated_relative_residual: float = Field(ge=0.0)
    calibrated_max_abs_actuator_command: float = Field(ge=0.0)
    calibrated_condition_number: float = Field(ge=1.0)


class G13FaultCase(BaseModel):
    disabled_tile_index: int = Field(ge=0)
    relative_residual: float = Field(ge=0.0)
    max_abs_actuator_command: float = Field(ge=0.0)
    transfer_condition_number: float = Field(ge=1.0)
    effective_rank: int = Field(ge=0, le=3)


class G13SaturationCase(BaseModel):
    target_scale: float = Field(gt=1.0)
    relative_residual: float = Field(ge=0.0)
    saturated_actuators: int = Field(ge=0)
    correctly_flagged_unreachable: bool


class G13ClosedLoopCase(BaseModel):
    grid_size: int = Field(ge=8)
    viscosity: float = Field(gt=0.0)
    resistivity: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    dt: float = Field(gt=0.0)
    feedback_gain: float = Field(gt=0.0)
    g12_command_limit: float = Field(gt=0.0)
    actuator_limit: float = Field(gt=0.0)
    target_modal_energy_baseline_final: float = Field(ge=0.0)
    target_modal_energy_ideal_g12_final: float = Field(ge=0.0)
    target_modal_energy_forward_map_final: float = Field(ge=0.0)
    target_modal_energy_reduction_fraction: float
    forward_map_vs_ideal_relative_gap: float = Field(ge=0.0)
    baseline_enstrophy_final: float = Field(ge=0.0)
    forward_map_enstrophy_final: float = Field(ge=0.0)
    enstrophy_reduction_fraction: float
    actuator_effort: float = Field(ge=0.0)
    max_abs_actuator_command: float = Field(ge=0.0)
    max_modal_tracking_residual: float = Field(ge=0.0)
    velocity_divergence_rms: float = Field(ge=0.0)
    magnetic_divergence_rms: float = Field(ge=0.0)


class G13AcceptanceSummary(BaseModel):
    nominal_residual_limit: float = Field(gt=0.0)
    fault_residual_limit: float = Field(gt=0.0)
    calibrated_residual_limit: float = Field(gt=0.0)
    condition_number_limit: float = Field(gt=1.0)
    target_reduction_floor: float = Field(gt=0.0)
    ideal_gap_limit: float = Field(gt=0.0)
    divergence_limit: float = Field(gt=0.0)
    nominal_reachability_pass: bool
    calibration_pass: bool
    single_fault_pass: bool
    saturation_detection_pass: bool
    closed_loop_pass: bool
    geometry_pass: bool
    acceptance_pass: bool


class NSBG13Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G13-001"
    benchmark_version: str = "1.8"
    formulation: str = "bounded synthetic actuator-to-G12 modal-force forward-map and reachability gate"
    actuator_model: str = "8-channel normalized periodic current-sheet surrogate mapped to the three G12 Lorentz-curl control modes"
    allocator: str = "regularized minimum-norm modal allocation with hard per-actuator saturation"
    nominal_case: G13AllocationCase
    calibration_case: G13CalibrationCase
    fault_case: G13FaultCase
    saturation_case: G13SaturationCase
    closed_loop_case: G13ClosedLoopCase
    acceptance: G13AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    actuator_forward_map_simulated: bool = True
    modal_reachability_quantified: bool = True
    saturation_and_fault_cases_executed: bool = True
    g12_loop_executed_through_forward_map: bool = True
    physical_actuator_mapping_validated: bool = False
    full_wave_em_solved: bool = False
    measured_coil_or_electrode_transfer_used: bool = False
    hardware_boundary_control_validated: bool = False
    laboratory_validation_performed: bool = False
    adaptive_em_control_validated: bool = False
    plasma_validated: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G13 is a deterministic engineering surrogate that maps bounded actuator channels into the three abstract G12 Lorentz-force-curl modes.",
        "The transfer matrix is synthetic and normalized; it is not derived from a full-wave Maxwell solve, Biot-Savart coil geometry, measured electrode response, or calibrated hardware.",
        "Passing G13 establishes only simulated reachability, allocation, saturation, fault, calibration, and closed-loop behavior for this surrogate.",
        "G13 does not establish physical actuator realizability, laboratory adaptive EM control, plasma capability, propulsion, shielding, stealth, cloaking, or operational performance.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG13Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.8 must remain SIMULATED_ONLY")
        required = (
            self.actuator_forward_map_simulated,
            self.modal_reachability_quantified,
            self.saturation_and_fault_cases_executed,
            self.g12_loop_executed_through_forward_map,
        )
        if not all(required):
            raise ValueError("G13 report must represent the executed surrogate forward-map gate")
        prohibited = (
            self.physical_actuator_mapping_validated,
            self.full_wave_em_solved,
            self.measured_coil_or_electrode_transfer_used,
            self.hardware_boundary_control_validated,
            self.laboratory_validation_performed,
            self.adaptive_em_control_validated,
            self.plasma_validated,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v1.8 cannot promote unsupported physical or hardware claims")
        return self


def _normalize(row: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in row))
    if norm <= 1e-15:
        raise ValueError("degenerate transfer row")
    return [value / norm for value in row]


def build_transfer_matrix(
    *,
    tile_count: int = 8,
    gain_profile: tuple[float, ...] | None = None,
    disabled_tile_index: int | None = None,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    if tile_count < 4:
        raise ValueError("tile_count must be >= 4")
    if gain_profile is None:
        gain_profile = tuple(1.0 for _ in range(tile_count))
    if len(gain_profile) != tile_count or any(value <= 0.0 for value in gain_profile):
        raise ValueError("gain_profile must contain one positive gain per tile")
    if disabled_tile_index is not None and not 0 <= disabled_tile_index < tile_count:
        raise ValueError("disabled_tile_index out of range")
    positions = tuple(2.0 * math.pi * index / tile_count for index in range(tile_count))
    rows = (
        _normalize([math.cos(x) for x in positions]),
        _normalize([math.sin(2.0 * x + 0.3) for x in positions]),
        _normalize([math.cos(3.0 * x - 0.2) for x in positions]),
    )
    matrix: list[tuple[float, ...]] = []
    for row in rows:
        values = []
        for index, value in enumerate(row):
            gain = 0.0 if index == disabled_tile_index else gain_profile[index]
            values.append(value * gain)
        matrix.append(tuple(values))
    return tuple(matrix)  # type: ignore[return-value]


def _gram(matrix):
    return [[sum(matrix[i][k] * matrix[j][k] for k in range(len(matrix[0]))) for j in range(3)] for i in range(3)]


def _inverse3(matrix):
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) <= 1e-15:
        raise ValueError("singular 3x3 allocation matrix")
    return [
        [(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
        [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
        [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det],
    ]


def _jacobi_eigenvalues_sym3(matrix):
    a = [row[:] for row in matrix]
    for _ in range(40):
        pairs = ((0, 1), (0, 2), (1, 2))
        p, q = max(pairs, key=lambda pair: abs(a[pair[0]][pair[1]]))
        apq = a[p][q]
        if abs(apq) <= 1e-14:
            break
        tau = (a[q][q] - a[p][p]) / (2.0 * apq)
        t = (1.0 if tau >= 0.0 else -1.0) / (abs(tau) + math.sqrt(1.0 + tau * tau))
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        app = a[p][p]
        aqq = a[q][q]
        a[p][p] = c * c * app - 2.0 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2.0 * s * c * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0
        for r in range(3):
            if r in (p, q):
                continue
            arp = a[r][p]
            arq = a[r][q]
            a[r][p] = a[p][r] = c * arp - s * arq
            a[r][q] = a[q][r] = s * arp + c * arq
    return tuple(sorted((a[0][0], a[1][1], a[2][2])))


def _condition_and_rank(matrix):
    eigenvalues = _jacobi_eigenvalues_sym3(_gram(matrix))
    largest = max(eigenvalues)
    threshold = largest * 1e-10
    positive = [value for value in eigenvalues if value > threshold]
    rank = len(positive)
    if rank < 3:
        return math.inf, rank
    return math.sqrt(largest / min(positive)), rank


def _matvec(matrix, vector):
    return tuple(sum(matrix[row][col] * vector[col] for col in range(len(vector))) for row in range(3))


def allocate_modal_command(
    target: tuple[float, float, float],
    *,
    matrix,
    actuator_limit: float = 3.0,
    regularization: float = 1e-12,
):
    if actuator_limit <= 0.0 or regularization < 0.0:
        raise ValueError("actuator_limit must be positive and regularization nonnegative")
    if len(matrix) != 3 or any(len(row) < 4 for row in matrix):
        raise ValueError("transfer matrix must be 3xN with N >= 4")
    target_norm = math.sqrt(sum(value * value for value in target))
    if target_norm <= 1e-15:
        currents = tuple(0.0 for _ in matrix[0])
        return currents, (0.0, 0.0, 0.0), 0.0, 0
    gram = _gram(matrix)
    for index in range(3):
        gram[index][index] += regularization
    inverse = _inverse3(gram)
    y = tuple(sum(inverse[i][j] * target[j] for j in range(3)) for i in range(3))
    unconstrained = tuple(sum(matrix[row][col] * y[row] for row in range(3)) for col in range(len(matrix[0])))
    currents = tuple(max(-actuator_limit, min(actuator_limit, value)) for value in unconstrained)
    saturated = sum(abs(value) >= actuator_limit - 1e-12 for value in currents)
    realized = _matvec(matrix, currents)
    residual = math.sqrt(sum((realized[i] - target[i]) ** 2 for i in range(3))) / target_norm
    return currents, realized, residual, saturated


def _allocation_case(target, *, matrix, actuator_limit: float) -> G13AllocationCase:
    currents, realized, residual, saturated = allocate_modal_command(target, matrix=matrix, actuator_limit=actuator_limit)
    condition, rank = _condition_and_rank(matrix)
    return G13AllocationCase(
        tile_count=len(matrix[0]),
        target_commands=target,
        realized_commands=realized,
        actuator_commands=currents,
        actuator_limit=actuator_limit,
        max_abs_actuator_command=max(abs(value) for value in currents),
        power_proxy=sum(value * value for value in currents),
        relative_residual=residual,
        transfer_condition_number=condition,
        effective_rank=rank,
        saturated_actuators=saturated,
    )


def _representative_g12_target() -> tuple[float, float, float]:
    omega, _ = _mixed_initial(16)
    commands, _ = _commands(omega, gain=4.0, command_limit=2.0, feedback_sign=-1.0)
    return tuple(float(value) for value in commands)  # type: ignore[return-value]


def _calibration_case(target, *, actuator_limit: float) -> G13CalibrationCase:
    gains = (0.90, 0.95, 1.00, 1.05, 1.10, 1.08, 0.92, 1.03)
    nominal = build_transfer_matrix(tile_count=8)
    actual = build_transfer_matrix(tile_count=8, gain_profile=gains)
    nominal_currents, _, _, _ = allocate_modal_command(target, matrix=nominal, actuator_limit=actuator_limit)
    realized_uncalibrated = _matvec(actual, nominal_currents)
    norm = math.sqrt(sum(value * value for value in target))
    uncalibrated = math.sqrt(sum((realized_uncalibrated[i] - target[i]) ** 2 for i in range(3))) / norm
    calibrated_currents, _, calibrated, _ = allocate_modal_command(target, matrix=actual, actuator_limit=actuator_limit)
    condition, _ = _condition_and_rank(actual)
    return G13CalibrationCase(
        gain_profile=gains,
        uncalibrated_relative_residual=uncalibrated,
        calibrated_relative_residual=calibrated,
        calibrated_max_abs_actuator_command=max(abs(value) for value in calibrated_currents),
        calibrated_condition_number=condition,
    )


def _fault_case(target, *, actuator_limit: float) -> G13FaultCase:
    disabled = 0
    matrix = build_transfer_matrix(tile_count=8, disabled_tile_index=disabled)
    currents, _, residual, _ = allocate_modal_command(target, matrix=matrix, actuator_limit=actuator_limit)
    condition, rank = _condition_and_rank(matrix)
    return G13FaultCase(
        disabled_tile_index=disabled,
        relative_residual=residual,
        max_abs_actuator_command=max(abs(value) for value in currents),
        transfer_condition_number=condition,
        effective_rank=rank,
    )


def _saturation_case(target, *, actuator_limit: float) -> G13SaturationCase:
    scale = 3.0
    scaled = tuple(scale * value for value in target)
    matrix = build_transfer_matrix(tile_count=8)
    _, _, residual, saturated = allocate_modal_command(scaled, matrix=matrix, actuator_limit=actuator_limit)
    return G13SaturationCase(
        target_scale=scale,
        relative_residual=residual,
        saturated_actuators=saturated,
        correctly_flagged_unreachable=residual > 0.05 and saturated > 0,
    )


def _integrate_forward_mapped_feedback(
    *,
    initial_vorticity,
    initial_magnetic_potential,
    viscosity: float,
    resistivity: float,
    dt: float,
    final_time: float,
    gain: float,
    command_limit: float,
    actuator_limit: float,
    matrix,
):
    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    omega = [row[:] for row in initial_vorticity]
    a = [row[:] for row in initial_magnetic_potential]
    effort = 0.0
    max_actuator = 0.0
    max_tracking_residual = 0.0
    for _ in range(steps):
        desired, bases = _commands(omega, gain=gain, command_limit=command_limit, feedback_sign=-1.0)
        currents, realized, residual, _ = allocate_modal_command(tuple(desired), matrix=matrix, actuator_limit=actuator_limit)
        max_tracking_residual = max(max_tracking_residual, residual)
        max_actuator = max(max_actuator, *(abs(value) for value in currents))
        effort += effective_dt * sum(value * value for value in currents)
        source = _source_from_commands(realized, bases)
        omega, a = _controlled_midpoint_step(
            omega,
            a,
            dt=effective_dt,
            viscosity=viscosity,
            resistivity=resistivity,
            source=source,
        )
    return omega, a, effective_dt, effort, max_actuator, max_tracking_residual


def _closed_loop_case(
    *,
    n: int = 16,
    viscosity: float = 0.01,
    resistivity: float = 0.015,
    dt: float = 0.0005,
    final_time: float = 0.05,
    feedback_gain: float = 4.0,
    command_limit: float = 2.0,
    actuator_limit: float = 3.0,
) -> G13ClosedLoopCase:
    omega0, a0 = _mixed_initial(n)
    baseline_w, _, _, _, _, _, _, _ = integrate_feedback_control(
        initial_vorticity=omega0,
        initial_magnetic_potential=a0,
        viscosity=viscosity,
        resistivity=resistivity,
        dt=dt,
        final_time=final_time,
        gain=0.0,
        command_limit=command_limit,
        feedback_sign=-1.0,
    )
    ideal_w, _, _, _, _, _, _, _ = integrate_feedback_control(
        initial_vorticity=omega0,
        initial_magnetic_potential=a0,
        viscosity=viscosity,
        resistivity=resistivity,
        dt=dt,
        final_time=final_time,
        gain=feedback_gain,
        command_limit=command_limit,
        feedback_sign=-1.0,
    )
    matrix = build_transfer_matrix(tile_count=8)
    realized_w, realized_a, effective_dt, effort, max_actuator, max_residual = _integrate_forward_mapped_feedback(
        initial_vorticity=omega0,
        initial_magnetic_potential=a0,
        viscosity=viscosity,
        resistivity=resistivity,
        dt=dt,
        final_time=final_time,
        gain=feedback_gain,
        command_limit=command_limit,
        actuator_limit=actuator_limit,
        matrix=matrix,
    )
    baseline_target = _target_modal_energy(baseline_w)
    ideal_target = _target_modal_energy(ideal_w)
    realized_target = _target_modal_energy(realized_w)
    baseline_enstrophy = _enstrophy(baseline_w)
    realized_enstrophy = _enstrophy(realized_w)
    u, v, _ = _velocity_and_streamfunction(realized_w)
    bx, by, _ = _magnetic_state(realized_a)
    return G13ClosedLoopCase(
        grid_size=n,
        viscosity=viscosity,
        resistivity=resistivity,
        final_time=final_time,
        dt=effective_dt,
        feedback_gain=feedback_gain,
        g12_command_limit=command_limit,
        actuator_limit=actuator_limit,
        target_modal_energy_baseline_final=baseline_target,
        target_modal_energy_ideal_g12_final=ideal_target,
        target_modal_energy_forward_map_final=realized_target,
        target_modal_energy_reduction_fraction=(baseline_target - realized_target) / max(baseline_target, 1e-15),
        forward_map_vs_ideal_relative_gap=abs(realized_target - ideal_target) / max(abs(ideal_target), 1e-15),
        baseline_enstrophy_final=baseline_enstrophy,
        forward_map_enstrophy_final=realized_enstrophy,
        enstrophy_reduction_fraction=(baseline_enstrophy - realized_enstrophy) / max(baseline_enstrophy, 1e-15),
        actuator_effort=effort,
        max_abs_actuator_command=max_actuator,
        max_modal_tracking_residual=max_residual,
        velocity_divergence_rms=_spectral_divergence_rms(u, v),
        magnetic_divergence_rms=_spectral_divergence_rms(bx, by),
    )


def run_nsb_g13_benchmark(
    *,
    nominal_residual_limit: float = 5e-4,
    fault_residual_limit: float = 5e-3,
    calibrated_residual_limit: float = 5e-4,
    condition_number_limit: float = 3.0,
    target_reduction_floor: float = 0.15,
    ideal_gap_limit: float = 0.01,
    divergence_limit: float = 1e-10,
) -> NSBG13Report:
    target = _representative_g12_target()
    actuator_limit = 3.0
    nominal = _allocation_case(target, matrix=build_transfer_matrix(tile_count=8), actuator_limit=actuator_limit)
    calibration = _calibration_case(target, actuator_limit=actuator_limit)
    fault = _fault_case(target, actuator_limit=actuator_limit)
    saturation = _saturation_case(target, actuator_limit=actuator_limit)
    closed = _closed_loop_case(actuator_limit=actuator_limit)

    nominal_pass = (
        nominal.effective_rank == 3
        and nominal.transfer_condition_number <= condition_number_limit
        and nominal.relative_residual <= nominal_residual_limit
        and nominal.max_abs_actuator_command <= nominal.actuator_limit + 1e-12
    )
    calibration_pass = (
        calibration.calibrated_relative_residual <= calibrated_residual_limit
        and calibration.calibrated_relative_residual < calibration.uncalibrated_relative_residual
        and calibration.calibrated_condition_number <= condition_number_limit
        and calibration.calibrated_max_abs_actuator_command <= actuator_limit + 1e-12
    )
    fault_pass = (
        fault.effective_rank == 3
        and fault.relative_residual <= fault_residual_limit
        and fault.transfer_condition_number <= condition_number_limit
        and fault.max_abs_actuator_command <= actuator_limit + 1e-12
    )
    saturation_pass = saturation.correctly_flagged_unreachable
    closed_pass = (
        closed.target_modal_energy_reduction_fraction >= target_reduction_floor
        and closed.forward_map_vs_ideal_relative_gap <= ideal_gap_limit
        and closed.max_abs_actuator_command <= actuator_limit + 1e-12
        and closed.actuator_effort > 0.0
        and closed.max_modal_tracking_residual <= nominal_residual_limit
    )
    geometry_pass = max(closed.velocity_divergence_rms, closed.magnetic_divergence_rms) <= divergence_limit
    acceptance_pass = all((nominal_pass, calibration_pass, fault_pass, saturation_pass, closed_pass, geometry_pass))

    report = NSBG13Report(
        nominal_case=nominal,
        calibration_case=calibration,
        fault_case=fault,
        saturation_case=saturation,
        closed_loop_case=closed,
        acceptance=G13AcceptanceSummary(
            nominal_residual_limit=nominal_residual_limit,
            fault_residual_limit=fault_residual_limit,
            calibrated_residual_limit=calibrated_residual_limit,
            condition_number_limit=condition_number_limit,
            target_reduction_floor=target_reduction_floor,
            ideal_gap_limit=ideal_gap_limit,
            divergence_limit=divergence_limit,
            nominal_reachability_pass=nominal_pass,
            calibration_pass=calibration_pass,
            single_fault_pass=fault_pass,
            saturation_detection_pass=saturation_pass,
            closed_loop_pass=closed_pass,
            geometry_pass=geometry_pass,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g13_report(report: NSBG13Report) -> bool:
    return report.report_digest == canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
