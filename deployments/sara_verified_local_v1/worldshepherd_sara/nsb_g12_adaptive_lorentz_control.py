from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .nsb_g3_solver import TWO_PI, _field_rms, _l2_difference, _spectral_divergence_rms, _velocity_and_streamfunction
from .nsb_g10_nonlinear_mhd import _magnetic_state, _mixed_initial, _rhs, integrate_periodic_mhd
from .qualification import CapabilityStatus, canonical_digest


class G12ControlCase(BaseModel):
    grid_size: int = Field(ge=8)
    viscosity: float = Field(gt=0.0)
    resistivity: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    dt: float = Field(gt=0.0)
    feedback_gain: float = Field(gt=0.0)
    command_limit: float = Field(gt=0.0)
    baseline_parity_l2: float = Field(ge=0.0)
    target_modal_energy_initial: float = Field(ge=0.0)
    target_modal_energy_baseline_final: float = Field(ge=0.0)
    target_modal_energy_controlled_final: float = Field(ge=0.0)
    target_modal_energy_wrong_sign_final: float = Field(ge=0.0)
    target_modal_energy_reduction_fraction: float
    baseline_enstrophy_final: float = Field(ge=0.0)
    controlled_enstrophy_final: float = Field(ge=0.0)
    enstrophy_reduction_fraction: float
    wrong_sign_vs_controlled_fraction: float
    control_effort: float = Field(ge=0.0)
    max_abs_command: float = Field(ge=0.0)
    initial_command_rms: float = Field(ge=0.0)
    final_command_rms: float = Field(ge=0.0)
    controlled_velocity_divergence_rms: float = Field(ge=0.0)
    controlled_magnetic_divergence_rms: float = Field(ge=0.0)


class G12AcceptanceSummary(BaseModel):
    baseline_parity_limit: float = Field(gt=0.0)
    target_reduction_floor: float = Field(gt=0.0)
    enstrophy_reduction_floor: float = Field(gt=0.0)
    divergence_limit: float = Field(gt=0.0)
    command_bound_tolerance: float = Field(ge=0.0)
    baseline_parity_pass: bool
    bounded_command_pass: bool
    target_reduction_pass: bool
    enstrophy_reduction_pass: bool
    wrong_sign_ordering_pass: bool
    geometry_pass: bool
    adaptive_response_pass: bool
    acceptance_pass: bool


