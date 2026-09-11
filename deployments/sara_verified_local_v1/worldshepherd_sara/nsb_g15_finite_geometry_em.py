from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .nsb_g3_solver import _spectral_divergence_rms, _velocity_and_streamfunction
from .nsb_g10_nonlinear_mhd import _magnetic_state, _mixed_initial
from .nsb_g12_adaptive_lorentz_control import _basis_fields, _enstrophy, _target_modal_energy, integrate_feedback_control
from .nsb_g13_actuator_forward_map import _condition_and_rank, _integrate_forward_mapped_feedback, _representative_g12_target, allocate_modal_command
from .nsb_g14_geometry_em_forward_map import G14Geometry, build_geometry_transfer_matrix
from .qualification import CapabilityStatus, canonical_digest

MU0_OVER_4PI = 1.0e-7
COPPER_RESISTIVITY_OHM_M = 1.68e-8
COPPER_DENSITY_KG_M3 = 8960.0


class G15Geometry(BaseModel):
    grid_size: int = Field(default=16, ge=8)
    domain_length_m: float = Field(default=0.10, gt=0.0)
    reference_velocity_m_s: float = Field(default=0.03, gt=0.0)
    fluid_density_kg_m3: float = Field(default=6400.0, gt=0.0)
    conductivity_s_m: float = Field(default=3.4e6, gt=0.0)
    electrode_voltage_drop_v: float = Field(default=0.014705882352941176, gt=0.0)
    coil_count: int = Field(default=8, ge=4)
    coil_ring_radius_m: float = Field(default=0.070, gt=0.0)
    coil_radius_m: float = Field(default=0.010, gt=0.0)
    coil_turns: int = Field(default=200, ge=1)
    coil_standoff_m: float = Field(default=0.025, gt=0.0)
    coil_angular_offset_deg: float = 22.5
    coil_segments: int = Field(default=96, ge=12)
    conductor_cross_section_m2: float = Field(default=1.0e-6, gt=0.0)
    coil_current_limit_a: float = Field(default=3.5, gt=0.0)


class G15ConductionCase(BaseModel):
    iterations: int = Field(ge=0)
    max_laplace_residual_v_m2: float = Field(ge=0.0)
    mean_jy_a_m2: float
    jy_relative_std: float = Field(ge=0.0)
    max_abs_jx_a_m2: float = Field(ge=0.0)
    max_abs_current_divergence_a_m3: float = Field(ge=0.0)
    target_uniform_jy_a_m2: float
    mean_jy_relative_error: float = Field(ge=0.0)


class G15LoopVerificationCase(BaseModel):
    segment_counts: tuple[int, ...]
    on_axis_relative_errors: tuple[float, ...]
    convergence_ratio_24_to_48: float = Field(ge=0.0)
    convergence_ratio_48_to_96: float = Field(ge=0.0)
    finest_relative_error: float = Field(ge=0.0)


class G15NominalCase(BaseModel):
    target_commands: tuple[float, float, float]
    realized_commands: tuple[float, float, float]
    coil_currents_a: tuple[float, ...]
    effective_rank: int = Field(ge=0, le=3)
    transfer_condition_number: float = Field(ge=1.0)
    relative_modal_residual: float = Field(ge=0.0)
    max_abs_coil_current_a: float = Field(ge=0.0)
    saturated_coils: int = Field(ge=0)
    max_abs_bz_t: float = Field(ge=0.0)
    rms_bz_t: float = Field(ge=0.0)
    total_joule_power_w: float = Field(ge=0.0)
    total_copper_mass_kg: float = Field(ge=0.0)
    relative_transfer_change_vs_g14: float = Field(ge=0.0)


class G15FaultCase(BaseModel):
    worst_disabled_coil_index: int = Field(ge=0)
    worst_relative_modal_residual: float = Field(ge=0.0)
    worst_max_abs_current_a: float = Field(ge=0.0)
    worst_condition_number: float = Field(ge=1.0)
    all_single_coil_faults_rank_three: bool


