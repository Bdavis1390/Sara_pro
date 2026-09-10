from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .nsb_g3_solver import (
    TWO_PI,
    _add_scaled,
    _enstrophy,
    _fft2,
    _field_mean,
    _field_rms,
    _ifft2_real,
    _kinetic_energy,
    _l2_difference,
    _mixed_mode_initial,
    _poisson_residual_rms,
    _require_radix2,
    _rhs_components,
    _spectral_divergence_rms,
    _stability_bound,
    _velocity_and_streamfunction,
    _wavenumbers,
)
from .qualification import CapabilityStatus, canonical_digest


class G7ModeResult(BaseModel):
    case_id: str
    grid_size: int = Field(ge=8)
    k_parallel: int = Field(ge=0)
    k_transverse: int = Field(ge=0)
    viscosity: float = Field(gt=0.0)
    magnetic_damping: float = Field(ge=0.0)
    final_time: float = Field(gt=0.0)
    requested_dt: float = Field(gt=0.0)
    effective_dt: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    orientation_fraction: float = Field(ge=0.0, le=1.0)
    exact_total_decay_rate: float = Field(ge=0.0)
    exact_magnetic_decay_rate: float = Field(ge=0.0)
    measured_total_decay_rate: float = Field(ge=0.0)
    measured_magnetic_decay_rate: float
    vorticity_l2_error: float = Field(ge=0.0)
    divergence_rms: float = Field(ge=0.0)
    poisson_residual_rms: float = Field(ge=0.0)
    kinetic_energy_initial: float = Field(ge=0.0)
    kinetic_energy_final: float = Field(ge=0.0)
    enstrophy_initial: float = Field(ge=0.0)
    enstrophy_final: float = Field(ge=0.0)
    magnetic_dissipation_rate_initial: float = Field(ge=0.0)


class G7NonlinearResult(BaseModel):
    grid_size: int = Field(ge=8)
    viscosity: float = Field(gt=0.0)
    magnetic_damping: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    dt: float = Field(gt=0.0)
    nonlinear_rhs_rms_initial: float = Field(ge=0.0)
    magnetic_dissipation_rate_initial: float = Field(ge=0.0)
    zero_field_energy_final: float = Field(ge=0.0)
    magnetic_energy_final: float = Field(ge=0.0)
    zero_field_enstrophy_final: float = Field(ge=0.0)
    magnetic_enstrophy_final: float = Field(ge=0.0)
    magnetic_energy_reduction_fraction: float = Field(ge=0.0)
    mean_vorticity_drift: float = Field(ge=0.0)
    divergence_rms_final: float = Field(ge=0.0)
    poisson_residual_rms_final: float = Field(ge=0.0)


class G7AcceptanceSummary(BaseModel):
    temporal_order_floor: float = Field(gt=0.0)
    temporal_orders: tuple[float, float]
    finest_mode_l2_limit: float = Field(gt=0.0)
    max_orientation_rate_error_limit: float = Field(gt=0.0)
    max_orientation_rate_error: float = Field(ge=0.0)
    divergence_limit: float = Field(gt=0.0)
    poisson_residual_limit: float = Field(gt=0.0)
    parallel_mode_sink_limit: float = Field(gt=0.0)
    nonlinear_energy_reduction_floor: float = Field(gt=0.0)
    temporal_convergence_pass: bool
    orientation_decay_pass: bool
    field_parallel_null_pass: bool
    field_transverse_max_pass: bool
    zero_magnetic_limit_pass: bool
    nonlinear_magnetic_sink_pass: bool
    conservation_geometry_pass: bool
    acceptance_pass: bool


