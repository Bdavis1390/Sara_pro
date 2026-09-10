from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


TWO_PI = 2.0 * math.pi


class G9ComparisonResult(BaseModel):
    case_id: str
    grid_size: int = Field(ge=16)
    wavenumber: int = Field(ge=1)
    alfven_speed: float
    viscosity: float = Field(ge=0.0)
    magnetic_diffusivity: float = Field(ge=0.0)
    final_time: float = Field(gt=0.0)
    requested_dt: float = Field(gt=0.0)
    effective_dt: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    velocity_l2_error: float = Field(ge=0.0)
    magnetic_l2_error: float = Field(ge=0.0)
    combined_l2_error: float = Field(ge=0.0)
    kinetic_energy: float = Field(ge=0.0)
    magnetic_energy: float = Field(ge=0.0)
    total_energy: float = Field(ge=0.0)


class G9TransferResult(BaseModel):
    grid_size: int = Field(ge=16)
    wavenumber: int = Field(ge=1)
    alfven_speed: float
    viscosity: float = Field(ge=0.0)
    magnetic_diffusivity: float = Field(ge=0.0)
    mode_magnetic_reynolds: float = Field(gt=0.0)
    quarter_period: float = Field(gt=0.0)
    effective_dt: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    kinetic_energy_initial: float = Field(ge=0.0)
    magnetic_energy_initial: float = Field(ge=0.0)
    kinetic_energy_final: float = Field(ge=0.0)
    magnetic_energy_final: float = Field(ge=0.0)
    total_energy_final: float = Field(ge=0.0)
    magnetic_energy_fraction_final: float = Field(ge=0.0, le=1.0)
    expected_total_energy_continuum: float = Field(ge=0.0)
    total_energy_relative_error: float = Field(ge=0.0)


class G9ControlResult(BaseModel):
    grid_size: int = Field(ge=16)
    diffusion_only_magnetic_l2: float = Field(ge=0.0)
    diffusion_only_velocity_rms: float = Field(ge=0.0)
    alfven_sign_velocity_l2: float = Field(ge=0.0)
    alfven_sign_magnetic_antisymmetry_l2: float = Field(ge=0.0)
    zero_coupling_generated_magnetic_rms: float = Field(ge=0.0)


class G9AcceptanceSummary(BaseModel):
    spatial_order_floor: float = Field(gt=0.0)
    spatial_orders: tuple[float, float]
    finest_spatial_l2_limit: float = Field(gt=0.0)
    temporal_order_floor: float = Field(gt=0.0)
    temporal_orders: tuple[float, float]
    finest_temporal_l2_limit: float = Field(gt=0.0)
    transfer_magnetic_fraction_floor: float = Field(gt=0.0, le=1.0)
    transfer_energy_relative_error_limit: float = Field(gt=0.0)
    diffusion_only_l2_limit: float = Field(gt=0.0)
    symmetry_limit: float = Field(gt=0.0)
    spatial_convergence_pass: bool
    temporal_convergence_pass: bool
    alfven_transfer_pass: bool
    diffusion_only_pass: bool
    sign_symmetry_pass: bool
    zero_coupling_pass: bool
    acceptance_pass: bool


