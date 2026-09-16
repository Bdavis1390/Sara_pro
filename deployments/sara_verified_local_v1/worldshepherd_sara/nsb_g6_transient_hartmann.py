from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


class TransientHartmannCaseResult(BaseModel):
    case_id: str
    hartmann: float = Field(ge=0.0)
    grid_size: int = Field(ge=5)
    requested_dt: float = Field(gt=0.0)
    effective_dt: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    l2_velocity_error: float = Field(ge=0.0)
    linf_velocity_error: float = Field(ge=0.0)
    centerline_velocity: float
    mean_velocity: float
    kinetic_energy_final: float = Field(ge=0.0)
    cumulative_forcing_work: float = Field(ge=0.0)
    cumulative_viscous_dissipation: float = Field(ge=0.0)
    cumulative_em_dissipation: float = Field(ge=0.0)
    energy_budget_abs_residual: float = Field(ge=0.0)
    max_step_energy_budget_abs_residual: float = Field(ge=0.0)


class G6ConvergenceSummary(BaseModel):
    spatial_hartmann: float = Field(gt=0.0)
    spatial_grids: tuple[int, int, int]
    spatial_errors: tuple[float, float, float]
    spatial_orders: tuple[float, float]
    spatial_order_floor: float = Field(gt=0.0)
    temporal_hartmann: float = Field(gt=0.0)
    temporal_grid_size: int = Field(ge=5)
    temporal_dts: tuple[float, float, float]
    temporal_effective_dts: tuple[float, float, float]
    temporal_errors: tuple[float, float, float]
    temporal_orders: tuple[float, float]
    temporal_order_floor: float = Field(gt=0.0)


class G6AcceptanceSummary(BaseModel):
    spatial_convergence_pass: bool
    temporal_convergence_pass: bool
    transient_profile_accuracy_pass: bool
    energy_budget_pass: bool
    zero_field_em_sink_pass: bool
    field_sign_symmetry_pass: bool
    monotonic_magnetic_damping_pass: bool
    positive_em_dissipation_pass: bool
    steady_limit_consistency_pass: bool
    finest_spatial_l2_limit: float = Field(gt=0.0)
    finest_temporal_l2_limit: float = Field(gt=0.0)
    energy_budget_abs_residual_limit: float = Field(gt=0.0)
    zero_field_em_sink_limit: float = Field(gt=0.0)
    field_sign_symmetry_l2_limit: float = Field(gt=0.0)
    steady_limit_l2_limit: float = Field(gt=0.0)
    field_sign_symmetry_l2: float = Field(ge=0.0)
    steady_limit_l2: float = Field(ge=0.0)
    acceptance_pass: bool


