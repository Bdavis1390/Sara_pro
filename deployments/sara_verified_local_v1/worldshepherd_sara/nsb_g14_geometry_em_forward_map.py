from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .nsb_g3_solver import _spectral_divergence_rms, _velocity_and_streamfunction
from .nsb_g10_nonlinear_mhd import _magnetic_state, _mixed_initial
from .nsb_g12_adaptive_lorentz_control import (
    _basis_fields,
    _enstrophy,
    _target_modal_energy,
    integrate_feedback_control,
)
from .nsb_g13_actuator_forward_map import (
    _condition_and_rank,
    _integrate_forward_mapped_feedback,
    _representative_g12_target,
    allocate_modal_command,
)
from .qualification import CapabilityStatus, canonical_digest


MU0_OVER_4PI = 1e-7
COPPER_RESISTIVITY_OHM_M = 1.68e-8
COPPER_DENSITY_KG_M3 = 8960.0


class G14Geometry(BaseModel):
    grid_size: int = Field(default=16, ge=8)
    domain_length_m: float = Field(default=0.10, gt=0.0)
    reference_velocity_m_s: float = Field(default=0.03, gt=0.0)
    fluid_density_kg_m3: float = Field(default=6400.0, gt=0.0)
    imposed_current_density_x_a_m2: float = 0.0
    imposed_current_density_y_a_m2: float = 5.0e5
    coil_count: int = Field(default=8, ge=4)
    coil_ring_radius_m: float = Field(default=0.070, gt=0.0)
    coil_radius_m: float = Field(default=0.010, gt=0.0)
    coil_turns: int = Field(default=200, ge=1)
    coil_standoff_m: float = Field(default=0.025, gt=0.0)
    coil_angular_offset_deg: float = 22.5
    conductor_cross_section_m2: float = Field(default=1.0e-6, gt=0.0)
    coil_current_limit_a: float = Field(default=3.5, gt=0.0)


class G14NominalCase(BaseModel):
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
    coil_resistance_ohm: float = Field(ge=0.0)
    total_joule_power_w: float = Field(ge=0.0)
    total_copper_mass_kg: float = Field(ge=0.0)


class G14GeometryMismatchCase(BaseModel):
    nominal_standoff_m: float = Field(gt=0.0)
    perturbed_standoff_m: float = Field(gt=0.0)
    uncalibrated_relative_modal_residual: float = Field(ge=0.0)
    recalibrated_relative_modal_residual: float = Field(ge=0.0)
    recalibrated_max_abs_current_a: float = Field(ge=0.0)
    recalibrated_condition_number: float = Field(ge=1.0)


class G14FaultCase(BaseModel):
    worst_disabled_coil_index: int = Field(ge=0)
    worst_relative_modal_residual: float = Field(ge=0.0)
    worst_max_abs_current_a: float = Field(ge=0.0)
    worst_condition_number: float = Field(ge=1.0)
    all_single_coil_faults_rank_three: bool


class G14SaturationCase(BaseModel):
    target_scale: float = Field(gt=1.0)
    relative_modal_residual: float = Field(ge=0.0)
    saturated_coils: int = Field(ge=0)
    correctly_flagged_unreachable: bool


class G14ClosedLoopCase(BaseModel):
    target_modal_energy_baseline_final: float = Field(ge=0.0)
    target_modal_energy_ideal_g12_final: float = Field(ge=0.0)
    target_modal_energy_geometry_map_final: float = Field(ge=0.0)
    target_modal_energy_reduction_fraction: float
    geometry_map_vs_ideal_relative_gap: float = Field(ge=0.0)
    baseline_enstrophy_final: float = Field(ge=0.0)
    geometry_map_enstrophy_final: float = Field(ge=0.0)
    enstrophy_reduction_fraction: float
    coil_current_effort_a2_s: float = Field(ge=0.0)
    max_abs_coil_current_a: float = Field(ge=0.0)
    max_modal_tracking_residual: float = Field(ge=0.0)
    velocity_divergence_rms: float = Field(ge=0.0)
    magnetic_divergence_rms: float = Field(ge=0.0)


class G14AcceptanceSummary(BaseModel):
    condition_number_limit: float = Field(gt=1.0)
    nominal_residual_limit: float = Field(gt=0.0)
    geometry_recalibrated_residual_limit: float = Field(gt=0.0)
    single_fault_residual_limit: float = Field(gt=0.0)
    target_reduction_floor: float = Field(gt=0.0)
    ideal_gap_limit: float = Field(gt=0.0)
    divergence_limit: float = Field(gt=0.0)
    nominal_geometry_pass: bool
    geometry_mismatch_recalibration_pass: bool
    single_fault_pass: bool
    saturation_detection_pass: bool
    closed_loop_pass: bool
    acceptance_pass: bool