class NSBG9Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G9-001"
    benchmark_version: str = "1.4"
    formulation: str = "1D periodic linearized resistive-viscous Alfven induction/backreaction reference"
    velocity_equation: str = "du/dt = v_A*dx(b) + nu*dxx(u)"
    induction_equation: str = "db/dt = v_A*dx(u) + eta*dxx(b)"
    magnetic_variable: str = "transverse magnetic perturbation in Alfven-speed units"
    background_state: str = "uniform guide field and constant density absorbed into v_A"
    spatial_scheme: str = "second-order centered finite differences on a periodic grid"
    temporal_scheme: str = "classical explicit RK4"
    analytical_reference: str = "equal-diffusivity damped Elsasser/Alfven traveling-wave solution"
    spatial_cases: tuple[G9ComparisonResult, ...]
    temporal_cases: tuple[G9ComparisonResult, ...]
    transfer_result: G9TransferResult
    controls: G9ControlResult
    acceptance: G9AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    linearized_induction_equation_solved: bool = True
    linearized_lorentz_backreaction_solved: bool = True
    finite_rm_linear_reference_implemented: bool = True
    equal_diffusivity_reference: bool = True
    nonlinear_mhd_solver_claimed: bool = False
    compressible_mhd_solved: bool = False
    general_2d_or_3d_mhd_claimed: bool = False
    hall_two_fluid_or_kinetic_solved: bool = False
    plasma_solved: bool = False
    adaptive_em_control_validated: bool = False
    laboratory_validation_performed: bool = False
    navier_stokes_singularity_reproduced: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G9 introduces an explicit time-dependent magnetic perturbation and reciprocal linear Alfven backreaction in a bounded 1D periodic reference.",
        "The finite magnetic Reynolds number is a mode-scale property of this linearized reference; G9 is not a nonlinear or general finite-Rm MHD solver.",
        "The analytical gate uses equal viscosity and magnetic diffusivity so the damped Elsasser solution remains closed form.",
        "Passing G9 does not establish compressible MHD, general 2D/3D MHD, Hall-MHD, two-fluid, kinetic, plasma, adaptive electromagnetic control, laboratory, propulsion, shielding, stealth, cloaking, or operational capability.",
        "Passing G9 does not reproduce, validate, or refute any finite-time Navier-Stokes singularity construction.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG9Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.4 must remain SIMULATED_ONLY")
        if not all(
            (
                self.linearized_induction_equation_solved,
                self.linearized_lorentz_backreaction_solved,
                self.finite_rm_linear_reference_implemented,
                self.equal_diffusivity_reference,
            )
        ):
            raise ValueError("G9 report must represent the complete bounded linear finite-Rm reference")
        prohibited = (
            self.nonlinear_mhd_solver_claimed,
            self.compressible_mhd_solved,
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
            raise ValueError("WS-NSB v1.4 cannot promote unsupported nonlinear MHD, plasma, physical, singularity, or operational claims")
        return self


def _validate_grid(grid_size: int) -> None:
    if grid_size < 16 or grid_size % 2:
        raise ValueError("G9 requires an even periodic grid_size >= 16")


def _field_rms(values: list[float]) -> float:
    if not values:
        raise ValueError("field cannot be empty")
    return math.sqrt(sum(value * value for value in values) / len(values))


def _l2(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("fields must have equal nonzero length")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)) / len(left))


def _combined_l2(
    u_left: list[float],
    u_right: list[float],
    b_left: list[float],
    b_right: list[float],
) -> float:
    u_error = _l2(u_left, u_right)
    b_error = _l2(b_left, b_right)
    return math.sqrt(u_error * u_error + b_error * b_error)


def _energy(u: list[float], b: list[float]) -> tuple[float, float, float]:
    if len(u) != len(b) or not u:
        raise ValueError("velocity and magnetic fields must have equal nonzero length")
    kinetic = 0.5 * sum(value * value for value in u) / len(u)
    magnetic = 0.5 * sum(value * value for value in b) / len(b)
    return kinetic, magnetic, kinetic + magnetic


def _dx(values: list[float], spacing: float) -> list[float]:
    n = len(values)
    return [
        (values[(i + 1) % n] - values[(i - 1) % n]) / (2.0 * spacing)
        for i in range(n)
    ]


def _dxx(values: list[float], spacing: float) -> list[float]:
    n = len(values)
    inv_h2 = 1.0 / (spacing * spacing)
    return [
        (values[(i + 1) % n] - 2.0 * values[i] + values[(i - 1) % n]) * inv_h2
        for i in range(n)
    ]