class NSBG6Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G6-001"
    benchmark_version: str = "1.1"
    formulation: str = "transient 1D quasi-static Hartmann channel-flow reference"
    normalized_equation: str = "du/dt = d2u/dy2 - Ha^2 u + 1 on y in [-1,1], u(+/-1,t)=0, u(y,0)=0"
    numerical_method: str = "Crank-Nicolson second-order centered finite differences with tridiagonal solve"
    exact_reference: str = "Dirichlet sine-series transient solution"
    energy_identity: str = "Delta E = W_forcing - D_viscous - D_EM"
    cases: tuple[TransientHartmannCaseResult, ...]
    convergence: G6ConvergenceSummary
    acceptance: G6AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    transient_quasi_static_hartmann_reference_solved: bool = True
    discrete_energy_budget_checked: bool = True
    zero_field_control_checked: bool = True
    field_sign_symmetry_checked: bool = True
    steady_g5_limit_checked: bool = True
    full_mhd_solver_claimed: bool = False
    induction_equation_solved: bool = False
    two_or_three_dimensional_mhd_claimed: bool = False
    hall_two_fluid_or_kinetic_solved: bool = False
    plasma_solved: bool = False
    adaptive_em_control_validated: bool = False
    laboratory_validation_performed: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G6 solves only a transient 1D quasi-static Hartmann reference with an imposed-field linear damping term.",
        "The magnetic contribution is validated as a bounded energy sink in this reduced reference; no induction equation or general MHD capability is established.",
        "Cross-checking the long-time limit against the steady G5 analytical profile does not constitute independent external validation.",
        "No Hall-MHD, two-fluid, kinetic, plasma, adaptive electromagnetic control, laboratory, propulsion, shielding, stealth, cloaking, or operational capability is established.",
        "Passing G6 does not reproduce, validate, or refute any finite-time Navier-Stokes singularity construction.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG6Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.1 must remain SIMULATED_ONLY")
        required = (
            self.transient_quasi_static_hartmann_reference_solved,
            self.discrete_energy_budget_checked,
            self.zero_field_control_checked,
            self.field_sign_symmetry_checked,
            self.steady_g5_limit_checked,
        )
        if not all(required):
            raise ValueError("G6 report must represent the complete bounded transient reference gate")
        prohibited = (
            self.full_mhd_solver_claimed,
            self.induction_equation_solved,
            self.two_or_three_dimensional_mhd_claimed,
            self.hall_two_fluid_or_kinetic_solved,
            self.plasma_solved,
            self.adaptive_em_control_validated,
            self.laboratory_validation_performed,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v1.1 cannot promote unsupported MHD, plasma, physical, or operational claims")
        return self


def _require_grid(grid_size: int) -> None:
    if grid_size < 5 or grid_size % 2 == 0:
        raise ValueError("transient Hartmann reference requires an odd grid_size >= 5")


def _solve_tridiagonal(
    lower: list[float],
    diagonal: list[float],
    upper: list[float],
    rhs: list[float],
) -> list[float]:
    size = len(diagonal)
    if size == 0 or len(rhs) != size:
        raise ValueError("invalid tridiagonal system")
    c_prime = [0.0] * max(0, size - 1)
    d_prime = [0.0] * size
    if size > 1:
        c_prime[0] = upper[0] / diagonal[0]
    d_prime[0] = rhs[0] / diagonal[0]
    for index in range(1, size):
        denominator = diagonal[index] - lower[index - 1] * c_prime[index - 1]
        if abs(denominator) <= 1e-15:
            raise ValueError("degenerate transient Hartmann tridiagonal system")
        if index < size - 1:
            c_prime[index] = upper[index] / denominator
        d_prime[index] = (rhs[index] - lower[index - 1] * d_prime[index - 1]) / denominator

    solution = [0.0] * size
    solution[-1] = d_prime[-1]
    for index in range(size - 2, -1, -1):
        solution[index] = d_prime[index] - c_prime[index] * solution[index + 1]
    return solution


def transient_hartmann_exact_velocity(
    y: float,
    hartmann: float,
    time_value: float,
    *,
    series_terms: int = 256,
) -> float:
    if time_value < 0.0:
        raise ValueError("time_value must be nonnegative")
    if series_terms < 8:
        raise ValueError("series_terms must be >= 8")
    if time_value == 0.0:
        return 0.0
    ha = abs(hartmann)
    x = 0.5 * (y + 1.0)
    total = 0.0
    for index in range(series_terms):
        n = 2 * index + 1
        eigenvalue = (0.5 * n * math.pi) ** 2 + ha * ha
        forcing_coefficient = 4.0 / (n * math.pi)
        transient_factor = 1.0 - math.exp(-eigenvalue * time_value)
        total += (
            forcing_coefficient
            * transient_factor
            * math.sin(n * math.pi * x)
            / eigenvalue
        )
    return total


def steady_hartmann_exact_velocity(y: float, hartmann: float) -> float:
    if abs(y) > 1.0:
        raise ValueError("steady Hartmann reference requires y in [-1, 1]")
    ha = abs(hartmann)
    if ha == 0.0:
        return 0.5 * (1.0 - y * y)
    if ha < 20.0:
        cosh_ratio = math.cosh(ha * y) / math.cosh(ha)
    else:
        absolute_y = abs(y)
        cosh_ratio = (
            math.exp(ha * (absolute_y - 1.0))
            + math.exp(-ha * (absolute_y + 1.0))
        ) / (1.0 + math.exp(-2.0 * ha))
    return (1.0 - cosh_ratio) / ha / ha


def _crank_nicolson_step(
    velocity: list[float],
    *,
    hartmann: float,
    dt: float,
    dy: float,
) -> list[float]:
    ha = abs(hartmann)
    interior = len(velocity) - 2
    ratio = dt / (2.0 * dy * dy)
    damping_half = 0.5 * dt * ha * ha

    lower = [-ratio] * (interior - 1)
    diagonal = [1.0 + 2.0 * ratio + damping_half] * interior
    upper = [-ratio] * (interior - 1)
    rhs: list[float] = []

    for index in range(1, len(velocity) - 1):
        rhs.append(
            (1.0 - 2.0 * ratio - damping_half) * velocity[index]
            + ratio * (velocity[index - 1] + velocity[index + 1])
            + dt
        )

    interior_solution = _solve_tridiagonal(lower, diagonal, upper, rhs)
    return [0.0, *interior_solution, 0.0]


def _kinetic_energy(values: list[float], dy: float) -> float:
    return 0.5 * dy * sum(value * value for value in values[1:-1])


def _mean_velocity(values: list[float], dy: float) -> float:
    integral = dy * (0.5 * values[0] + sum(values[1:-1]) + 0.5 * values[-1])
    return integral / 2.0


def _l2_difference(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("profile lengths must match")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)) / len(left))


