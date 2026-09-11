from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .nsb_g3_solver import _spectral_divergence_rms, _velocity_and_streamfunction
from .nsb_g10_nonlinear_mhd import _magnetic_state, _mixed_initial
from .nsb_g12_adaptive_lorentz_control import (
    _commands,
    _controlled_midpoint_step,
    _enstrophy,
    _source_from_commands,
    _target_modal_energy,
    integrate_feedback_control,
)
from .nsb_g13_actuator_forward_map import _representative_g12_target, allocate_modal_command
from .nsb_g15_finite_geometry_em import (
    COPPER_RESISTIVITY_OHM_M,
    G15Geometry,
    _coil_center,
    _coil_properties,
    build_finite_geometry_transfer_matrix,
)
from .qualification import CapabilityStatus, canonical_digest

MU0 = 4.0 * math.pi * 1.0e-7
COPPER_ALPHA_PER_K = 0.00393
COPPER_SPECIFIC_HEAT_J_KG_K = 385.0


class G16DriverConfig(BaseModel):
    driver_voltage_limit_v: float = Field(default=8.0, gt=0.0)
    current_limit_a: float = Field(default=3.5, gt=0.0)
    current_feedback_gain_v_per_a: float = Field(default=2.5, gt=0.0)
    ambient_temperature_k: float = Field(default=293.15, gt=0.0)
    thermal_limit_k: float = Field(default=353.15, gt=0.0)
    convection_coefficient_w_m2_k: float = Field(default=8.0, gt=0.0)
    electrical_substeps_per_fluid_step: int = Field(default=5, ge=1)
    command_latency_s: float = Field(default=0.0005, ge=0.0)
    driver_efficiency: float = Field(default=0.90, gt=0.0, le=1.0)


class G16CircuitCase(BaseModel):
    self_inductance_h: float = Field(gt=0.0)
    base_resistance_ohm: float = Field(gt=0.0)
    max_abs_mutual_inductance_h: float = Field(ge=0.0)
    max_mutual_to_self_ratio: float = Field(ge=0.0)
    inductance_matrix_condition_inf: float = Field(ge=1.0)
    electrical_time_constant_s: float = Field(gt=0.0)
    closed_loop_electrical_time_constant_s: float = Field(gt=0.0)


class G16StepResponseCase(BaseModel):
    target_currents_a: tuple[float, ...]
    final_currents_a: tuple[float, ...]
    final_relative_current_error: float = Field(ge=0.0)
    settling_time_s: float | None = Field(default=None, ge=0.0)
    max_abs_voltage_v: float = Field(ge=0.0)
    max_abs_current_a: float = Field(ge=0.0)
    peak_temperature_k: float = Field(gt=0.0)
    joule_energy_j: float = Field(ge=0.0)
    driver_input_energy_j: float = Field(ge=0.0)
    voltage_saturated_steps: int = Field(ge=0)


class G16ThermalCase(BaseModel):
    dwell_time_s: float = Field(gt=0.0)
    hold_current_a: float = Field(gt=0.0)
    peak_temperature_k: float = Field(gt=0.0)
    temperature_rise_k: float = Field(ge=0.0)
    final_resistance_ratio: float = Field(ge=1.0)
    total_joule_energy_j: float = Field(ge=0.0)
    thermal_limit_k: float = Field(gt=0.0)


class G16BandwidthCase(BaseModel):
    frequency_hz: float = Field(gt=0.0)
    target_amplitude_a: float = Field(gt=0.0)
    rms_tracking_error_fraction: float = Field(ge=0.0)
    max_abs_voltage_v: float = Field(ge=0.0)
    correctly_flagged_bandwidth_limited: bool