def _rhs(
    u: list[float],
    b: list[float],
    *,
    spacing: float,
    alfven_speed: float,
    viscosity: float,
    magnetic_diffusivity: float,
) -> tuple[list[float], list[float]]:
    du = _dx(b, spacing)
    db = _dx(u, spacing)
    d2u = _dxx(u, spacing)
    d2b = _dxx(b, spacing)
    rhs_u = [
        alfven_speed * du_i + viscosity * d2u_i
        for du_i, d2u_i in zip(du, d2u, strict=True)
    ]
    rhs_b = [
        alfven_speed * db_i + magnetic_diffusivity * d2b_i
        for db_i, d2b_i in zip(db, d2b, strict=True)
    ]
    return rhs_u, rhs_b


def _add_scaled(values: list[float], increments: list[float], scale: float) -> list[float]:
    return [
        value + scale * increment
        for value, increment in zip(values, increments, strict=True)
    ]


def _rk4_step(
    u: list[float],
    b: list[float],
    *,
    dt: float,
    spacing: float,
    alfven_speed: float,
    viscosity: float,
    magnetic_diffusivity: float,
) -> tuple[list[float], list[float]]:
    k1u, k1b = _rhs(
        u,
        b,
        spacing=spacing,
        alfven_speed=alfven_speed,
        viscosity=viscosity,
        magnetic_diffusivity=magnetic_diffusivity,
    )
    k2u, k2b = _rhs(
        _add_scaled(u, k1u, 0.5 * dt),
        _add_scaled(b, k1b, 0.5 * dt),
        spacing=spacing,
        alfven_speed=alfven_speed,
        viscosity=viscosity,
        magnetic_diffusivity=magnetic_diffusivity,
    )
    k3u, k3b = _rhs(
        _add_scaled(u, k2u, 0.5 * dt),
        _add_scaled(b, k2b, 0.5 * dt),
        spacing=spacing,
        alfven_speed=alfven_speed,
        viscosity=viscosity,
        magnetic_diffusivity=magnetic_diffusivity,
    )
    k4u, k4b = _rhs(
        _add_scaled(u, k3u, dt),
        _add_scaled(b, k3b, dt),
        spacing=spacing,
        alfven_speed=alfven_speed,
        viscosity=viscosity,
        magnetic_diffusivity=magnetic_diffusivity,
    )
    u_next = [
        u_i + dt * (a + 2.0 * c + 2.0 * d + e) / 6.0
        for u_i, a, c, d, e in zip(u, k1u, k2u, k3u, k4u, strict=True)
    ]
    b_next = [
        b_i + dt * (a + 2.0 * c + 2.0 * d + e) / 6.0
        for b_i, a, c, d, e in zip(b, k1b, k2b, k3b, k4b, strict=True)
    ]
    return u_next, b_next


def _stability_limit(
    *,
    grid_size: int,
    alfven_speed: float,
    viscosity: float,
    magnetic_diffusivity: float,
) -> float:
    spacing = TWO_PI / grid_size
    wave_limit = math.inf if abs(alfven_speed) <= 1e-15 else 0.4 * spacing / abs(alfven_speed)
    max_diffusivity = max(viscosity, magnetic_diffusivity)
    diffusion_limit = math.inf if max_diffusivity <= 1e-15 else 0.5 * spacing * spacing / max_diffusivity
    return min(wave_limit, diffusion_limit)