def _linf_difference(left: list[float], right: list[float]) -> float:
    return max(abs(a - b) for a, b in zip(left, right, strict=True))


def integrate_transient_hartmann(
    *,
    hartmann: float,
    grid_size: int,
    dt: float,
    final_time: float,
) -> tuple[list[float], float, int, dict[str, float]]:
    _require_grid(grid_size)
    if dt <= 0.0 or final_time <= 0.0:
        raise ValueError("dt and final_time must be positive")

    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    dy = 2.0 / (grid_size - 1)
    velocity = [0.0] * grid_size

    forcing_work = 0.0
    viscous_dissipation = 0.0
    em_dissipation = 0.0
    max_step_residual = 0.0
    initial_energy = _kinetic_energy(velocity, dy)

    for _ in range(steps):
        next_velocity = _crank_nicolson_step(
            velocity,
            hartmann=hartmann,
            dt=effective_dt,
            dy=dy,
        )
        midpoint = [
            0.5 * (before + after)
            for before, after in zip(velocity, next_velocity, strict=True)
        ]
        before_energy = _kinetic_energy(velocity, dy)
        after_energy = _kinetic_energy(next_velocity, dy)
        forcing_power = dy * sum(midpoint[1:-1])
        viscous_power = sum(
            (midpoint[index + 1] - midpoint[index]) ** 2
            for index in range(grid_size - 1)
        ) / dy
        em_power = abs(hartmann) ** 2 * dy * sum(
            value * value for value in midpoint[1:-1]
        )
        step_residual = abs(
            (after_energy - before_energy)
            - effective_dt * (forcing_power - viscous_power - em_power)
        )
        max_step_residual = max(max_step_residual, step_residual)
        forcing_work += effective_dt * forcing_power
        viscous_dissipation += effective_dt * viscous_power
        em_dissipation += effective_dt * em_power
        velocity = next_velocity

    final_energy = _kinetic_energy(velocity, dy)
    cumulative_residual = abs(
        (final_energy - initial_energy)
        - (forcing_work - viscous_dissipation - em_dissipation)
    )
    return velocity, effective_dt, steps, {
        "kinetic_energy_final": final_energy,
        "cumulative_forcing_work": forcing_work,
        "cumulative_viscous_dissipation": viscous_dissipation,
        "cumulative_em_dissipation": em_dissipation,
        "energy_budget_abs_residual": cumulative_residual,
        "max_step_energy_budget_abs_residual": max_step_residual,
    }


def _case_result(
    *,
    case_id: str,
    hartmann: float,
    grid_size: int,
    dt: float,
    final_time: float,
) -> tuple[TransientHartmannCaseResult, list[float]]:
    numerical, effective_dt, steps, budget = integrate_transient_hartmann(
        hartmann=hartmann,
        grid_size=grid_size,
        dt=dt,
        final_time=final_time,
    )
    dy = 2.0 / (grid_size - 1)
    y = [-1.0 + index * dy for index in range(grid_size)]
    exact = [
        transient_hartmann_exact_velocity(value, hartmann, final_time)
        for value in y
    ]
    center = grid_size // 2
    return (
        TransientHartmannCaseResult(
            case_id=case_id,
            hartmann=abs(hartmann),
            grid_size=grid_size,
            requested_dt=dt,
            effective_dt=effective_dt,
            final_time=final_time,
            steps=steps,
            l2_velocity_error=_l2_difference(numerical, exact),
            linf_velocity_error=_linf_difference(numerical, exact),
            centerline_velocity=numerical[center],
            mean_velocity=_mean_velocity(numerical, dy),
            **budget,
        ),
        numerical,
    )