class NSBG14Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G14-001"
    benchmark_version: str = "1.9"
    formulation: str = "geometry-specific quasi-static magnetic-dipole coil/electrode forward-map projected into the G12 Lorentz-curl control basis"
    geometry: G14Geometry
    nominal_case: G14NominalCase
    geometry_mismatch_case: G14GeometryMismatchCase
    fault_case: G14FaultCase
    saturation_case: G14SaturationCase
    closed_loop_case: G14ClosedLoopCase
    acceptance: G14AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    geometry_specific_em_forward_map_simulated: bool = True
    analytic_magnetostatic_dipole_field_used: bool = True
    current_density_lorentz_curl_projection_executed: bool = True
    g12_loop_executed_through_geometry_map: bool = True
    finite_coil_biot_savart_solved: bool = False
    full_wave_maxwell_solved: bool = False
    measured_material_or_device_transfer_used: bool = False
    coil_thermal_state_validated: bool = False
    laboratory_validation_performed: bool = False
    adaptive_em_control_validated: bool = False
    plasma_validated: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G14 replaces the synthetic G13 transfer matrix with a geometry-specific quasi-static magnetic dipole approximation for eight circular coils plus a prescribed uniform in-plane conduction-current density.",
        "The coil model uses the far-field magnetic-dipole approximation m=N*I*pi*r^2, not an exact finite-wire Biot-Savart integration, mutual inductance model, ferromagnetic core model, or full-wave Maxwell solver.",
        "The conductive-medium current density is prescribed rather than solved from electrodes, contact impedance, Hall response, plasma sheath physics, or measured conductivity fields.",
        "Joule power and copper mass are engineering estimates from idealized copper geometry; they are not thermal or hardware qualification results.",
        "Passing G14 establishes only SIMULATED_ONLY geometry-conditioned modal reachability and closed-loop behavior for this bounded reference model.",
        "G14 does not establish laboratory adaptive EM control, plasma control, propulsion, shielding, stealth, cloaking, or operational capability.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG14Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.9 must remain SIMULATED_ONLY")
        if not all(
            (
                self.geometry_specific_em_forward_map_simulated,
                self.analytic_magnetostatic_dipole_field_used,
                self.current_density_lorentz_curl_projection_executed,
                self.g12_loop_executed_through_geometry_map,
            )
        ):
            raise ValueError("G14 report must represent the executed geometry-specific simulation gate")
        prohibited = (
            self.finite_coil_biot_savart_solved,
            self.full_wave_maxwell_solved,
            self.measured_material_or_device_transfer_used,
            self.coil_thermal_state_validated,
            self.laboratory_validation_performed,
            self.adaptive_em_control_validated,
            self.plasma_validated,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v1.9 cannot promote unsupported physical or hardware claims")
        return self


def _grid_coordinate(index: int, n: int, length_m: float) -> float:
    return (index / n - 0.5) * length_m


def _coil_center(index: int, geometry: G14Geometry) -> tuple[float, float]:
    angle = math.radians(geometry.coil_angular_offset_deg) + 2.0 * math.pi * index / geometry.coil_count
    return (
        geometry.coil_ring_radius_m * math.cos(angle),
        geometry.coil_ring_radius_m * math.sin(angle),
    )


def _dipole_moment_per_amp(geometry: G14Geometry) -> float:
    return geometry.coil_turns * math.pi * geometry.coil_radius_m**2


def _coil_bz_and_derivatives_per_amp(
    *,
    coil_index: int,
    geometry: G14Geometry,
) -> tuple[list[list[float]], list[list[float]], list[list[float]]]:
    n = geometry.grid_size
    cx, cy = _coil_center(coil_index, geometry)
    z = -geometry.coil_standoff_m
    magnetic_moment_per_amp = _dipole_moment_per_amp(geometry)
    coefficient = MU0_OVER_4PI * magnetic_moment_per_amp

    bz: list[list[float]] = []
    dbdx: list[list[float]] = []
    dbdy: list[list[float]] = []
    for i in range(n):
        x = _grid_coordinate(i, n, geometry.domain_length_m)
        bz_row: list[float] = []
        dx_row: list[float] = []
        dy_row: list[float] = []
        for j in range(n):
            y = _grid_coordinate(j, n, geometry.domain_length_m)
            dx = x - cx
            dy = y - cy
            s = dx * dx + dy * dy + z * z
            if s <= 1e-18:
                raise ValueError("coil dipole coincides with a control-grid point")
            s32 = s ** 1.5
            s52 = s ** 2.5
            s72 = s ** 3.5
            b = coefficient * (3.0 * z * z / s52 - 1.0 / s32)
            derivative_factor = 3.0 * coefficient * (s - 5.0 * z * z) / s72
            bz_row.append(b)
            dx_row.append(derivative_factor * dx)
            dy_row.append(derivative_factor * dy)
        bz.append(bz_row)
        dbdx.append(dx_row)
        dbdy.append(dy_row)
    return bz, dbdx, dbdy


def _lorentz_curl_kernel_per_amp(*, coil_index: int, geometry: G14Geometry) -> tuple[list[list[float]], list[list[float]]]:
    bz, dbdx, dbdy = _coil_bz_and_derivatives_per_amp(coil_index=coil_index, geometry=geometry)
    source_scale = geometry.reference_velocity_m_s**2 / geometry.domain_length_m**2
    if source_scale <= 0.0:
        raise ValueError("invalid nondimensional source scale")
    n = geometry.grid_size
    kernel: list[list[float]] = []
    for i in range(n):
        row: list[float] = []
        for j in range(n):
            physical_curl = -(
                geometry.imposed_current_density_x_a_m2 * dbdx[i][j]
                + geometry.imposed_current_density_y_a_m2 * dbdy[i][j]
            ) / geometry.fluid_density_kg_m3
            row.append(physical_curl / source_scale)
        kernel.append(row)
    return kernel, bz


def _projection(field: list[list[float]], basis: list[list[float]]) -> float:
    n = len(field)
    numerator = sum(field[i][j] * basis[i][j] for i in range(n) for j in range(n))
    denominator = sum(basis[i][j] ** 2 for i in range(n) for j in range(n))
    if denominator <= 1e-15:
        raise ValueError("degenerate G12 basis")
    return numerator / denominator


def build_geometry_transfer_matrix(
    geometry: G14Geometry,
    *,
    disabled_coil_index: int | None = None,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    if disabled_coil_index is not None and not 0 <= disabled_coil_index < geometry.coil_count:
        raise ValueError("disabled coil index out of range")
    bases = _basis_fields(geometry.grid_size)
    rows = [[0.0 for _ in range(geometry.coil_count)] for _ in range(3)]
    for coil_index in range(geometry.coil_count):
        if coil_index == disabled_coil_index:
            continue
        kernel, _ = _lorentz_curl_kernel_per_amp(coil_index=coil_index, geometry=geometry)
        for mode in range(3):
            rows[mode][coil_index] = _projection(kernel, bases[mode])
    return tuple(tuple(value for value in row) for row in rows)  # type: ignore[return-value]


def _combined_bz(
    currents: tuple[float, ...],
    geometry: G14Geometry,
) -> list[list[float]]:
    n = geometry.grid_size
    total = [[0.0 for _ in range(n)] for _ in range(n)]
    for coil_index, current in enumerate(currents):
        bz, _, _ = _coil_bz_and_derivatives_per_amp(coil_index=coil_index, geometry=geometry)
        for i in range(n):
            for j in range(n):
                total[i][j] += current * bz[i][j]
    return total


def _rms(field: list[list[float]]) -> float:
    n = len(field)
    return math.sqrt(sum(value * value for row in field for value in row) / (n * n))


def _coil_electrical_properties(geometry: G14Geometry) -> tuple[float, float]:
    wire_length = geometry.coil_turns * 2.0 * math.pi * geometry.coil_radius_m
    resistance = COPPER_RESISTIVITY_OHM_M * wire_length / geometry.conductor_cross_section_m2
    mass = COPPER_DENSITY_KG_M3 * wire_length * geometry.conductor_cross_section_m2
    return resistance, mass


def _nominal_case(geometry: G14Geometry) -> G14NominalCase:
    target = _representative_g12_target()
    matrix = build_geometry_transfer_matrix(geometry)
    currents, realized, residual, saturated = allocate_modal_command(
        target,
        matrix=matrix,
        actuator_limit=geometry.coil_current_limit_a,
    )
    condition, rank = _condition_and_rank(matrix)
    field = _combined_bz(currents, geometry)
    resistance, mass_per_coil = _coil_electrical_properties(geometry)
    return G14NominalCase(
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
        coil_resistance_ohm=resistance,
        total_joule_power_w=sum(value * value * resistance for value in currents),
        total_copper_mass_kg=geometry.coil_count * mass_per_coil,
    )


def _geometry_mismatch_case(geometry: G14Geometry) -> G14GeometryMismatchCase:
    target = _representative_g12_target()
    nominal_matrix = build_geometry_transfer_matrix(geometry)
    nominal_currents, _, _, _ = allocate_modal_command(
        target,
        matrix=nominal_matrix,
        actuator_limit=geometry.coil_current_limit_a,
    )
    perturbed = geometry.model_copy(update={"coil_standoff_m": geometry.coil_standoff_m + 0.001})
    actual_matrix = build_geometry_transfer_matrix(perturbed)
    realized = tuple(
        sum(actual_matrix[row][col] * nominal_currents[col] for col in range(geometry.coil_count))
        for row in range(3)
    )
    target_norm = math.sqrt(sum(value * value for value in target))
    uncalibrated = math.sqrt(sum((realized[i] - target[i]) ** 2 for i in range(3))) / target_norm
    recalibrated_currents, _, recalibrated_residual, _ = allocate_modal_command(
        target,
        matrix=actual_matrix,
        actuator_limit=geometry.coil_current_limit_a,
    )
    condition, _ = _condition_and_rank(actual_matrix)
    return G14GeometryMismatchCase(
        nominal_standoff_m=geometry.coil_standoff_m,
        perturbed_standoff_m=perturbed.coil_standoff_m,
        uncalibrated_relative_modal_residual=uncalibrated,
        recalibrated_relative_modal_residual=recalibrated_residual,
        recalibrated_max_abs_current_a=max(abs(value) for value in recalibrated_currents),
        recalibrated_condition_number=condition,
    )


def _fault_case(geometry: G14Geometry) -> G14FaultCase:
    target = _representative_g12_target()
    worst = (-1.0, 0, 0.0, 1.0, True)
    all_rank_three = True
    for disabled in range(geometry.coil_count):
        matrix = build_geometry_transfer_matrix(geometry, disabled_coil_index=disabled)
        currents, _, residual, _ = allocate_modal_command(
            target,
            matrix=matrix,
            actuator_limit=geometry.coil_current_limit_a,
        )
        condition, rank = _condition_and_rank(matrix)
        all_rank_three = all_rank_three and rank == 3
        candidate = (
            residual,
            disabled,
            max(abs(value) for value in currents),
            condition,
            rank == 3,
        )
        if candidate[0] > worst[0]:
            worst = candidate
    return G14FaultCase(
        worst_disabled_coil_index=worst[1],
        worst_relative_modal_residual=worst[0],
        worst_max_abs_current_a=worst[2],
        worst_condition_number=worst[3],
        all_single_coil_faults_rank_three=all_rank_three,
    )


def _saturation_case(geometry: G14Geometry) -> G14SaturationCase:
    scale = 3.0
    target = tuple(scale * value for value in _representative_g12_target())
    matrix = build_geometry_transfer_matrix(geometry)
    _, _, residual, saturated = allocate_modal_command(
        target,
        matrix=matrix,
        actuator_limit=geometry.coil_current_limit_a,
    )
    return G14SaturationCase(
        target_scale=scale,
        relative_modal_residual=residual,
        saturated_coils=saturated,
        correctly_flagged_unreachable=residual > 0.05 and saturated > 0,
    )


def _closed_loop_case(geometry: G14Geometry) -> G14ClosedLoopCase:
    n = geometry.grid_size
    viscosity = 0.01
    resistivity = 0.015
    dt = 0.0005
    final_time = 0.05
    feedback_gain = 4.0
    command_limit = 2.0
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
    matrix = build_geometry_transfer_matrix(geometry)
    realized_w, realized_a, _, effort, max_current, max_residual = _integrate_forward_mapped_feedback(
        initial_vorticity=omega0,
        initial_magnetic_potential=a0,
        viscosity=viscosity,
        resistivity=resistivity,
        dt=dt,
        final_time=final_time,
        gain=feedback_gain,
        command_limit=command_limit,
        actuator_limit=geometry.coil_current_limit_a,
        matrix=matrix,
    )

    baseline_target = _target_modal_energy(baseline_w)
    ideal_target = _target_modal_energy(ideal_w)
    realized_target = _target_modal_energy(realized_w)
    baseline_enstrophy = _enstrophy(baseline_w)
    realized_enstrophy = _enstrophy(realized_w)
    u, v, _ = _velocity_and_streamfunction(realized_w)
    bx, by, _ = _magnetic_state(realized_a)

    return G14ClosedLoopCase(
        target_modal_energy_baseline_final=baseline_target,
        target_modal_energy_ideal_g12_final=ideal_target,
        target_modal_energy_geometry_map_final=realized_target,
        target_modal_energy_reduction_fraction=(baseline_target - realized_target) / max(baseline_target, 1e-15),
        geometry_map_vs_ideal_relative_gap=abs(realized_target - ideal_target) / max(abs(ideal_target), 1e-15),
        baseline_enstrophy_final=baseline_enstrophy,
        geometry_map_enstrophy_final=realized_enstrophy,
        enstrophy_reduction_fraction=(baseline_enstrophy - realized_enstrophy) / max(baseline_enstrophy, 1e-15),
        coil_current_effort_a2_s=effort,
        max_abs_coil_current_a=max_current,
        max_modal_tracking_residual=max_residual,
        velocity_divergence_rms=_spectral_divergence_rms(u, v),
        magnetic_divergence_rms=_spectral_divergence_rms(bx, by),
    )


def run_nsb_g14_benchmark(
    *,
    condition_number_limit: float = 8.0,
    nominal_residual_limit: float = 5e-4,
    geometry_recalibrated_residual_limit: float = 5e-4,
    single_fault_residual_limit: float = 5e-3,
    target_reduction_floor: float = 0.15,
    ideal_gap_limit: float = 0.02,
    divergence_limit: float = 1e-10,
) -> NSBG14Report:
    geometry = G14Geometry()
    nominal = _nominal_case(geometry)
    mismatch = _geometry_mismatch_case(geometry)
    fault = _fault_case(geometry)
    saturation = _saturation_case(geometry)
    closed = _closed_loop_case(geometry)

    nominal_pass = (
        nominal.effective_rank == 3
        and nominal.transfer_condition_number <= condition_number_limit
        and nominal.relative_modal_residual <= nominal_residual_limit
        and nominal.max_abs_coil_current_a <= geometry.coil_current_limit_a + 1e-12
        and nominal.saturated_coils == 0
        and nominal.total_joule_power_w > 0.0
        and nominal.total_copper_mass_kg > 0.0
    )
    mismatch_pass = (
        mismatch.recalibrated_relative_modal_residual <= geometry_recalibrated_residual_limit
        and mismatch.recalibrated_relative_modal_residual < mismatch.uncalibrated_relative_modal_residual
        and mismatch.recalibrated_max_abs_current_a <= geometry.coil_current_limit_a + 1e-12
        and mismatch.recalibrated_condition_number <= condition_number_limit
    )
    fault_pass = (
        fault.all_single_coil_faults_rank_three
        and fault.worst_relative_modal_residual <= single_fault_residual_limit
        and fault.worst_max_abs_current_a <= geometry.coil_current_limit_a + 1e-12
        and fault.worst_condition_number <= 12.0
    )
    saturation_pass = saturation.correctly_flagged_unreachable
    closed_pass = (
        closed.target_modal_energy_reduction_fraction >= target_reduction_floor
        and closed.geometry_map_vs_ideal_relative_gap <= ideal_gap_limit
        and closed.max_abs_coil_current_a <= geometry.coil_current_limit_a + 1e-12
        and closed.coil_current_effort_a2_s > 0.0
        and closed.max_modal_tracking_residual <= nominal_residual_limit
        and max(closed.velocity_divergence_rms, closed.magnetic_divergence_rms) <= divergence_limit
    )
    acceptance_pass = all((nominal_pass, mismatch_pass, fault_pass, saturation_pass, closed_pass))

    report = NSBG14Report(
        geometry=geometry,
        nominal_case=nominal,
        geometry_mismatch_case=mismatch,
        fault_case=fault,
        saturation_case=saturation,
        closed_loop_case=closed,
        acceptance=G14AcceptanceSummary(
            condition_number_limit=condition_number_limit,
            nominal_residual_limit=nominal_residual_limit,
            geometry_recalibrated_residual_limit=geometry_recalibrated_residual_limit,
            single_fault_residual_limit=single_fault_residual_limit,
            target_reduction_floor=target_reduction_floor,
            ideal_gap_limit=ideal_gap_limit,
            divergence_limit=divergence_limit,
            nominal_geometry_pass=nominal_pass,
            geometry_mismatch_recalibration_pass=mismatch_pass,
            single_fault_pass=fault_pass,
            saturation_detection_pass=saturation_pass,
            closed_loop_pass=closed_pass,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g14_report(report: NSBG14Report) -> bool:
    return report.report_digest == canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