def integrate_linear_alfven(
    *,
    initial_velocity: list[float],
    initial_magnetic: list[float],
    alfven_speed: float,
    viscosity: float,
    magnetic_diffusivity: float,
    dt: float,
    final_time: float,
) -> tuple[list[float], list[float], float, int]:
    if len(initial_velocity) != len(initial_magnetic):
        raise ValueError("initial velocity and magnetic fields must have matching lengths")
    grid_size = len(initial_velocity)
    _validate_grid(grid_size)
    if viscosity < 0.0 or magnetic_diffusivity < 0.0:
        raise ValueError("diffusivities must be nonnegative")
    if dt <= 0.0 or final_time <= 0.0:
        raise ValueError("dt and final_time must be positive")

    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    if effective_dt > _stability_limit(
        grid_size=grid_size,
        alfven_speed=alfven_speed,
        viscosity=viscosity,
        magnetic_diffusivity=magnetic_diffusivity,
    ):
        raise ValueError("requested timestep exceeds conservative G9 RK4 stability bound")

    spacing = TWO_PI / grid_size
    u = list(initial_velocity)
    b = list(initial_magnetic)
    for _ in range(steps):
        u, b = _rk4_step(
            u,
            b,
            dt=effective_dt,
            spacing=spacing,
            alfven_speed=alfven_speed,
            viscosity=viscosity,
            magnetic_diffusivity=magnetic_diffusivity,
        )
    return u, b, effective_dt, steps


def _initial_velocity_mode(grid_size: int, wavenumber: int) -> list[float]:
    _validate_grid(grid_size)
    if wavenumber <= 0 or 4 * wavenumber >= grid_size:
        raise ValueError("wavenumber must be positive and comfortably resolved")
    spacing = TWO_PI / grid_size
    return [math.sin(wavenumber * i * spacing) for i in range(grid_size)]


def _initial_magnetic_mode(grid_size: int, wavenumber: int) -> list[float]:
    _validate_grid(grid_size)
    if wavenumber <= 0 or 4 * wavenumber >= grid_size:
        raise ValueError("wavenumber must be positive and comfortably resolved")
    spacing = TWO_PI / grid_size
    return [math.cos(wavenumber * i * spacing) for i in range(grid_size)]


def _exact_alfven(
    *,
    grid_size: int,
    wavenumber: int,
    alfven_speed: float,
    diffusivity: float,
    time_value: float,
    semidiscrete: bool,
) -> tuple[list[float], list[float]]:
    _validate_grid(grid_size)
    spacing = TWO_PI / grid_size
    if semidiscrete:
        wave_number_effective = math.sin(wavenumber * spacing) / spacing
        laplacian_number = 4.0 * math.sin(0.5 * wavenumber * spacing) ** 2 / (spacing * spacing)
    else:
        wave_number_effective = float(wavenumber)
        laplacian_number = float(wavenumber * wavenumber)
    decay = math.exp(-diffusivity * laplacian_number * time_value)
    phase = alfven_speed * wave_number_effective * time_value
    u = [
        decay * math.sin(wavenumber * i * spacing) * math.cos(phase)
        for i in range(grid_size)
    ]
    b = [
        decay * math.cos(wavenumber * i * spacing) * math.sin(phase)
        for i in range(grid_size)
    ]
    return u, b


def _comparison_case(
    *,
    case_id: str,
    grid_size: int,
    wavenumber: int,
    alfven_speed: float,
    diffusivity: float,
    dt: float,
    final_time: float,
    semidiscrete_target: bool,
) -> G9ComparisonResult:
    initial_u = _initial_velocity_mode(grid_size, wavenumber)
    initial_b = [0.0] * grid_size
    numerical_u, numerical_b, effective_dt, steps = integrate_linear_alfven(
        initial_velocity=initial_u,
        initial_magnetic=initial_b,
        alfven_speed=alfven_speed,
        viscosity=diffusivity,
        magnetic_diffusivity=diffusivity,
        dt=dt,
        final_time=final_time,
    )
    exact_u, exact_b = _exact_alfven(
        grid_size=grid_size,
        wavenumber=wavenumber,
        alfven_speed=alfven_speed,
        diffusivity=diffusivity,
        time_value=final_time,
        semidiscrete=semidiscrete_target,
    )
    u_error = _l2(numerical_u, exact_u)
    b_error = _l2(numerical_b, exact_b)
    kinetic, magnetic, total = _energy(numerical_u, numerical_b)
    return G9ComparisonResult(
        case_id=case_id,
        grid_size=grid_size,
        wavenumber=wavenumber,
        alfven_speed=alfven_speed,
        viscosity=diffusivity,
        magnetic_diffusivity=diffusivity,
        final_time=final_time,
        requested_dt=dt,
        effective_dt=effective_dt,
        steps=steps,
        velocity_l2_error=u_error,
        magnetic_l2_error=b_error,
        combined_l2_error=math.sqrt(u_error * u_error + b_error * b_error),
        kinetic_energy=kinetic,
        magnetic_energy=magnetic,
        total_energy=total,
    )