class G16ClosedLoopCase(BaseModel):
    target_modal_energy_baseline_final: float = Field(ge=0.0)
    target_modal_energy_ideal_g12_final: float = Field(ge=0.0)
    target_modal_energy_dynamic_driver_final: float = Field(ge=0.0)
    target_modal_energy_reduction_fraction: float
    dynamic_driver_vs_ideal_relative_gap: float = Field(ge=0.0)
    baseline_enstrophy_final: float = Field(ge=0.0)
    dynamic_driver_enstrophy_final: float = Field(ge=0.0)
    enstrophy_reduction_fraction: float
    max_abs_current_a: float = Field(ge=0.0)
    max_abs_voltage_v: float = Field(ge=0.0)
    peak_temperature_k: float = Field(gt=0.0)
    max_relative_current_tracking_error: float = Field(ge=0.0)
    current_effort_a2_s: float = Field(ge=0.0)
    electrical_energy_j: float = Field(ge=0.0)
    velocity_divergence_rms: float = Field(ge=0.0)
    magnetic_divergence_rms: float = Field(ge=0.0)


class G16AcceptanceSummary(BaseModel):
    inductance_condition_limit: float = Field(gt=1.0)
    step_error_limit: float = Field(gt=0.0)
    step_settling_limit_s: float = Field(gt=0.0)
    target_reduction_floor: float = Field(gt=0.0)
    ideal_gap_limit: float = Field(gt=0.0)
    divergence_limit: float = Field(gt=0.0)
    circuit_pass: bool
    step_response_pass: bool
    thermal_pass: bool
    bandwidth_limit_detection_pass: bool
    closed_loop_pass: bool
    acceptance_pass: bool