class NSBG7Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G7-001"
    benchmark_version: str = "1.2"
    formulation: str = "bounded 2D periodic low-Rm imposed-field quasi-static spectral damping reference"
    imposed_field_direction: str = "x / k_parallel axis"
    normalized_magnetic_operator: str = "d(omega_hat_k)/dt|B = -Lambda*(k_parallel^2/|k|^2)*omega_hat_k"
    physical_scope: str = "homogeneous periodic low-magnetic-Reynolds-number imposed-field reference with no induction equation"
    temporal_scheme: str = "explicit midpoint RK2"
    spatial_scheme: str = "G3 Fourier vorticity-streamfunction solver with two-thirds-dealiased nonlinear advection"
    mode_cases: tuple[G7ModeResult, ...]
    temporal_cases: tuple[G7ModeResult, ...]
    nonlinear_result: G7NonlinearResult
    acceptance: G7AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    anisotropic_qs_operator_implemented: bool = True
    exact_single_mode_decay_verified: bool = True
    nonlinear_2d_periodic_reference_executed: bool = True
    full_mhd_solver_claimed: bool = False
    induction_equation_solved: bool = False
    finite_rm_mhd_claimed: bool = False
    general_2d_or_3d_mhd_claimed: bool = False
    hall_two_fluid_or_kinetic_solved: bool = False
    plasma_solved: bool = False
    adaptive_em_control_validated: bool = False
    laboratory_validation_performed: bool = False
    navier_stokes_singularity_reproduced: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G7 verifies a bounded low-Rm imposed-field anisotropic Joule-damping operator inside the existing 2D periodic spectral flow solver.",
        "The operator is the normalized homogeneous quasi-static Fourier-space damping proportional to k_parallel^2/|k|^2; it does not solve magnetic induction or finite-Rm MHD.",
        "The 2D periodic geometry is a reference domain, not a claim of general magnetofluid boundary-condition capability.",
        "Passing G7 does not establish Hall-MHD, two-fluid, kinetic, plasma, adaptive electromagnetic control, laboratory, propulsion, shielding, stealth, cloaking, or operational capability.",
        "Passing G7 does not reproduce, validate, or refute any finite-time Navier-Stokes singularity construction.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG7Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.2 must remain SIMULATED_ONLY")
        if not all((
            self.anisotropic_qs_operator_implemented,
            self.exact_single_mode_decay_verified,
            self.nonlinear_2d_periodic_reference_executed,
        )):
            raise ValueError("G7 report must represent the complete bounded reference gate")
        prohibited = (
            self.full_mhd_solver_claimed,
            self.induction_equation_solved,
            self.finite_rm_mhd_claimed,
            self.general_2d_or_3d_mhd_claimed,
            self.hall_two_fluid_or_kinetic_solved,
            self.plasma_solved,
            self.adaptive_em_control_validated,
            self.laboratory_validation_performed,
            self.navier_stokes_singularity_reproduced,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v1.2 cannot promote unsupported MHD, plasma, physical, singularity, or operational claims")
        return self


def _orientation_fraction(k_parallel: int, k_transverse: int) -> float:
    k2 = k_parallel * k_parallel + k_transverse * k_transverse
    if k2 <= 0:
        raise ValueError("mode must have nonzero wavenumber")
    return (k_parallel * k_parallel) / k2


def _single_mode_initial(
    grid_size: int,
    *,
    k_parallel: int,
    k_transverse: int,
    amplitude: float = 1.0,
) -> list[list[float]]:
    _require_radix2(grid_size)
    if k_parallel < 0 or k_transverse < 0 or k_parallel + k_transverse == 0:
        raise ValueError("single-mode wavenumbers must be nonnegative and not both zero")
    if max(k_parallel, k_transverse) >= grid_size // 3:
        raise ValueError("single-mode reference must remain below two-thirds cutoff")
    dx = TWO_PI / grid_size
    return [
        [
            amplitude
            * (math.cos(k_parallel * i * dx) if k_parallel else 1.0)
            * (math.cos(k_transverse * j * dx) if k_transverse else 1.0)
            for j in range(grid_size)
        ]
        for i in range(grid_size)
    ]


def _magnetic_vorticity_term(
    vorticity: list[list[float]],
    magnetic_damping: float,
) -> list[list[float]]:
    if magnetic_damping < 0.0:
        raise ValueError("magnetic_damping must be nonnegative")
    n = len(vorticity)
    omega_hat = _fft2(vorticity)
    modes = _wavenumbers(n)
    magnetic_hat = [[0.0j] * n for _ in range(n)]
    for i, k_parallel in enumerate(modes):
        for j, k_transverse in enumerate(modes):
            k2 = k_parallel * k_parallel + k_transverse * k_transverse
            if k2 == 0:
                magnetic_hat[i][j] = 0.0j
            else:
                fraction = (k_parallel * k_parallel) / k2
                magnetic_hat[i][j] = -magnetic_damping * fraction * omega_hat[i][j]
    return _ifft2_real(magnetic_hat)


def _magnetic_dissipation_rate(
    vorticity: list[list[float]],
    magnetic_damping: float,
) -> float:
    if magnetic_damping < 0.0:
        raise ValueError("magnetic_damping must be nonnegative")
    n = len(vorticity)
    omega_hat = _fft2(vorticity)
    modes = _wavenumbers(n)
    total = 0.0
    for i, k_parallel in enumerate(modes):
        for j, k_transverse in enumerate(modes):
            k2 = k_parallel * k_parallel + k_transverse * k_transverse
            if k2 == 0:
                continue
            fraction = (k_parallel * k_parallel) / k2
            total += fraction * (abs(omega_hat[i][j]) ** 2) / k2
    return magnetic_damping * total / (n ** 4)


def _rhs_qs(
    vorticity: list[list[float]],
    *,
    viscosity: float,
    magnetic_damping: float,
) -> tuple[list[list[float]], list[list[float]], list[list[float]], list[list[float]]]:
    hydro_rhs, u, v, nonlinear = _rhs_components(vorticity, viscosity)
    magnetic = _magnetic_vorticity_term(vorticity, magnetic_damping)
    n = len(vorticity)
    rhs = [[hydro_rhs[i][j] + magnetic[i][j] for j in range(n)] for i in range(n)]
    return rhs, u, v, nonlinear


def _midpoint_step_qs(
    vorticity: list[list[float]],
    *,
    dt: float,
    viscosity: float,
    magnetic_damping: float,
) -> list[list[float]]:
    k1, _, _, _ = _rhs_qs(vorticity, viscosity=viscosity, magnetic_damping=magnetic_damping)
    midpoint = _add_scaled(vorticity, k1, 0.5 * dt)
    k2, _, _, _ = _rhs_qs(midpoint, viscosity=viscosity, magnetic_damping=magnetic_damping)
    return _add_scaled(vorticity, k2, dt)


def integrate_qs_periodic_vorticity(
    *,
    initial_vorticity: list[list[float]],
    viscosity: float,
    magnetic_damping: float,
    dt: float,
    final_time: float,
) -> tuple[list[list[float]], float, int]:
    n = len(initial_vorticity)
    _require_radix2(n)
    if any(len(row) != n for row in initial_vorticity):
        raise ValueError("initial_vorticity must be square")
    if viscosity <= 0.0:
        raise ValueError("G7 reference integration requires positive viscosity")
    if magnetic_damping < 0.0:
        raise ValueError("magnetic_damping must be nonnegative")
    if dt <= 0.0 or final_time <= 0.0:
        raise ValueError("dt and final_time must be positive")
    if abs(_field_mean(initial_vorticity)) > 1e-12:
        raise ValueError("periodic streamfunction inversion requires near-zero mean vorticity")

    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    hydro_limit = _stability_bound(initial_vorticity, viscosity)
    magnetic_limit = math.inf if magnetic_damping <= 0.0 else 0.5 / magnetic_damping
    if effective_dt > min(hydro_limit, magnetic_limit):
        raise ValueError("requested timestep exceeds conservative G7 stability bound")

    vorticity = [row[:] for row in initial_vorticity]
    for _ in range(steps):
        vorticity = _midpoint_step_qs(
            vorticity,
            dt=effective_dt,
            viscosity=viscosity,
            magnetic_damping=magnetic_damping,
        )
        if effective_dt > 1.05 * min(_stability_bound(vorticity, viscosity), magnetic_limit):
            raise ValueError("evolving flow exceeded conservative G7 stability bound")
    return vorticity, effective_dt, steps


def _mode_case(
    *,
    case_id: str,
    grid_size: int,
    k_parallel: int,
    k_transverse: int,
    viscosity: float,
    magnetic_damping: float,
    dt: float,
    final_time: float,
) -> G7ModeResult:
    initial = _single_mode_initial(
        grid_size,
        k_parallel=k_parallel,
        k_transverse=k_transverse,
    )
    numerical, effective_dt, steps = integrate_qs_periodic_vorticity(
        initial_vorticity=initial,
        viscosity=viscosity,
        magnetic_damping=magnetic_damping,
        dt=dt,
        final_time=final_time,
    )
    k2 = k_parallel * k_parallel + k_transverse * k_transverse
    fraction = _orientation_fraction(k_parallel, k_transverse)
    magnetic_rate = magnetic_damping * fraction
    total_rate = viscosity * k2 + magnetic_rate
    decay = math.exp(-total_rate * final_time)
    exact = [[decay * value for value in row] for row in initial]

    rms_initial = _field_rms(initial)
    rms_final = _field_rms(numerical)
    measured_total = -math.log(rms_final / rms_initial) / final_time
    measured_magnetic = measured_total - viscosity * k2

    u_initial, v_initial, _ = _velocity_and_streamfunction(initial)
    u_final, v_final, psi_final = _velocity_and_streamfunction(numerical)
    return G7ModeResult(
        case_id=case_id,
        grid_size=grid_size,
        k_parallel=k_parallel,
        k_transverse=k_transverse,
        viscosity=viscosity,
        magnetic_damping=magnetic_damping,
        final_time=final_time,
        requested_dt=dt,
        effective_dt=effective_dt,
        steps=steps,
        orientation_fraction=fraction,
        exact_total_decay_rate=total_rate,
        exact_magnetic_decay_rate=magnetic_rate,
        measured_total_decay_rate=measured_total,
        measured_magnetic_decay_rate=measured_magnetic,
        vorticity_l2_error=_l2_difference(numerical, exact),
        divergence_rms=_spectral_divergence_rms(u_final, v_final),
        poisson_residual_rms=_poisson_residual_rms(numerical, psi_final),
        kinetic_energy_initial=_kinetic_energy(u_initial, v_initial),
        kinetic_energy_final=_kinetic_energy(u_final, v_final),
        enstrophy_initial=_enstrophy(initial),
        enstrophy_final=_enstrophy(numerical),
        magnetic_dissipation_rate_initial=_magnetic_dissipation_rate(initial, magnetic_damping),
    )


def _observed_order(coarse_error: float, fine_error: float) -> float:
    if coarse_error <= 0.0 or fine_error <= 0.0:
        raise ValueError("convergence errors must be positive")
    return math.log(coarse_error / fine_error) / math.log(2.0)


def _nonlinear_case(
    *,
    grid_size: int,
    viscosity: float,
    magnetic_damping: float,
    dt: float,
    final_time: float,
) -> G7NonlinearResult:
    initial = _mixed_mode_initial(grid_size)
    _, _, _, nonlinear_initial = _rhs_qs(
        initial,
        viscosity=viscosity,
        magnetic_damping=magnetic_damping,
    )
    zero_field, _, _ = integrate_qs_periodic_vorticity(
        initial_vorticity=initial,
        viscosity=viscosity,
        magnetic_damping=0.0,
        dt=dt,
        final_time=final_time,
    )
    magnetic, _, _ = integrate_qs_periodic_vorticity(
        initial_vorticity=initial,
        viscosity=viscosity,
        magnetic_damping=magnetic_damping,
        dt=dt,
        final_time=final_time,
    )
    u_zero, v_zero, _ = _velocity_and_streamfunction(zero_field)
    u_mag, v_mag, psi_mag = _velocity_and_streamfunction(magnetic)
    energy_zero = _kinetic_energy(u_zero, v_zero)
    energy_mag = _kinetic_energy(u_mag, v_mag)
    mean_initial = _field_mean(initial)
    mean_final = _field_mean(magnetic)
    return G7NonlinearResult(
        grid_size=grid_size,
        viscosity=viscosity,
        magnetic_damping=magnetic_damping,
        final_time=final_time,
        dt=dt,
        nonlinear_rhs_rms_initial=_field_rms(nonlinear_initial),
        magnetic_dissipation_rate_initial=_magnetic_dissipation_rate(initial, magnetic_damping),
        zero_field_energy_final=energy_zero,
        magnetic_energy_final=energy_mag,
        zero_field_enstrophy_final=_enstrophy(zero_field),
        magnetic_enstrophy_final=_enstrophy(magnetic),
        magnetic_energy_reduction_fraction=(energy_zero - energy_mag) / max(energy_zero, 1e-15),
        mean_vorticity_drift=abs(mean_final - mean_initial),
        divergence_rms_final=_spectral_divergence_rms(u_mag, v_mag),
        poisson_residual_rms_final=_poisson_residual_rms(magnetic, psi_mag),
    )


def run_nsb_g7_benchmark(
    *,
    grid_size: int = 32,
    viscosity: float = 0.03,
    magnetic_damping: float = 0.8,
    mode_dt: float = 0.002,
    mode_final_time: float = 0.3,
    temporal_dts: tuple[float, float, float] = (0.04, 0.02, 0.01),
    temporal_final_time: float = 0.4,
    temporal_order_floor: float = 1.8,
    finest_mode_l2_limit: float = 5e-5,
    max_orientation_rate_error_limit: float = 5e-4,
    divergence_limit: float = 1e-10,
    poisson_residual_limit: float = 1e-10,
    parallel_mode_sink_limit: float = 1e-12,
    nonlinear_energy_reduction_floor: float = 1e-3,
) -> NSBG7Report:
    _require_radix2(grid_size)
    if not (temporal_dts[0] == 2.0 * temporal_dts[1] and temporal_dts[1] == 2.0 * temporal_dts[2]):
        raise ValueError("temporal dts must halve exactly")

    mode_specs = (
        (0, 2, "parallel_flow_k0_2"),
        (1, 3, "weakly_damped_k1_3"),
        (1, 1, "diagonal_k1_1"),
        (3, 1, "strongly_damped_k3_1"),
        (2, 0, "transverse_flow_k2_0"),
    )
    mode_cases = tuple(
        _mode_case(
            case_id=case_id,
            grid_size=grid_size,
            k_parallel=k_parallel,
            k_transverse=k_transverse,
            viscosity=viscosity,
            magnetic_damping=magnetic_damping,
            dt=mode_dt,
            final_time=mode_final_time,
        )
        for k_parallel, k_transverse, case_id in mode_specs
    )

    temporal_cases = tuple(
        _mode_case(
            case_id=f"temporal_k3_1_dt_{dt:g}",
            grid_size=grid_size,
            k_parallel=3,
            k_transverse=1,
            viscosity=viscosity,
            magnetic_damping=magnetic_damping,
            dt=dt,
            final_time=temporal_final_time,
        )
        for dt in temporal_dts
    )
    temporal_errors = tuple(case.vorticity_l2_error for case in temporal_cases)
    temporal_orders = (
        _observed_order(temporal_errors[0], temporal_errors[1]),
        _observed_order(temporal_errors[1], temporal_errors[2]),
    )

    zero_magnetic = _mode_case(
        case_id="zero_magnetic_k3_1",
        grid_size=grid_size,
        k_parallel=3,
        k_transverse=1,
        viscosity=viscosity,
        magnetic_damping=0.0,
        dt=mode_dt,
        final_time=mode_final_time,
    )
    nonlinear = _nonlinear_case(
        grid_size=grid_size,
        viscosity=0.01,
        magnetic_damping=magnetic_damping,
        dt=0.002,
        final_time=0.08,
    )

    rate_errors = tuple(
        abs(case.measured_magnetic_decay_rate - case.exact_magnetic_decay_rate)
        for case in mode_cases
    )
    max_rate_error = max(rate_errors)
    temporal_pass = min(temporal_orders) >= temporal_order_floor and temporal_errors[-1] <= finest_mode_l2_limit
    orientation_pass = max_rate_error <= max_orientation_rate_error_limit
    parallel_case = mode_cases[0]
    transverse_case = mode_cases[-1]
    parallel_pass = (
        parallel_case.orientation_fraction == 0.0
        and parallel_case.magnetic_dissipation_rate_initial <= parallel_mode_sink_limit
        and abs(parallel_case.measured_magnetic_decay_rate) <= max_orientation_rate_error_limit
    )
    transverse_pass = (
        abs(transverse_case.orientation_fraction - 1.0) <= 1e-15
        and abs(transverse_case.measured_magnetic_decay_rate - magnetic_damping) <= max_orientation_rate_error_limit
        and transverse_case.magnetic_dissipation_rate_initial > 0.0
    )
    zero_magnetic_pass = (
        zero_magnetic.magnetic_dissipation_rate_initial <= parallel_mode_sink_limit
        and abs(zero_magnetic.measured_magnetic_decay_rate) <= max_orientation_rate_error_limit
        and zero_magnetic.vorticity_l2_error <= finest_mode_l2_limit
    )
    nonlinear_pass = (
        nonlinear.nonlinear_rhs_rms_initial > 1e-2
        and nonlinear.magnetic_dissipation_rate_initial > 0.0
        and nonlinear.magnetic_energy_reduction_fraction >= nonlinear_energy_reduction_floor
    )
    geometry_pass = (
        max(case.divergence_rms for case in (*mode_cases, *temporal_cases)) <= divergence_limit
        and max(case.poisson_residual_rms for case in (*mode_cases, *temporal_cases)) <= poisson_residual_limit
        and nonlinear.divergence_rms_final <= divergence_limit
        and nonlinear.poisson_residual_rms_final <= poisson_residual_limit
        and nonlinear.mean_vorticity_drift <= 1e-12
    )
    acceptance_pass = all((
        temporal_pass,
        orientation_pass,
        parallel_pass,
        transverse_pass,
        zero_magnetic_pass,
        nonlinear_pass,
        geometry_pass,
    ))

    report = NSBG7Report(
        mode_cases=mode_cases,
        temporal_cases=temporal_cases,
        nonlinear_result=nonlinear,
        acceptance=G7AcceptanceSummary(
            temporal_order_floor=temporal_order_floor,
            temporal_orders=temporal_orders,
            finest_mode_l2_limit=finest_mode_l2_limit,
            max_orientation_rate_error_limit=max_orientation_rate_error_limit,
            max_orientation_rate_error=max_rate_error,
            divergence_limit=divergence_limit,
            poisson_residual_limit=poisson_residual_limit,
            parallel_mode_sink_limit=parallel_mode_sink_limit,
            nonlinear_energy_reduction_floor=nonlinear_energy_reduction_floor,
            temporal_convergence_pass=temporal_pass,
            orientation_decay_pass=orientation_pass,
            field_parallel_null_pass=parallel_pass,
            field_transverse_max_pass=transverse_pass,
            zero_magnetic_limit_pass=zero_magnetic_pass,
            nonlinear_magnetic_sink_pass=nonlinear_pass,
            conservation_geometry_pass=geometry_pass,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g7_report(report: NSBG7Report) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