def _observed_order(coarse_error: float, fine_error: float) -> float:
    if coarse_error <= 0.0 or fine_error <= 0.0:
        raise ValueError("convergence errors must be positive")
    return math.log(coarse_error / fine_error) / math.log(2.0)


def _transfer_case(
    *,
    grid_size: int,
    wavenumber: int,
    alfven_speed: float,
    diffusivity: float,
) -> G9TransferResult:
    if abs(alfven_speed) <= 1e-15 or diffusivity <= 0.0:
        raise ValueError("transfer reference requires nonzero Alfven speed and positive diffusivity")
    quarter_period = math.pi / (2.0 * wavenumber * abs(alfven_speed))
    spacing = TWO_PI / grid_size
    dt = 0.13 * spacing / abs(alfven_speed)
    initial_u = _initial_velocity_mode(grid_size, wavenumber)
    initial_b = [0.0] * grid_size
    kinetic_initial, magnetic_initial, total_initial = _energy(initial_u, initial_b)
    final_u, final_b, effective_dt, steps = integrate_linear_alfven(
        initial_velocity=initial_u,
        initial_magnetic=initial_b,
        alfven_speed=alfven_speed,
        viscosity=diffusivity,
        magnetic_diffusivity=diffusivity,
        dt=dt,
        final_time=quarter_period,
    )
    kinetic_final, magnetic_final, total_final = _energy(final_u, final_b)
    expected_total = total_initial * math.exp(
        -2.0 * diffusivity * wavenumber * wavenumber * quarter_period
    )
    return G9TransferResult(
        grid_size=grid_size,
        wavenumber=wavenumber,
        alfven_speed=alfven_speed,
        viscosity=diffusivity,
        magnetic_diffusivity=diffusivity,
        mode_magnetic_reynolds=abs(alfven_speed) / (diffusivity * wavenumber),
        quarter_period=quarter_period,
        effective_dt=effective_dt,
        steps=steps,
        kinetic_energy_initial=kinetic_initial,
        magnetic_energy_initial=magnetic_initial,
        kinetic_energy_final=kinetic_final,
        magnetic_energy_final=magnetic_final,
        total_energy_final=total_final,
        magnetic_energy_fraction_final=magnetic_final / max(total_final, 1e-15),
        expected_total_energy_continuum=expected_total,
        total_energy_relative_error=abs(total_final - expected_total) / max(expected_total, 1e-15),
    )