class G15ClosedLoopCase(BaseModel):
    target_modal_energy_baseline_final: float = Field(ge=0.0)
    target_modal_energy_ideal_g12_final: float = Field(ge=0.0)
    target_modal_energy_finite_geometry_final: float = Field(ge=0.0)
    target_modal_energy_reduction_fraction: float
    finite_geometry_vs_ideal_relative_gap: float = Field(ge=0.0)
    baseline_enstrophy_final: float = Field(ge=0.0)
    finite_geometry_enstrophy_final: float = Field(ge=0.0)
    enstrophy_reduction_fraction: float
    coil_current_effort_a2_s: float = Field(ge=0.0)
    max_abs_coil_current_a: float = Field(ge=0.0)
    max_modal_tracking_residual: float = Field(ge=0.0)
    velocity_divergence_rms: float = Field(ge=0.0)
    magnetic_divergence_rms: float = Field(ge=0.0)


class G15AcceptanceSummary(BaseModel):
    loop_error_limit: float = Field(gt=0.0)
    conduction_relative_error_limit: float = Field(gt=0.0)
    conduction_uniformity_limit: float = Field(gt=0.0)
    condition_number_limit: float = Field(gt=1.0)
    nominal_residual_limit: float = Field(gt=0.0)
    fault_residual_limit: float = Field(gt=0.0)
    target_reduction_floor: float = Field(gt=0.0)
    ideal_gap_limit: float = Field(gt=0.0)
    divergence_limit: float = Field(gt=0.0)
    loop_verification_pass: bool
    conduction_solve_pass: bool
    nominal_reachability_pass: bool
    single_fault_pass: bool
    closed_loop_pass: bool
    acceptance_pass: bool