class NSBG12Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G12-001"
    benchmark_version: str = "1.7"
    formulation: str = "bounded adaptive Lorentz-force-curl control abstraction on the validated G10 nonlinear 2D MHD plant"
    plant: str = "G10 2D periodic incompressible nonlinear resistive-MHD reference"
    controller: str = "deterministic bounded modal feedback with zero-order-held commands"
    actuator_abstraction: str = "prescribed basis for curl(f_EM)/rho injected into the vorticity equation"
    control_case: G12ControlCase
    acceptance: G12AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    adaptive_lorentz_curl_control_simulated: bool = True
    bounded_feedback_loop_executed: bool = True
    zero_control_ablation_executed: bool = True
    wrong_sign_red_team_executed: bool = True
    physical_actuator_mapping_validated: bool = False
    adaptive_em_control_validated: bool = False
    laboratory_validation_performed: bool = False
    hardware_boundary_control_validated: bool = False
    compressible_or_3d_mhd_validated: bool = False
    hall_two_fluid_kinetic_or_plasma_validated: bool = False
    navier_stokes_singularity_reproduced: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G12 demonstrates bounded feedback against an abstract Lorentz-force-curl actuator basis inside the validated G10 simulation plant.",
        "The actuator basis is a control abstraction; no mapping from real coils, electrodes, metasurface cells, currents, voltages, or RF hardware to that basis is established by G12.",
        "G12 is simulated control evidence only and does not establish physical adaptive electromagnetic control or laboratory performance.",
        "G12 does not establish compressible/3D MHD, Hall-MHD, two-fluid, kinetic, plasma, propulsion, shielding, stealth, cloaking, or operational capability.",
        "Passing G12 does not reproduce, validate, or refute a finite-time Navier-Stokes singularity construction.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG12Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.7 must remain SIMULATED_ONLY")
        if not all((
            self.adaptive_lorentz_curl_control_simulated,
            self.bounded_feedback_loop_executed,
            self.zero_control_ablation_executed,
            self.wrong_sign_red_team_executed,
        )):
            raise ValueError("G12 report must represent the executed bounded simulated control gate")
        prohibited = (
            self.physical_actuator_mapping_validated,
            self.adaptive_em_control_validated,
            self.laboratory_validation_performed,
            self.hardware_boundary_control_validated,
            self.compressible_or_3d_mhd_validated,
            self.hall_two_fluid_kinetic_or_plasma_validated,
            self.navier_stokes_singularity_reproduced,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v1.7 cannot promote unsupported physical, hardware, or higher-fidelity claims")
        return self


def _basis_fields(n: int):
    h = TWO_PI / n
    return (
        [[math.sin(i * h) * math.cos(2.0 * j * h) for j in range(n)] for i in range(n)],
        [[math.cos(2.0 * i * h + j * h) for j in range(n)] for i in range(n)],
        [[math.sin(3.0 * i * h - 2.0 * j * h) for j in range(n)] for i in range(n)],
    )


def _projection(field, basis):
    n = len(field)
    numerator = sum(field[i][j] * basis[i][j] for i in range(n) for j in range(n)) / (n * n)
    denominator = sum(basis[i][j] ** 2 for i in range(n) for j in range(n)) / (n * n)
    return numerator / max(denominator, 1e-15)


def _commands(omega, *, gain: float, command_limit: float, feedback_sign: float):
    bases = _basis_fields(len(omega))
    commands = []
    for basis in bases:
        amplitude = _projection(omega, basis)
        raw = feedback_sign * gain * amplitude
        commands.append(max(-command_limit, min(command_limit, raw)))
    return tuple(commands), bases


def _source_from_commands(commands, bases):
    n = len(bases[0])
    return [[sum(commands[k] * bases[k][i][j] for k in range(len(commands))) for j in range(n)] for i in range(n)]


def _controlled_rhs(omega, a, *, viscosity: float, resistivity: float, source):
    domega, da, components = _rhs(omega, a, viscosity=viscosity, resistivity=resistivity)
    n = len(omega)
    controlled = [[domega[i][j] + source[i][j] for j in range(n)] for i in range(n)]
    return controlled, da, components


def _add_scaled_pair(omega, a, domega, da, scale):
    n = len(omega)
    return (
        [[omega[i][j] + scale * domega[i][j] for j in range(n)] for i in range(n)],
        [[a[i][j] + scale * da[i][j] for j in range(n)] for i in range(n)],
    )


def _controlled_midpoint_step(omega, a, *, dt: float, viscosity: float, resistivity: float, source):
    k1w, k1a, _ = _controlled_rhs(omega, a, viscosity=viscosity, resistivity=resistivity, source=source)
    mw, ma = _add_scaled_pair(omega, a, k1w, k1a, 0.5 * dt)
    k2w, k2a, _ = _controlled_rhs(mw, ma, viscosity=viscosity, resistivity=resistivity, source=source)
    return _add_scaled_pair(omega, a, k2w, k2a, dt)


def integrate_feedback_control(
    *,
    initial_vorticity,
    initial_magnetic_potential,
    viscosity: float,
    resistivity: float,
    dt: float,
    final_time: float,
    gain: float,
    command_limit: float,
    feedback_sign: float = -1.0,
):
    if dt <= 0.0 or final_time <= 0.0:
        raise ValueError("dt and final_time must be positive")
    if gain < 0.0 or command_limit <= 0.0:
        raise ValueError("gain must be nonnegative and command_limit positive")
    n = len(initial_vorticity)
    if n < 8 or n & (n - 1):
        raise ValueError("G12 requires radix-2 grid size >= 8")
    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    omega = [row[:] for row in initial_vorticity]
    a = [row[:] for row in initial_magnetic_potential]
    effort = 0.0
    max_abs = 0.0
    first_commands = None
    last_commands = None
    for _ in range(steps):
        commands, bases = _commands(omega, gain=gain, command_limit=command_limit, feedback_sign=feedback_sign)
        if first_commands is None:
            first_commands = commands
        last_commands = commands
        max_abs = max(max_abs, *(abs(value) for value in commands))
        effort += effective_dt * sum(value * value for value in commands)
        source = _source_from_commands(commands, bases)
        omega, a = _controlled_midpoint_step(
            omega,
            a,
            dt=effective_dt,
            viscosity=viscosity,
            resistivity=resistivity,
            source=source,
        )
        if not all(math.isfinite(value) for row in omega for value in row):
            raise ValueError("G12 controlled plant became non-finite")
    assert first_commands is not None and last_commands is not None
    rms0 = math.sqrt(sum(value * value for value in first_commands) / len(first_commands))
    rmsf = math.sqrt(sum(value * value for value in last_commands) / len(last_commands))
    return omega, a, effective_dt, steps, effort, max_abs, rms0, rmsf


def _target_modal_energy(omega):
    bases = _basis_fields(len(omega))
    n = len(omega)
    total = 0.0
    for basis in bases:
        amplitude = _projection(omega, basis)
        norm = sum(value * value for row in basis for value in row) / (n * n)
        total += 0.5 * amplitude * amplitude * norm
    return total


def _enstrophy(omega):
    n = len(omega)
    return 0.5 * sum(value * value for row in omega for value in row) / (n * n)


def _control_case(
    *,
    n: int = 16,
    viscosity: float = 0.01,
    resistivity: float = 0.015,
    dt: float = 0.0005,
    final_time: float = 0.05,
    feedback_gain: float = 4.0,
    command_limit: float = 2.0,
):
    omega0, a0 = _mixed_initial(n)
    target0 = _target_modal_energy(omega0)
    baseline_w, baseline_a, _, _, _, _, _, _ = integrate_feedback_control(
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
    reference_w, reference_a, _, _ = integrate_periodic_mhd(
        initial_vorticity=omega0,
        initial_magnetic_potential=a0,
        viscosity=viscosity,
        resistivity=resistivity,
        dt=dt,
        final_time=final_time,
    )
    parity = math.sqrt(_l2_difference(baseline_w, reference_w) ** 2 + _l2_difference(baseline_a, reference_a) ** 2)
    controlled_w, controlled_a, effective_dt, _, effort, max_abs, rms0, rmsf = integrate_feedback_control(
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
    wrong_w, _, _, _, _, _, _, _ = integrate_feedback_control(
        initial_vorticity=omega0,
        initial_magnetic_potential=a0,
        viscosity=viscosity,
        resistivity=resistivity,
        dt=dt,
        final_time=final_time,
        gain=feedback_gain,
        command_limit=command_limit,
        feedback_sign=1.0,
    )
    target_b = _target_modal_energy(baseline_w)
    target_c = _target_modal_energy(controlled_w)
    target_w = _target_modal_energy(wrong_w)
    enstrophy_b = _enstrophy(baseline_w)
    enstrophy_c = _enstrophy(controlled_w)
    u, v, _ = _velocity_and_streamfunction(controlled_w)
    bx, by, _ = _magnetic_state(controlled_a)
    return G12ControlCase(
        grid_size=n,
        viscosity=viscosity,
        resistivity=resistivity,
        final_time=final_time,
        dt=effective_dt,
        feedback_gain=feedback_gain,
        command_limit=command_limit,
        baseline_parity_l2=parity,
        target_modal_energy_initial=target0,
        target_modal_energy_baseline_final=target_b,
        target_modal_energy_controlled_final=target_c,
        target_modal_energy_wrong_sign_final=target_w,
        target_modal_energy_reduction_fraction=(target_b - target_c) / max(target_b, 1e-15),
        baseline_enstrophy_final=enstrophy_b,
        controlled_enstrophy_final=enstrophy_c,
        enstrophy_reduction_fraction=(enstrophy_b - enstrophy_c) / max(enstrophy_b, 1e-15),
        wrong_sign_vs_controlled_fraction=(target_w - target_c) / max(target_c, 1e-15),
        control_effort=effort,
        max_abs_command=max_abs,
        initial_command_rms=rms0,
        final_command_rms=rmsf,
        controlled_velocity_divergence_rms=_spectral_divergence_rms(u, v),
        controlled_magnetic_divergence_rms=_spectral_divergence_rms(bx, by),
    )


def run_nsb_g12_benchmark(
    *,
    baseline_parity_limit: float = 1e-12,
    target_reduction_floor: float = 0.05,
    enstrophy_reduction_floor: float = 0.02,
    divergence_limit: float = 1e-10,
    command_bound_tolerance: float = 1e-12,
) -> NSBG12Report:
    case = _control_case()
    parity_pass = case.baseline_parity_l2 <= baseline_parity_limit
    bound_pass = case.max_abs_command <= case.command_limit + command_bound_tolerance
    target_pass = case.target_modal_energy_reduction_fraction >= target_reduction_floor
    enstrophy_pass = case.enstrophy_reduction_fraction >= enstrophy_reduction_floor
    wrong_sign_pass = case.target_modal_energy_wrong_sign_final > case.target_modal_energy_controlled_final
    geometry_pass = max(case.controlled_velocity_divergence_rms, case.controlled_magnetic_divergence_rms) <= divergence_limit
    adaptive_pass = case.initial_command_rms > 0.0 and abs(case.final_command_rms - case.initial_command_rms) > 1e-6 and case.control_effort > 0.0
    acceptance_pass = all((parity_pass, bound_pass, target_pass, enstrophy_pass, wrong_sign_pass, geometry_pass, adaptive_pass))
    report = NSBG12Report(
        control_case=case,
        acceptance=G12AcceptanceSummary(
            baseline_parity_limit=baseline_parity_limit,
            target_reduction_floor=target_reduction_floor,
            enstrophy_reduction_floor=enstrophy_reduction_floor,
            divergence_limit=divergence_limit,
            command_bound_tolerance=command_bound_tolerance,
            baseline_parity_pass=parity_pass,
            bounded_command_pass=bound_pass,
            target_reduction_pass=target_pass,
            enstrophy_reduction_pass=enstrophy_pass,
            wrong_sign_ordering_pass=wrong_sign_pass,
            geometry_pass=geometry_pass,
            adaptive_response_pass=adaptive_pass,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g12_report(report: NSBG12Report) -> bool:
    return report.report_digest == canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