def _controls(
    *,
    grid_size: int,
    wavenumber: int,
    alfven_speed: float,
    diffusivity: float,
) -> G9ControlResult:
    spacing = TWO_PI / grid_size
    final_time = 0.25
    dt = 0.08 * spacing / max(abs(alfven_speed), 1.0)

    magnetic_initial = _initial_magnetic_mode(grid_size, wavenumber)
    zero_velocity = [0.0] * grid_size
    diffusion_u, diffusion_b, _, _ = integrate_linear_alfven(
        initial_velocity=zero_velocity,
        initial_magnetic=magnetic_initial,
        alfven_speed=0.0,
        viscosity=diffusivity,
        magnetic_diffusivity=diffusivity,
        dt=dt,
        final_time=final_time,
    )
    continuum_decay = math.exp(-diffusivity * wavenumber * wavenumber * final_time)
    exact_diffusion_b = [continuum_decay * value for value in magnetic_initial]

    initial_u = _initial_velocity_mode(grid_size, wavenumber)
    initial_b = [0.0] * grid_size
    positive_u, positive_b, _, _ = integrate_linear_alfven(
        initial_velocity=initial_u,
        initial_magnetic=initial_b,
        alfven_speed=abs(alfven_speed),
        viscosity=diffusivity,
        magnetic_diffusivity=diffusivity,
        dt=dt,
        final_time=final_time,
    )
    negative_u, negative_b, _, _ = integrate_linear_alfven(
        initial_velocity=initial_u,
        initial_magnetic=initial_b,
        alfven_speed=-abs(alfven_speed),
        viscosity=diffusivity,
        magnetic_diffusivity=diffusivity,
        dt=dt,
        final_time=final_time,
    )
    magnetic_antisymmetry = _l2(
        positive_b,
        [-value for value in negative_b],
    )

    zero_coupling_u, zero_coupling_b, _, _ = integrate_linear_alfven(
        initial_velocity=initial_u,
        initial_magnetic=initial_b,
        alfven_speed=0.0,
        viscosity=diffusivity,
        magnetic_diffusivity=diffusivity,
        dt=dt,
        final_time=final_time,
    )
    _ = zero_coupling_u

    return G9ControlResult(
        grid_size=grid_size,
        diffusion_only_magnetic_l2=_l2(diffusion_b, exact_diffusion_b),
        diffusion_only_velocity_rms=_field_rms(diffusion_u),
        alfven_sign_velocity_l2=_l2(positive_u, negative_u),
        alfven_sign_magnetic_antisymmetry_l2=magnetic_antisymmetry,
        zero_coupling_generated_magnetic_rms=_field_rms(zero_coupling_b),
    )