class NSBG15Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G15-001"
    benchmark_version: str = "2.0"
    formulation: str = "finite-segment Biot-Savart circular-coil geometry plus solved conductive-potential current field projected into G12 Lorentz-curl modes"
    geometry: G15Geometry
    conduction_case: G15ConductionCase
    loop_verification_case: G15LoopVerificationCase
    nominal_case: G15NominalCase
    fault_case: G15FaultCase
    closed_loop_case: G15ClosedLoopCase
    acceptance: G15AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    finite_segment_biot_savart_simulated: bool = True
    conduction_potential_solved: bool = True
    lorentz_curl_projection_executed: bool = True
    g12_loop_executed_through_finite_geometry_map: bool = True
    continuous_wire_solution_validated: bool = False
    mutual_inductance_or_driver_dynamics_modeled: bool = False
    measured_conductivity_or_contact_impedance_used: bool = False
    coupled_thermal_state_validated: bool = False
    full_wave_maxwell_solved: bool = False
    laboratory_validation_performed: bool = False
    adaptive_em_control_validated: bool = False
    plasma_validated: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G15 replaces G14 point dipoles with deterministic finite-segment circular-loop Biot-Savart integration and replaces prescribed uniform current with a solved scalar-potential conduction field.",
        "The conduction solve uses uniform scalar conductivity, full-width ideal electrodes, and insulating side walls; electrode polarization, contact impedance, Hall effects, anisotropy, and fluid-motion-induced electric fields are not modeled.",
        "The loop integral is a converged numerical line-segment approximation, not a full 3D conductor/skin-effect/inductance/driver solution.",
        "Power and mass remain idealized engineering estimates; no coupled thermal or structural qualification is represented.",
        "Passing G15 establishes SIMULATED_ONLY finite-geometry reachability and closed-loop behavior, not laboratory adaptive EM control or operational capability.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG15Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v2.0 must remain SIMULATED_ONLY")
        if not all((self.finite_segment_biot_savart_simulated, self.conduction_potential_solved, self.lorentz_curl_projection_executed, self.g12_loop_executed_through_finite_geometry_map)):
            raise ValueError("G15 report must represent the executed finite-geometry simulation gate")
        prohibited = (
            self.continuous_wire_solution_validated,
            self.mutual_inductance_or_driver_dynamics_modeled,
            self.measured_conductivity_or_contact_impedance_used,
            self.coupled_thermal_state_validated,
            self.full_wave_maxwell_solved,
            self.laboratory_validation_performed,
            self.adaptive_em_control_validated,
            self.plasma_validated,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v2.0 cannot promote unsupported physical or hardware claims")
        return self


def _coordinate(index: int, n: int, length: float) -> float:
    return (index / (n - 1) - 0.5) * length


def _coil_center(index: int, geometry: G15Geometry) -> tuple[float, float, float]:
    angle = math.radians(geometry.coil_angular_offset_deg) + 2.0 * math.pi * index / geometry.coil_count
    return (
        geometry.coil_ring_radius_m * math.cos(angle),
        geometry.coil_ring_radius_m * math.sin(angle),
        -geometry.coil_standoff_m,
    )


def _loop_bz_per_amp_at_point(*, x: float, y: float, coil_index: int, geometry: G15Geometry, segments: int | None = None) -> float:
    segments = geometry.coil_segments if segments is None else segments
    if segments < 12:
        raise ValueError("loop discretization requires at least 12 segments")
    cx, cy, cz = _coil_center(coil_index, geometry)
    total = 0.0
    for segment in range(segments):
        theta0 = 2.0 * math.pi * segment / segments
        theta1 = 2.0 * math.pi * (segment + 1) / segments
        p0x = cx + geometry.coil_radius_m * math.cos(theta0)
        p0y = cy + geometry.coil_radius_m * math.sin(theta0)
        p1x = cx + geometry.coil_radius_m * math.cos(theta1)
        p1y = cy + geometry.coil_radius_m * math.sin(theta1)
        dlx = p1x - p0x
        dly = p1y - p0y
        mx = 0.5 * (p0x + p1x)
        my = 0.5 * (p0y + p1y)
        rx = x - mx
        ry = y - my
        rz = -cz
        r2 = rx * rx + ry * ry + rz * rz
        if r2 <= 1e-18:
            raise ValueError("field point lies on a coil segment")
        cross_z = dlx * ry - dly * rx
        total += cross_z / (r2 ** 1.5)
    return MU0_OVER_4PI * geometry.coil_turns * total


def _loop_field_per_amp(*, coil_index: int, geometry: G15Geometry) -> list[list[float]]:
    n = geometry.grid_size
    return [
        [
            _loop_bz_per_amp_at_point(
                x=_coordinate(i, n, geometry.domain_length_m),
                y=_coordinate(j, n, geometry.domain_length_m),
                coil_index=coil_index,
                geometry=geometry,
            )
            for j in range(n)
        ]
        for i in range(n)
    ]


def _exact_on_axis_loop_bz_per_amp(geometry: G15Geometry) -> float:
    z = geometry.coil_standoff_m
    r = geometry.coil_radius_m
    return 2.0 * math.pi * MU0_OVER_4PI * geometry.coil_turns * r * r / ((r * r + z * z) ** 1.5)


def _loop_verification_case(geometry: G15Geometry) -> G15LoopVerificationCase:
    cx, cy, _ = _coil_center(0, geometry)
    exact = _exact_on_axis_loop_bz_per_amp(geometry)
    counts = (24, 48, 96)
    errors = []
    for segments in counts:
        estimate = _loop_bz_per_amp_at_point(x=cx, y=cy, coil_index=0, geometry=geometry, segments=segments)
        errors.append(abs(estimate - exact) / abs(exact))
    return G15LoopVerificationCase(
        segment_counts=counts,
        on_axis_relative_errors=tuple(errors),
        convergence_ratio_24_to_48=errors[0] / max(errors[1], 1e-30),
        convergence_ratio_48_to_96=errors[1] / max(errors[2], 1e-30),
        finest_relative_error=errors[-1],
    )


def _solve_conduction_potential(geometry: G15Geometry, *, tolerance: float = 1e-12, max_iterations: int = 20000):
    n = geometry.grid_size
    voltage = geometry.electrode_voltage_drop_v
    phi = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        phi[i][0] = 0.5 * voltage
        phi[i][n - 1] = -0.5 * voltage
    omega = 1.7
    iterations = 0
    for iteration in range(max_iterations):
        max_delta = 0.0
        for j in range(1, n - 1):
            phi[0][j] = phi[1][j]
            phi[n - 1][j] = phi[n - 2][j]
        for i in range(1, n - 1):
            for j in range(1, n - 1):
                candidate = 0.25 * (phi[i - 1][j] + phi[i + 1][j] + phi[i][j - 1] + phi[i][j + 1])
                updated = phi[i][j] + omega * (candidate - phi[i][j])
                max_delta = max(max_delta, abs(updated - phi[i][j]))
                phi[i][j] = updated
        iterations = iteration + 1
        if max_delta <= tolerance:
            break
    else:
        raise ValueError("G15 conduction potential solve did not converge")
    for j in range(1, n - 1):
        phi[0][j] = phi[1][j]
        phi[n - 1][j] = phi[n - 2][j]
    return phi, iterations


def _derivative_x(field: list[list[float]], i: int, j: int, h: float) -> float:
    n = len(field)
    if i == 0:
        return (field[1][j] - field[0][j]) / h
    if i == n - 1:
        return (field[n - 1][j] - field[n - 2][j]) / h
    return (field[i + 1][j] - field[i - 1][j]) / (2.0 * h)


def _derivative_y(field: list[list[float]], i: int, j: int, h: float) -> float:
    n = len(field)
    if j == 0:
        return (field[i][1] - field[i][0]) / h
    if j == n - 1:
        return (field[i][n - 1] - field[i][n - 2]) / h
    return (field[i][j + 1] - field[i][j - 1]) / (2.0 * h)


def _current_from_potential(phi: list[list[float]], geometry: G15Geometry):
    n = geometry.grid_size
    h = geometry.domain_length_m / (n - 1)
    jx = [[-geometry.conductivity_s_m * _derivative_x(phi, i, j, h) for j in range(n)] for i in range(n)]
    jy = [[-geometry.conductivity_s_m * _derivative_y(phi, i, j, h) for j in range(n)] for i in range(n)]
    return jx, jy


def _conduction_case(geometry: G15Geometry):
    phi, iterations = _solve_conduction_potential(geometry)
    jx, jy = _current_from_potential(phi, geometry)
    n = geometry.grid_size
    h = geometry.domain_length_m / (n - 1)
    laplace_max = 0.0
    for i in range(1, n - 1):
        for j in range(1, n - 1):
            laplace = (phi[i - 1][j] + phi[i + 1][j] + phi[i][j - 1] + phi[i][j + 1] - 4.0 * phi[i][j]) / (h * h)
            laplace_max = max(laplace_max, abs(laplace))
    divergence_max = 0.0
    for i in range(n):
        for j in range(n):
            divergence_max = max(divergence_max, abs(_derivative_x(jx, i, j, h) + _derivative_y(jy, i, j, h)))
    values = [jy[i][j] for i in range(n) for j in range(n)]
    mean_jy = sum(values) / len(values)
    std_jy = math.sqrt(sum((value - mean_jy) ** 2 for value in values) / len(values))
    target_jy = geometry.conductivity_s_m * geometry.electrode_voltage_drop_v / geometry.domain_length_m
    return G15ConductionCase(
        iterations=iterations,
        max_laplace_residual_v_m2=laplace_max,
        mean_jy_a_m2=mean_jy,
        jy_relative_std=std_jy / max(abs(mean_jy), 1e-30),
        max_abs_jx_a_m2=max(abs(value) for row in jx for value in row),
        max_abs_current_divergence_a_m3=divergence_max,
        target_uniform_jy_a_m2=target_jy,
        mean_jy_relative_error=abs(mean_jy - target_jy) / abs(target_jy),
    ), jx, jy


def _projection(field: list[list[float]], basis: list[list[float]]) -> float:
    n = len(field)
    numerator = sum(field[i][j] * basis[i][j] for i in range(n) for j in range(n))
    denominator = sum(basis[i][j] ** 2 for i in range(n) for j in range(n))
    if denominator <= 1e-15:
        raise ValueError("degenerate G12 basis")
    return numerator / denominator


def _source_kernel_per_amp(*, coil_index: int, geometry: G15Geometry, jx, jy):
    bz = _loop_field_per_amp(coil_index=coil_index, geometry=geometry)
    n = geometry.grid_size
    h = geometry.domain_length_m / (n - 1)
    source_scale = geometry.reference_velocity_m_s**2 / geometry.domain_length_m**2
    kernel = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dbdx = _derivative_x(bz, i, j, h)
            dbdy = _derivative_y(bz, i, j, h)
            physical = -(jx[i][j] * dbdx + jy[i][j] * dbdy) / geometry.fluid_density_kg_m3
            kernel[i][j] = physical / source_scale
    return kernel, bz


def build_finite_geometry_transfer_matrix(geometry: G15Geometry, *, disabled_coil_index: int | None = None):
    if disabled_coil_index is not None and not 0 <= disabled_coil_index < geometry.coil_count:
        raise ValueError("disabled coil index out of range")
    _, jx, jy = _conduction_case(geometry)
    bases = _basis_fields(geometry.grid_size)
    rows = [[0.0 for _ in range(geometry.coil_count)] for _ in range(3)]
    for coil_index in range(geometry.coil_count):
        if coil_index == disabled_coil_index:
            continue
        kernel, _ = _source_kernel_per_amp(coil_index=coil_index, geometry=geometry, jx=jx, jy=jy)
        for mode in range(3):
            rows[mode][coil_index] = _projection(kernel, bases[mode])
    return tuple(tuple(value for value in row) for row in rows)


def _combined_bz(currents: tuple[float, ...], geometry: G15Geometry):
    n = geometry.grid_size
    total = [[0.0 for _ in range(n)] for _ in range(n)]
    for coil_index, current in enumerate(currents):
        field = _loop_field_per_amp(coil_index=coil_index, geometry=geometry)
        for i in range(n):
            for j in range(n):
                total[i][j] += current * field[i][j]
    return total


def _rms(field):
    n = len(field)
    return math.sqrt(sum(value * value for row in field for value in row) / (n * n))


def _relative_matrix_change(left, right):
    numerator = math.sqrt(sum((left[r][c] - right[r][c]) ** 2 for r in range(3) for c in range(len(left[0]))))
    denominator = math.sqrt(sum(right[r][c] ** 2 for r in range(3) for c in range(len(right[0]))))
    return numerator / max(denominator, 1e-30)


def _coil_properties(geometry: G15Geometry):
    wire_length = geometry.coil_turns * 2.0 * math.pi * geometry.coil_radius_m
    resistance = COPPER_RESISTIVITY_OHM_M * wire_length / geometry.conductor_cross_section_m2
    mass = COPPER_DENSITY_KG_M3 * wire_length * geometry.conductor_cross_section_m2
    return resistance, mass


def _nominal_case(geometry: G15Geometry):
    target = _representative_g12_target()
    matrix = build_finite_geometry_transfer_matrix(geometry)
    currents, realized, residual, saturated = allocate_modal_command(target, matrix=matrix, actuator_limit=geometry.coil_current_limit_a)
    condition, rank = _condition_and_rank(matrix)
    field = _combined_bz(currents, geometry)
    resistance, mass_per_coil = _coil_properties(geometry)
    g14 = build_geometry_transfer_matrix(G14Geometry())
    return G15NominalCase(
        target_commands=target,
        realized_commands=realized,
        coil_currents_a=currents,
        effective_rank=rank,
        transfer_condition_number=condition,
        relative_modal_residual=residual,
        max_abs_coil_current_a=max(abs(value) for value in currents),
        saturated_coils=saturated,
        max_abs_bz_t=max(abs(value) for row in field for value in row),
        rms_bz_t=_rms(field),
        total_joule_power_w=sum(value * value * resistance for value in currents),
        total_copper_mass_kg=geometry.coil_count * mass_per_coil,
        relative_transfer_change_vs_g14=_relative_matrix_change(matrix, g14),
    )


def _fault_case(geometry: G15Geometry):
    target = _representative_g12_target()
    worst = (-1.0, 0, 0.0, 1.0)
    all_rank_three = True
    for disabled in range(geometry.coil_count):
        matrix = build_finite_geometry_transfer_matrix(geometry, disabled_coil_index=disabled)
        currents, _, residual, _ = allocate_modal_command(target, matrix=matrix, actuator_limit=geometry.coil_current_limit_a)
        condition, rank = _condition_and_rank(matrix)
        all_rank_three = all_rank_three and rank == 3
        candidate = (residual, disabled, max(abs(value) for value in currents), condition)
        if candidate[0] > worst[0]:
            worst = candidate
    return G15FaultCase(
        worst_disabled_coil_index=worst[1],
        worst_relative_modal_residual=worst[0],
        worst_max_abs_current_a=worst[2],
        worst_condition_number=worst[3],
        all_single_coil_faults_rank_three=all_rank_three,
    )


def _closed_loop_case(geometry: G15Geometry):
    n = geometry.grid_size
    viscosity = 0.01
    resistivity = 0.015
    dt = 0.0005
    final_time = 0.05
    gain = 4.0
    command_limit = 2.0
    omega0, a0 = _mixed_initial(n)
    baseline_w, _, _, _, _, _, _, _ = integrate_feedback_control(initial_vorticity=omega0, initial_magnetic_potential=a0, viscosity=viscosity, resistivity=resistivity, dt=dt, final_time=final_time, gain=0.0, command_limit=command_limit, feedback_sign=-1.0)
    ideal_w, _, _, _, _, _, _, _ = integrate_feedback_control(initial_vorticity=omega0, initial_magnetic_potential=a0, viscosity=viscosity, resistivity=resistivity, dt=dt, final_time=final_time, gain=gain, command_limit=command_limit, feedback_sign=-1.0)
    matrix = build_finite_geometry_transfer_matrix(geometry)
    realized_w, realized_a, _, effort, max_current, max_residual = _integrate_forward_mapped_feedback(initial_vorticity=omega0, initial_magnetic_potential=a0, viscosity=viscosity, resistivity=resistivity, dt=dt, final_time=final_time, gain=gain, command_limit=command_limit, actuator_limit=geometry.coil_current_limit_a, matrix=matrix)
    baseline_target = _target_modal_energy(baseline_w)
    ideal_target = _target_modal_energy(ideal_w)
    realized_target = _target_modal_energy(realized_w)
    baseline_enstrophy = _enstrophy(baseline_w)
    realized_enstrophy = _enstrophy(realized_w)
    u, v, _ = _velocity_and_streamfunction(realized_w)
    bx, by, _ = _magnetic_state(realized_a)
    return G15ClosedLoopCase(
        target_modal_energy_baseline_final=baseline_target,
        target_modal_energy_ideal_g12_final=ideal_target,
        target_modal_energy_finite_geometry_final=realized_target,
        target_modal_energy_reduction_fraction=(baseline_target - realized_target) / max(baseline_target, 1e-15),
        finite_geometry_vs_ideal_relative_gap=abs(realized_target - ideal_target) / max(abs(ideal_target), 1e-15),
        baseline_enstrophy_final=baseline_enstrophy,
        finite_geometry_enstrophy_final=realized_enstrophy,
        enstrophy_reduction_fraction=(baseline_enstrophy - realized_enstrophy) / max(baseline_enstrophy, 1e-15),
        coil_current_effort_a2_s=effort,
        max_abs_coil_current_a=max_current,
        max_modal_tracking_residual=max_residual,
        velocity_divergence_rms=_spectral_divergence_rms(u, v),
        magnetic_divergence_rms=_spectral_divergence_rms(bx, by),
    )


def run_nsb_g15_benchmark(*, loop_error_limit: float = 5e-4, conduction_relative_error_limit: float = 2e-4, conduction_uniformity_limit: float = 2e-3, condition_number_limit: float = 10.0, nominal_residual_limit: float = 1e-3, fault_residual_limit: float = 1e-2, target_reduction_floor: float = 0.12, ideal_gap_limit: float = 0.05, divergence_limit: float = 1e-10) -> NSBG15Report:
    geometry = G15Geometry()
    conduction, _, _ = _conduction_case(geometry)
    loop = _loop_verification_case(geometry)
    nominal = _nominal_case(geometry)
    fault = _fault_case(geometry)
    closed = _closed_loop_case(geometry)
    loop_pass = loop.finest_relative_error <= loop_error_limit and loop.convergence_ratio_48_to_96 > 3.5
    conduction_pass = conduction.mean_jy_relative_error <= conduction_relative_error_limit and conduction.jy_relative_std <= conduction_uniformity_limit
    nominal_pass = nominal.effective_rank == 3 and nominal.transfer_condition_number <= condition_number_limit and nominal.relative_modal_residual <= nominal_residual_limit and nominal.max_abs_coil_current_a <= geometry.coil_current_limit_a + 1e-12 and nominal.saturated_coils == 0
    fault_pass = fault.all_single_coil_faults_rank_three and fault.worst_relative_modal_residual <= fault_residual_limit and fault.worst_max_abs_current_a <= geometry.coil_current_limit_a + 1e-12 and fault.worst_condition_number <= 15.0
    closed_pass = closed.target_modal_energy_reduction_fraction >= target_reduction_floor and closed.finite_geometry_vs_ideal_relative_gap <= ideal_gap_limit and closed.max_abs_coil_current_a <= geometry.coil_current_limit_a + 1e-12 and closed.max_modal_tracking_residual <= nominal_residual_limit and max(closed.velocity_divergence_rms, closed.magnetic_divergence_rms) <= divergence_limit
    acceptance_pass = all((loop_pass, conduction_pass, nominal_pass, fault_pass, closed_pass))
    report = NSBG15Report(
        geometry=geometry,
        conduction_case=conduction,
        loop_verification_case=loop,
        nominal_case=nominal,
        fault_case=fault,
        closed_loop_case=closed,
        acceptance=G15AcceptanceSummary(
            loop_error_limit=loop_error_limit,
            conduction_relative_error_limit=conduction_relative_error_limit,
            conduction_uniformity_limit=conduction_uniformity_limit,
            condition_number_limit=condition_number_limit,
            nominal_residual_limit=nominal_residual_limit,
            fault_residual_limit=fault_residual_limit,
            target_reduction_floor=target_reduction_floor,
            ideal_gap_limit=ideal_gap_limit,
            divergence_limit=divergence_limit,
            loop_verification_pass=loop_pass,
            conduction_solve_pass=conduction_pass,
            nominal_reachability_pass=nominal_pass,
            single_fault_pass=fault_pass,
            closed_loop_pass=closed_pass,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g15_report(report: NSBG15Report) -> bool:
    return report.report_digest == canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