def _observed_order(
    coarse_error: float,
    fine_error: float,
    refinement_ratio: float = 2.0,
) -> float:
    if coarse_error <= 0.0 or fine_error <= 0.0:
        raise ValueError("convergence errors must be positive")
    if refinement_ratio <= 1.0:
        raise ValueError("refinement_ratio must be greater than one")
    return math.log(coarse_error / fine_error) / math.log(refinement_ratio)


def run_nsb_g6_benchmark(
    *,
    sweep_hartmann: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0, 5.0, 10.0),
    sweep_grid_size: int = 129,
    sweep_dt: float = 0.002,
    sweep_final_time: float = 0.2,
    spatial_hartmann: float = 2.0,
    spatial_grids: tuple[int, int, int] = (33, 65, 129),
    spatial_dt: float = 0.0005,
    spatial_final_time: float = 0.2,
    temporal_hartmann: float = 2.0,
    temporal_grid_size: int = 513,
    temporal_dts: tuple[float, float, float] = (0.08, 0.04, 0.02),
    temporal_final_time: float = 0.4,
    spatial_order_floor: float = 1.8,
    temporal_order_floor: float = 1.8,
    finest_spatial_l2_limit: float = 1e-5,
    finest_temporal_l2_limit: float = 5e-5,
    energy_budget_abs_residual_limit: float = 1e-10,
    zero_field_em_sink_limit: float = 1e-14,
    field_sign_symmetry_l2_limit: float = 1e-14,
    steady_limit_l2_limit: float = 1e-5,
) -> NSBG6Report:
    _require_grid(sweep_grid_size)
    _require_grid(temporal_grid_size)
    if (
        len(sweep_hartmann) < 2
        or sweep_hartmann[0] != 0.0
        or tuple(sorted(sweep_hartmann)) != sweep_hartmann
        or not any(value > 0.0 for value in sweep_hartmann[1:])
    ):
        raise ValueError(
            "sweep_hartmann must be sorted, begin with zero, and include a positive field case"
        )
    if any(value < 0.0 for value in sweep_hartmann):
        raise ValueError("sweep_hartmann values must be nonnegative")
    if spatial_grids[1] != 2 * spatial_grids[0] - 1 or spatial_grids[2] != 2 * spatial_grids[1] - 1:
        raise ValueError("spatial grids must halve spacing exactly")
    if not (temporal_dts[0] == 2.0 * temporal_dts[1] and temporal_dts[1] == 2.0 * temporal_dts[2]):
        raise ValueError("temporal dts must halve exactly")

    cases = tuple(
        _case_result(
            case_id=f"transient_ha_{value:g}",
            hartmann=value,
            grid_size=sweep_grid_size,
            dt=sweep_dt,
            final_time=sweep_final_time,
        )[0]
        for value in sweep_hartmann
    )

    spatial_cases = tuple(
        _case_result(
            case_id=f"spatial_ha_{spatial_hartmann:g}_n_{grid}",
            hartmann=spatial_hartmann,
            grid_size=grid,
            dt=spatial_dt,
            final_time=spatial_final_time,
        )[0]
        for grid in spatial_grids
    )
    spatial_errors = tuple(item.l2_velocity_error for item in spatial_cases)
    spatial_orders = (
        _observed_order(spatial_errors[0], spatial_errors[1]),
        _observed_order(spatial_errors[1], spatial_errors[2]),
    )

    temporal_cases = tuple(
        _case_result(
            case_id=f"temporal_ha_{temporal_hartmann:g}_dt_{dt:g}",
            hartmann=temporal_hartmann,
            grid_size=temporal_grid_size,
            dt=dt,
            final_time=temporal_final_time,
        )[0]
        for dt in temporal_dts
    )
    temporal_errors = tuple(item.l2_velocity_error for item in temporal_cases)
    temporal_orders = (
        _observed_order(
            temporal_errors[0],
            temporal_errors[1],
            temporal_cases[0].effective_dt / temporal_cases[1].effective_dt,
        ),
        _observed_order(
            temporal_errors[1],
            temporal_errors[2],
            temporal_cases[1].effective_dt / temporal_cases[2].effective_dt,
        ),
    )

    _, positive = _case_result(
        case_id="sign_positive",
        hartmann=spatial_hartmann,
        grid_size=sweep_grid_size,
        dt=sweep_dt,
        final_time=sweep_final_time,
    )
    _, negative = _case_result(
        case_id="sign_negative",
        hartmann=-spatial_hartmann,
        grid_size=sweep_grid_size,
        dt=sweep_dt,
        final_time=sweep_final_time,
    )
    sign_symmetry_l2 = _l2_difference(positive, negative)

    long_time, _, _, _ = integrate_transient_hartmann(
        hartmann=spatial_hartmann,
        grid_size=sweep_grid_size,
        dt=0.01,
        final_time=3.0,
    )
    dy = 2.0 / (sweep_grid_size - 1)
    y = [-1.0 + index * dy for index in range(sweep_grid_size)]
    steady_exact = [
        steady_hartmann_exact_velocity(value, spatial_hartmann)
        for value in y
    ]
    steady_limit_l2 = _l2_difference(long_time, steady_exact)

    centerlines = tuple(case.centerline_velocity for case in cases)
    means = tuple(case.mean_velocity for case in cases)
    monotonic = all(
        centerlines[index + 1] < centerlines[index]
        and means[index + 1] < means[index]
        for index in range(len(cases) - 1)
    )

    zero_field = cases[0]
    spatial_pass = (
        min(spatial_orders) >= spatial_order_floor
        and spatial_errors[-1] <= finest_spatial_l2_limit
    )
    temporal_pass = (
        min(temporal_orders) >= temporal_order_floor
        and temporal_errors[-1] <= finest_temporal_l2_limit
    )
    profile_accuracy_pass = max(case.l2_velocity_error for case in cases) <= finest_spatial_l2_limit
    all_budget_cases = (*cases, *spatial_cases, *temporal_cases)
    energy_budget_pass = max(
        case.energy_budget_abs_residual for case in all_budget_cases
    ) <= energy_budget_abs_residual_limit
    zero_field_pass = zero_field.cumulative_em_dissipation <= zero_field_em_sink_limit
    symmetry_pass = sign_symmetry_l2 <= field_sign_symmetry_l2_limit
    positive_em_pass = all(
        case.cumulative_em_dissipation > zero_field_em_sink_limit
        for case in cases[1:]
    )
    steady_pass = steady_limit_l2 <= steady_limit_l2_limit
    acceptance_pass = (
        spatial_pass
        and temporal_pass
        and profile_accuracy_pass
        and energy_budget_pass
        and zero_field_pass
        and symmetry_pass
        and monotonic
        and positive_em_pass
        and steady_pass
    )

    report = NSBG6Report(
        cases=cases,
        convergence=G6ConvergenceSummary(
            spatial_hartmann=spatial_hartmann,
            spatial_grids=spatial_grids,
            spatial_errors=spatial_errors,
            spatial_orders=spatial_orders,
            spatial_order_floor=spatial_order_floor,
            temporal_hartmann=temporal_hartmann,
            temporal_grid_size=temporal_grid_size,
            temporal_dts=temporal_dts,
            temporal_effective_dts=tuple(case.effective_dt for case in temporal_cases),
            temporal_errors=temporal_errors,
            temporal_orders=temporal_orders,
            temporal_order_floor=temporal_order_floor,
        ),
        acceptance=G6AcceptanceSummary(
            spatial_convergence_pass=spatial_pass,
            temporal_convergence_pass=temporal_pass,
            transient_profile_accuracy_pass=profile_accuracy_pass,
            energy_budget_pass=energy_budget_pass,
            zero_field_em_sink_pass=zero_field_pass,
            field_sign_symmetry_pass=symmetry_pass,
            monotonic_magnetic_damping_pass=monotonic,
            positive_em_dissipation_pass=positive_em_pass,
            steady_limit_consistency_pass=steady_pass,
            finest_spatial_l2_limit=finest_spatial_l2_limit,
            finest_temporal_l2_limit=finest_temporal_l2_limit,
            energy_budget_abs_residual_limit=energy_budget_abs_residual_limit,
            zero_field_em_sink_limit=zero_field_em_sink_limit,
            field_sign_symmetry_l2_limit=field_sign_symmetry_l2_limit,
            steady_limit_l2_limit=steady_limit_l2_limit,
            field_sign_symmetry_l2=sign_symmetry_l2,
            steady_limit_l2=steady_limit_l2,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g6_report(report: NSBG6Report) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