def run_nsb_g9_benchmark(
    *,
    spatial_grids: tuple[int, int, int] = (32, 64, 128),
    temporal_grid: int = 128,
    temporal_dts: tuple[float, float, float] = (0.016, 0.008, 0.004),
    wavenumber: int = 2,
    alfven_speed: float = 1.0,
    diffusivity: float = 0.02,
    spatial_final_time: float = 0.4,
    temporal_final_time: float = 0.32,
    spatial_order_floor: float = 1.9,
    finest_spatial_l2_limit: float = 1e-3,
    temporal_order_floor: float = 3.6,
    finest_temporal_l2_limit: float = 1e-9,
    transfer_magnetic_fraction_floor: float = 0.999,
    transfer_energy_relative_error_limit: float = 2e-4,
    diffusion_only_l2_limit: float = 5e-5,
    symmetry_limit: float = 1e-12,
) -> NSBG9Report:
    if diffusivity <= 0.0:
        raise ValueError("G9 analytical gate requires positive equal diffusivity")
    if abs(alfven_speed) <= 1e-15:
        raise ValueError("G9 analytical gate requires nonzero Alfven speed")
    if not (
        spatial_grids[1] == 2 * spatial_grids[0]
        and spatial_grids[2] == 2 * spatial_grids[1]
    ):
        raise ValueError("G9 spatial grids must refine by exactly two")
    if not (
        temporal_dts[0] == 2.0 * temporal_dts[1]
        and temporal_dts[1] == 2.0 * temporal_dts[2]
    ):
        raise ValueError("G9 temporal dts must halve exactly")
    for grid_size in (*spatial_grids, temporal_grid):
        _validate_grid(grid_size)

    spatial_cases = tuple(
        _comparison_case(
            case_id=f"continuum_spatial_n{grid_size}",
            grid_size=grid_size,
            wavenumber=wavenumber,
            alfven_speed=alfven_speed,
            diffusivity=diffusivity,
            dt=0.15 * (TWO_PI / grid_size) / abs(alfven_speed),
            final_time=spatial_final_time,
            semidiscrete_target=False,
        )
        for grid_size in spatial_grids
    )
    spatial_errors = tuple(case.combined_l2_error for case in spatial_cases)
    spatial_orders = (
        _observed_order(spatial_errors[0], spatial_errors[1]),
        _observed_order(spatial_errors[1], spatial_errors[2]),
    )

    temporal_cases = tuple(
        _comparison_case(
            case_id=f"semidiscrete_temporal_dt_{dt:g}",
            grid_size=temporal_grid,
            wavenumber=wavenumber,
            alfven_speed=alfven_speed,
            diffusivity=diffusivity,
            dt=dt,
            final_time=temporal_final_time,
            semidiscrete_target=True,
        )
        for dt in temporal_dts
    )
    temporal_errors = tuple(case.combined_l2_error for case in temporal_cases)
    temporal_orders = (
        _observed_order(temporal_errors[0], temporal_errors[1]),
        _observed_order(temporal_errors[1], temporal_errors[2]),
    )

    transfer = _transfer_case(
        grid_size=temporal_grid,
        wavenumber=wavenumber,
        alfven_speed=alfven_speed,
        diffusivity=diffusivity,
    )
    controls = _controls(
        grid_size=temporal_grid,
        wavenumber=wavenumber,
        alfven_speed=alfven_speed,
        diffusivity=diffusivity,
    )

    spatial_pass = (
        min(spatial_orders) >= spatial_order_floor
        and spatial_errors[-1] <= finest_spatial_l2_limit
    )
    temporal_pass = (
        min(temporal_orders) >= temporal_order_floor
        and temporal_errors[-1] <= finest_temporal_l2_limit
    )
    transfer_pass = (
        transfer.mode_magnetic_reynolds > 1.0
        and transfer.magnetic_energy_fraction_final >= transfer_magnetic_fraction_floor
        and transfer.total_energy_relative_error <= transfer_energy_relative_error_limit
    )
    diffusion_pass = (
        controls.diffusion_only_magnetic_l2 <= diffusion_only_l2_limit
        and controls.diffusion_only_velocity_rms <= symmetry_limit
    )
    sign_pass = (
        controls.alfven_sign_velocity_l2 <= symmetry_limit
        and controls.alfven_sign_magnetic_antisymmetry_l2 <= symmetry_limit
    )
    zero_coupling_pass = controls.zero_coupling_generated_magnetic_rms <= symmetry_limit
    acceptance_pass = all(
        (
            spatial_pass,
            temporal_pass,
            transfer_pass,
            diffusion_pass,
            sign_pass,
            zero_coupling_pass,
        )
    )

    report = NSBG9Report(
        spatial_cases=spatial_cases,
        temporal_cases=temporal_cases,
        transfer_result=transfer,
        controls=controls,
        acceptance=G9AcceptanceSummary(
            spatial_order_floor=spatial_order_floor,
            spatial_orders=spatial_orders,
            finest_spatial_l2_limit=finest_spatial_l2_limit,
            temporal_order_floor=temporal_order_floor,
            temporal_orders=temporal_orders,
            finest_temporal_l2_limit=finest_temporal_l2_limit,
            transfer_magnetic_fraction_floor=transfer_magnetic_fraction_floor,
            transfer_energy_relative_error_limit=transfer_energy_relative_error_limit,
            diffusion_only_l2_limit=diffusion_only_l2_limit,
            symmetry_limit=symmetry_limit,
            spatial_convergence_pass=spatial_pass,
            temporal_convergence_pass=temporal_pass,
            alfven_transfer_pass=transfer_pass,
            diffusion_only_pass=diffusion_pass,
            sign_symmetry_pass=sign_pass,
            zero_coupling_pass=zero_coupling_pass,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g9_report(report: NSBG9Report) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