class NSBG16Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G16-001"
    benchmark_version: str = "2.1"
    formulation: str = "G15 finite-geometry EM transfer map driven through a bounded coupled RL electrothermal actuator model"
    geometry: G15Geometry
    driver: G16DriverConfig
    circuit_case: G16CircuitCase
    step_response_case: G16StepResponseCase
    thermal_case: G16ThermalCase
    bandwidth_case: G16BandwidthCase
    closed_loop_case: G16ClosedLoopCase
    acceptance: G16AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    finite_geometry_transfer_reused: bool = True
    temperature_dependent_resistance_simulated: bool = True
    inductive_current_dynamics_simulated: bool = True
    mutual_inductance_center_field_approximation_simulated: bool = True
    voltage_saturation_and_current_limits_simulated: bool = True
    coupled_lumped_thermal_state_simulated: bool = True
    command_latency_simulated: bool = True
    measured_lcr_parameters_used: bool = False
    calibrated_thermal_parameters_used: bool = False
    measured_driver_efficiency_used: bool = False
    conductor_skin_or_proximity_effects_modeled: bool = False
    switching_power_electronics_modeled: bool = False
    laboratory_validation_performed: bool = False
    adaptive_em_control_validated: bool = False
    plasma_validated: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G16 adds bounded voltage, inductive current slew, temperature-dependent copper resistance, command latency, current limiting, and lumped thermal evolution to the G15 finite-geometry transfer map.",
        "Self inductance uses an air-core circular-coil engineering approximation; mutual inductance uses receiver-center field times receiver area and is not a full Neumann-integral or measured coupling matrix.",
        "The thermal model is a single lumped copper temperature per coil with idealized natural-convection cooling; winding insulation, potting, core materials, contact thermal resistance, radiation, and structural hot spots are not resolved.",
        "The driver is an averaged voltage source with proportional current feedback, not a switching converter, EMI model, gate-drive model, or calibrated power stage.",
        "Passing G16 establishes only SIMULATED_ONLY circuit/thermal reachability and dynamic closed-loop behavior; it does not establish laboratory adaptive EM control, plasma capability, propulsion, shielding, or operational performance.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG16Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v2.1 must remain SIMULATED_ONLY")
        required = (
            self.finite_geometry_transfer_reused,
            self.temperature_dependent_resistance_simulated,
            self.inductive_current_dynamics_simulated,
            self.mutual_inductance_center_field_approximation_simulated,
            self.voltage_saturation_and_current_limits_simulated,
            self.coupled_lumped_thermal_state_simulated,
            self.command_latency_simulated,
        )
        if not all(required):
            raise ValueError("G16 report must represent the executed electrothermal driver gate")
        prohibited = (
            self.measured_lcr_parameters_used,
            self.calibrated_thermal_parameters_used,
            self.measured_driver_efficiency_used,
            self.conductor_skin_or_proximity_effects_modeled,
            self.switching_power_electronics_modeled,
            self.laboratory_validation_performed,
            self.adaptive_em_control_validated,
            self.plasma_validated,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v2.1 cannot promote unsupported measured, hardware, or operational claims")
        return self


def _wire_radius_m(geometry: G15Geometry) -> float:
    return math.sqrt(geometry.conductor_cross_section_m2 / math.pi)


def _self_inductance_h(geometry: G15Geometry) -> float:
    wire_radius = _wire_radius_m(geometry)
    argument = 8.0 * geometry.coil_radius_m / wire_radius
    if argument <= math.exp(2.0):
        raise ValueError("G16 self-inductance approximation outside its intended thin-wire regime")
    return MU0 * geometry.coil_turns**2 * geometry.coil_radius_m * (math.log(argument) - 2.0)


def _loop_bz_3d_per_amp(*, x: float, y: float, z: float, coil_index: int, geometry: G15Geometry) -> float:
    cx, cy, cz = _coil_center(coil_index, geometry)
    total = 0.0
    segments = geometry.coil_segments
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
        rz = z - cz
        r2 = rx * rx + ry * ry + rz * rz
        if r2 <= 1e-18:
            raise ValueError("mutual-inductance sample lies on source coil")
        total += (dlx * ry - dly * rx) / (r2 ** 1.5)
    return 1.0e-7 * geometry.coil_turns * total


def _inductance_matrix(geometry: G15Geometry):
    count = geometry.coil_count
    self_l = _self_inductance_h(geometry)
    area = math.pi * geometry.coil_radius_m**2
    matrix = [[0.0 for _ in range(count)] for _ in range(count)]
    for i in range(count):
        matrix[i][i] = self_l
    for i in range(count):
        xi, yi, zi = _coil_center(i, geometry)
        for j in range(i + 1, count):
            xj, yj, zj = _coil_center(j, geometry)
            bij = _loop_bz_3d_per_amp(x=xj, y=yj, z=zj, coil_index=i, geometry=geometry)
            bji = _loop_bz_3d_per_amp(x=xi, y=yi, z=zi, coil_index=j, geometry=geometry)
            mutual = 0.5 * (bij + bji) * area * geometry.coil_turns
            matrix[i][j] = mutual
            matrix[j][i] = mutual
    return tuple(tuple(value for value in row) for row in matrix)


def _invert_matrix(matrix):
    n = len(matrix)
    augmented = [list(matrix[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) <= 1e-18:
            raise ValueError("singular G16 circuit matrix")
        if pivot != col:
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        scale = augmented[col][col]
        augmented[col] = [value / scale for value in augmented[col]]
        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            if factor == 0.0:
                continue
            augmented[row] = [augmented[row][k] - factor * augmented[col][k] for k in range(2 * n)]
    return tuple(tuple(augmented[i][n + j] for j in range(n)) for i in range(n))


def _matvec(matrix, vector):
    return tuple(sum(matrix[i][j] * vector[j] for j in range(len(vector))) for i in range(len(matrix)))


def _condition_inf(matrix, inverse) -> float:
    norm = max(sum(abs(value) for value in row) for row in matrix)
    inv_norm = max(sum(abs(value) for value in row) for row in inverse)
    return norm * inv_norm


def _resistance_at_temperature(base_resistance: float, temperature_k: float, ambient_k: float) -> float:
    return base_resistance * (1.0 + COPPER_ALPHA_PER_K * (temperature_k - ambient_k))


def _thermal_area_per_coil(geometry: G15Geometry) -> float:
    wire_length = geometry.coil_turns * 2.0 * math.pi * geometry.coil_radius_m
    return 2.0 * math.pi * _wire_radius_m(geometry) * wire_length


def _relative_error(actual, target) -> float:
    numerator = math.sqrt(sum((actual[i] - target[i]) ** 2 for i in range(len(target))))
    denominator = math.sqrt(sum(value * value for value in target))
    return numerator / max(denominator, 1e-15)


def _driver_step(*, currents, temperatures, targets, dt: float, geometry: G15Geometry, driver: G16DriverConfig, inverse_l, base_resistance: float, mass_per_coil: float):
    resistances = tuple(_resistance_at_temperature(base_resistance, temperatures[i], driver.ambient_temperature_k) for i in range(geometry.coil_count))
    raw_voltages = tuple(
        resistances[i] * targets[i] + driver.current_feedback_gain_v_per_a * (targets[i] - currents[i])
        for i in range(geometry.coil_count)
    )
    voltages = tuple(max(-driver.driver_voltage_limit_v, min(driver.driver_voltage_limit_v, value)) for value in raw_voltages)
    rhs = tuple(voltages[i] - resistances[i] * currents[i] for i in range(geometry.coil_count))
    derivatives = _matvec(inverse_l, rhs)
    updated_currents = tuple(
        max(-driver.current_limit_a, min(driver.current_limit_a, currents[i] + dt * derivatives[i]))
        for i in range(geometry.coil_count)
    )
    area = _thermal_area_per_coil(geometry)
    thermal_capacity = mass_per_coil * COPPER_SPECIFIC_HEAT_J_KG_K
    updated_temperatures = []
    joule_power = 0.0
    input_power = 0.0
    for i in range(geometry.coil_count):
        resistance = _resistance_at_temperature(base_resistance, temperatures[i], driver.ambient_temperature_k)
        copper_heat = updated_currents[i] ** 2 * resistance
        cooling = driver.convection_coefficient_w_m2_k * area * (temperatures[i] - driver.ambient_temperature_k)
        updated_temperatures.append(temperatures[i] + dt * (copper_heat - cooling) / thermal_capacity)
        joule_power += copper_heat
        input_power += abs(voltages[i] * updated_currents[i]) / driver.driver_efficiency
    saturated = sum(abs(raw_voltages[i]) > driver.driver_voltage_limit_v + 1e-12 for i in range(geometry.coil_count))
    return updated_currents, tuple(updated_temperatures), voltages, saturated, joule_power, input_power


def _circuit_case(geometry: G15Geometry, driver: G16DriverConfig):
    matrix = _inductance_matrix(geometry)
    inverse = _invert_matrix(matrix)
    resistance, _ = _coil_properties(geometry)
    self_l = matrix[0][0]
    mutual = max(abs(matrix[i][j]) for i in range(geometry.coil_count) for j in range(geometry.coil_count) if i != j)
    return G16CircuitCase(
        self_inductance_h=self_l,
        base_resistance_ohm=resistance,
        max_abs_mutual_inductance_h=mutual,
        max_mutual_to_self_ratio=mutual / self_l,
        inductance_matrix_condition_inf=_condition_inf(matrix, inverse),
        electrical_time_constant_s=self_l / resistance,
        closed_loop_electrical_time_constant_s=self_l / (resistance + driver.current_feedback_gain_v_per_a),
    )


def _step_response_case(geometry: G15Geometry, driver: G16DriverConfig):
    matrix = build_finite_geometry_transfer_matrix(geometry)
    target_modes = _representative_g12_target()
    target_currents, _, _, _ = allocate_modal_command(target_modes, matrix=matrix, actuator_limit=driver.current_limit_a)
    inductance = _inductance_matrix(geometry)
    inverse = _invert_matrix(inductance)
    base_resistance, mass_per_coil = _coil_properties(geometry)
    currents = tuple(0.0 for _ in range(geometry.coil_count))
    temperatures = tuple(driver.ambient_temperature_k for _ in range(geometry.coil_count))
    dt = 5.0e-5
    final_time = 0.02
    steps = round(final_time / dt)
    settled_since = None
    settling_time = None
    max_voltage = 0.0
    max_current = 0.0
    peak_temperature = driver.ambient_temperature_k
    joule_energy = 0.0
    input_energy = 0.0
    saturated_steps = 0
    for step in range(steps):
        currents, temperatures, voltages, saturated, joule_power, input_power = _driver_step(
            currents=currents,
            temperatures=temperatures,
            targets=target_currents,
            dt=dt,
            geometry=geometry,
            driver=driver,
            inverse_l=inverse,
            base_resistance=base_resistance,
            mass_per_coil=mass_per_coil,
        )
        time = (step + 1) * dt
        error = _relative_error(currents, target_currents)
        if error <= 0.02:
            if settled_since is None:
                settled_since = time
            if time - settled_since >= 0.001 and settling_time is None:
                settling_time = settled_since
        else:
            settled_since = None
        max_voltage = max(max_voltage, *(abs(value) for value in voltages))
        max_current = max(max_current, *(abs(value) for value in currents))
        peak_temperature = max(peak_temperature, *temperatures)
        joule_energy += dt * joule_power
        input_energy += dt * input_power
        saturated_steps += 1 if saturated else 0
    return G16StepResponseCase(
        target_currents_a=target_currents,
        final_currents_a=currents,
        final_relative_current_error=_relative_error(currents, target_currents),
        settling_time_s=settling_time,
        max_abs_voltage_v=max_voltage,
        max_abs_current_a=max_current,
        peak_temperature_k=peak_temperature,
        joule_energy_j=joule_energy,
        driver_input_energy_j=input_energy,
        voltage_saturated_steps=saturated_steps,
    )


def _thermal_case(geometry: G15Geometry, driver: G16DriverConfig):
    inductance = _inductance_matrix(geometry)
    inverse = _invert_matrix(inductance)
    base_resistance, mass_per_coil = _coil_properties(geometry)
    hold_current = 0.90 * driver.current_limit_a
    targets = tuple(hold_current for _ in range(geometry.coil_count))
    currents = tuple(0.0 for _ in range(geometry.coil_count))
    temperatures = tuple(driver.ambient_temperature_k for _ in range(geometry.coil_count))
    dt = 0.02
    dwell = 60.0
    peak = driver.ambient_temperature_k
    joule_energy = 0.0
    for _ in range(round(dwell / dt)):
        currents, temperatures, _, _, joule_power, _ = _driver_step(
            currents=currents,
            temperatures=temperatures,
            targets=targets,
            dt=dt,
            geometry=geometry,
            driver=driver,
            inverse_l=inverse,
            base_resistance=base_resistance,
            mass_per_coil=mass_per_coil,
        )
        peak = max(peak, *temperatures)
        joule_energy += dt * joule_power
    final_resistance = max(_resistance_at_temperature(base_resistance, value, driver.ambient_temperature_k) for value in temperatures)
    return G16ThermalCase(
        dwell_time_s=dwell,
        hold_current_a=hold_current,
        peak_temperature_k=peak,
        temperature_rise_k=peak - driver.ambient_temperature_k,
        final_resistance_ratio=final_resistance / base_resistance,
        total_joule_energy_j=joule_energy,
        thermal_limit_k=driver.thermal_limit_k,
    )


def _bandwidth_case(geometry: G15Geometry, driver: G16DriverConfig):
    inductance = _inductance_matrix(geometry)
    inverse = _invert_matrix(inductance)
    base_resistance, mass_per_coil = _coil_properties(geometry)
    currents = tuple(0.0 for _ in range(geometry.coil_count))
    temperatures = tuple(driver.ambient_temperature_k for _ in range(geometry.coil_count))
    dt = 2.5e-5
    frequency = 400.0
    amplitude = 0.85 * driver.current_limit_a
    final_time = 0.025
    error_sum = 0.0
    target_sum = 0.0
    max_voltage = 0.0
    for step in range(round(final_time / dt)):
        time = step * dt
        target = amplitude * math.sin(2.0 * math.pi * frequency * time)
        targets = tuple(target if index % 2 == 0 else -target for index in range(geometry.coil_count))
        currents, temperatures, voltages, _, _, _ = _driver_step(
            currents=currents,
            temperatures=temperatures,
            targets=targets,
            dt=dt,
            geometry=geometry,
            driver=driver,
            inverse_l=inverse,
            base_resistance=base_resistance,
            mass_per_coil=mass_per_coil,
        )
        error_sum += sum((currents[i] - targets[i]) ** 2 for i in range(geometry.coil_count))
        target_sum += sum(value * value for value in targets)
        max_voltage = max(max_voltage, *(abs(value) for value in voltages))
    rms_fraction = math.sqrt(error_sum / max(target_sum, 1e-30))
    return G16BandwidthCase(
        frequency_hz=frequency,
        target_amplitude_a=amplitude,
        rms_tracking_error_fraction=rms_fraction,
        max_abs_voltage_v=max_voltage,
        correctly_flagged_bandwidth_limited=rms_fraction >= 0.20,
    )


def _dynamic_closed_loop_case(geometry: G15Geometry, driver: G16DriverConfig):
    n = geometry.grid_size
    viscosity = 0.01
    resistivity = 0.015
    fluid_dt = 0.0005
    final_time = 0.05
    gain = 4.0
    command_limit = 2.0
    omega0, a0 = _mixed_initial(n)
    baseline_w, _, _, _, _, _, _, _ = integrate_feedback_control(
        initial_vorticity=omega0,
        initial_magnetic_potential=a0,
        viscosity=viscosity,
        resistivity=resistivity,
        dt=fluid_dt,
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
        dt=fluid_dt,
        final_time=final_time,
        gain=gain,
        command_limit=command_limit,
        feedback_sign=-1.0,
    )
    transfer = build_finite_geometry_transfer_matrix(geometry)
    inductance = _inductance_matrix(geometry)
    inverse = _invert_matrix(inductance)
    base_resistance, mass_per_coil = _coil_properties(geometry)
    omega = [row[:] for row in omega0]
    magnetic = [row[:] for row in a0]
    currents = tuple(0.0 for _ in range(geometry.coil_count))
    temperatures = tuple(driver.ambient_temperature_k for _ in range(geometry.coil_count))
    zero_targets = tuple(0.0 for _ in range(geometry.coil_count))
    delay_steps = max(0, round(driver.command_latency_s / fluid_dt))
    queue = [zero_targets for _ in range(delay_steps + 1)]
    electrical_dt = fluid_dt / driver.electrical_substeps_per_fluid_step
    max_current = 0.0
    max_voltage = 0.0
    peak_temperature = driver.ambient_temperature_k
    max_tracking_error = 0.0
    effort = 0.0
    electrical_energy = 0.0
    steps = round(final_time / fluid_dt)
    for _ in range(steps):
        modal_targets, bases = _commands(omega, gain=gain, command_limit=command_limit, feedback_sign=-1.0)
        target_currents, _, _, _ = allocate_modal_command(tuple(modal_targets), matrix=transfer, actuator_limit=driver.current_limit_a)
        queue.append(target_currents)
        applied_targets = queue.pop(0)
        for _ in range(driver.electrical_substeps_per_fluid_step):
            currents, temperatures, voltages, _, joule_power, input_power = _driver_step(
                currents=currents,
                temperatures=temperatures,
                targets=applied_targets,
                dt=electrical_dt,
                geometry=geometry,
                driver=driver,
                inverse_l=inverse,
                base_resistance=base_resistance,
                mass_per_coil=mass_per_coil,
            )
            max_current = max(max_current, *(abs(value) for value in currents))
            max_voltage = max(max_voltage, *(abs(value) for value in voltages))
            peak_temperature = max(peak_temperature, *temperatures)
            effort += electrical_dt * sum(value * value for value in currents)
            electrical_energy += electrical_dt * input_power
        max_tracking_error = max(max_tracking_error, _relative_error(currents, applied_targets) if any(abs(value) > 1e-12 for value in applied_targets) else 0.0)
        realized_modes = tuple(sum(transfer[mode][coil] * currents[coil] for coil in range(geometry.coil_count)) for mode in range(3))
        source = _source_from_commands(realized_modes, bases)
        omega, magnetic = _controlled_midpoint_step(
            omega,
            magnetic,
            dt=fluid_dt,
            viscosity=viscosity,
            resistivity=resistivity,
            source=source,
        )
    baseline_target = _target_modal_energy(baseline_w)
    ideal_target = _target_modal_energy(ideal_w)
    dynamic_target = _target_modal_energy(omega)
    baseline_enstrophy = _enstrophy(baseline_w)
    dynamic_enstrophy = _enstrophy(omega)
    u, v, _ = _velocity_and_streamfunction(omega)
    bx, by, _ = _magnetic_state(magnetic)
    return G16ClosedLoopCase(
        target_modal_energy_baseline_final=baseline_target,
        target_modal_energy_ideal_g12_final=ideal_target,
        target_modal_energy_dynamic_driver_final=dynamic_target,
        target_modal_energy_reduction_fraction=(baseline_target - dynamic_target) / max(baseline_target, 1e-15),
        dynamic_driver_vs_ideal_relative_gap=abs(dynamic_target - ideal_target) / max(abs(ideal_target), 1e-15),
        baseline_enstrophy_final=baseline_enstrophy,
        dynamic_driver_enstrophy_final=dynamic_enstrophy,
        enstrophy_reduction_fraction=(baseline_enstrophy - dynamic_enstrophy) / max(baseline_enstrophy, 1e-15),
        max_abs_current_a=max_current,
        max_abs_voltage_v=max_voltage,
        peak_temperature_k=peak_temperature,
        max_relative_current_tracking_error=max_tracking_error,
        current_effort_a2_s=effort,
        electrical_energy_j=electrical_energy,
        velocity_divergence_rms=_spectral_divergence_rms(u, v),
        magnetic_divergence_rms=_spectral_divergence_rms(bx, by),
    )


def run_nsb_g16_benchmark(
    *,
    inductance_condition_limit: float = 2.0,
    step_error_limit: float = 0.02,
    step_settling_limit_s: float = 0.015,
    target_reduction_floor: float = 0.08,
    ideal_gap_limit: float = 0.25,
    divergence_limit: float = 1e-10,
) -> NSBG16Report:
    geometry = G15Geometry()
    driver = G16DriverConfig(current_limit_a=geometry.coil_current_limit_a)
    circuit = _circuit_case(geometry, driver)
    step = _step_response_case(geometry, driver)
    thermal = _thermal_case(geometry, driver)
    bandwidth = _bandwidth_case(geometry, driver)
    closed = _dynamic_closed_loop_case(geometry, driver)
    circuit_pass = circuit.inductance_matrix_condition_inf <= inductance_condition_limit and circuit.max_mutual_to_self_ratio < 0.20
    step_pass = (
        step.final_relative_current_error <= step_error_limit
        and step.settling_time_s is not None
        and step.settling_time_s <= step_settling_limit_s
        and step.max_abs_current_a <= driver.current_limit_a + 1e-12
        and step.max_abs_voltage_v <= driver.driver_voltage_limit_v + 1e-12
    )
    thermal_pass = thermal.peak_temperature_k < thermal.thermal_limit_k
    bandwidth_pass = bandwidth.correctly_flagged_bandwidth_limited and bandwidth.max_abs_voltage_v <= driver.driver_voltage_limit_v + 1e-12
    closed_pass = (
        closed.target_modal_energy_reduction_fraction >= target_reduction_floor
        and closed.dynamic_driver_vs_ideal_relative_gap <= ideal_gap_limit
        and closed.max_abs_current_a <= driver.current_limit_a + 1e-12
        and closed.max_abs_voltage_v <= driver.driver_voltage_limit_v + 1e-12
        and closed.peak_temperature_k < driver.thermal_limit_k
        and max(closed.velocity_divergence_rms, closed.magnetic_divergence_rms) <= divergence_limit
    )
    acceptance_pass = all((circuit_pass, step_pass, thermal_pass, bandwidth_pass, closed_pass))
    report = NSBG16Report(
        geometry=geometry,
        driver=driver,
        circuit_case=circuit,
        step_response_case=step,
        thermal_case=thermal,
        bandwidth_case=bandwidth,
        closed_loop_case=closed,
        acceptance=G16AcceptanceSummary(
            inductance_condition_limit=inductance_condition_limit,
            step_error_limit=step_error_limit,
            step_settling_limit_s=step_settling_limit_s,
            target_reduction_floor=target_reduction_floor,
            ideal_gap_limit=ideal_gap_limit,
            divergence_limit=divergence_limit,
            circuit_pass=circuit_pass,
            step_response_pass=step_pass,
            thermal_pass=thermal_pass,
            bandwidth_limit_detection_pass=bandwidth_pass,
            closed_loop_pass=closed_pass,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g16_report(report: NSBG16Report) -> bool:
    return report.report_digest == canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
