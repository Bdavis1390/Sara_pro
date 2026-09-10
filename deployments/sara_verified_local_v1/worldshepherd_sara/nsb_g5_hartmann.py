from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


class HartmannCaseResult(BaseModel):
    case_id: str
    hartmann: float = Field(ge=0.0)
    grid_size: int = Field(ge=5)
    l2_velocity_error: float = Field(ge=0.0)
    linf_velocity_error: float = Field(ge=0.0)
    centerline_velocity: float = Field(ge=0.0)
    centerline_velocity_exact: float = Field(ge=0.0)
    mean_velocity: float = Field(ge=0.0)
    mean_velocity_exact: float = Field(ge=0.0)
    mean_velocity_relative_error: float = Field(ge=0.0)
    normalized_flow_retention_vs_hydrodynamic: float = Field(ge=0.0)


class HartmannConvergenceSummary(BaseModel):
    hartmann: float = Field(gt=0.0)
    grid_sizes: tuple[int, int, int]
    l2_errors: tuple[float, float, float]
    observed_orders: tuple[float, float]
    spatial_order_floor: float = Field(gt=0.0)
    finest_l2_limit: float = Field(gt=0.0)


class G5AcceptanceSummary(BaseModel):
    spatial_order_pass: bool
    zero_field_hydrodynamic_limit_pass: bool
    field_sign_symmetry_pass: bool
    monotonic_magnetic_damping_pass: bool
    profile_accuracy_pass: bool
    flow_rate_accuracy_pass: bool
    zero_field_l2_limit: float = Field(gt=0.0)
    field_sign_symmetry_l2_limit: float = Field(gt=0.0)
    mean_velocity_relative_error_limit: float = Field(gt=0.0)
    field_sign_symmetry_l2: float = Field(ge=0.0)
    acceptance_pass: bool


class NSBG5Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G5-001"
    benchmark_version: str = "1.0"
    formulation: str = "steady 1D quasi-static Hartmann channel-flow reference"
    normalized_equation: str = "d2u/dy2 - Ha^2 u = -1 on y in [-1,1], u(-1)=u(1)=0"
    numerical_method: str = "second-order centered finite-difference tridiagonal solve"
    literature_regime: str = "low magnetic Reynolds number / imposed transverse magnetic field"
    cases: tuple[HartmannCaseResult, ...]
    convergence: HartmannConvergenceSummary
    acceptance: G5AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    quasi_static_hartmann_reference_solved: bool = True
    zero_field_hydrodynamic_limit_checked: bool = True
    magnetic_field_sign_symmetry_checked: bool = True
    full_mhd_solver_claimed: bool = False
    induction_equation_solved: bool = False
    hall_two_fluid_or_kinetic_solved: bool = False
    plasma_solved: bool = False
    three_dimensional_solver_claimed: bool = False
    laboratory_validation_performed: bool = False
    adaptive_em_control_validated: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G5 solves only the classical steady 1D quasi-static Hartmann reference equation for a fixed pressure-gradient normalization.",
        "The benchmark validates a bounded Lorentz-damping source-term reference and its hydrodynamic Ha=0 limit; it is not a general MHD solver.",
        "No induction equation, Hall-MHD, two-fluid, kinetic, plasma, adaptive electromagnetic control, laboratory, propulsion, shielding, stealth, cloaking, or operational capability is established.",
        "Passing G5 does not reproduce, validate, or refute any finite-time Navier-Stokes singularity construction.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG5Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.0 must remain SIMULATED_ONLY")
        if not self.quasi_static_hartmann_reference_solved:
            raise ValueError("G5 must represent an executed quasi-static Hartmann reference solve")
        if not self.zero_field_hydrodynamic_limit_checked or not self.magnetic_field_sign_symmetry_checked:
            raise ValueError("G5 requires zero-field and field-sign controls")
        prohibited = (
            self.full_mhd_solver_claimed,
            self.induction_equation_solved,
            self.hall_two_fluid_or_kinetic_solved,
            self.plasma_solved,
            self.three_dimensional_solver_claimed,
            self.laboratory_validation_performed,
            self.adaptive_em_control_validated,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v1.0 cannot promote unsupported MHD, plasma, physical, or operational claims")
        return self


def _require_grid(grid_size: int) -> None:
    if grid_size < 5 or grid_size % 2 == 0:
        raise ValueError("Hartmann reference requires an odd grid_size >= 5")


def hartmann_exact_velocity(y: float, hartmann: float) -> float:
    ha = abs(hartmann)
    if ha == 0.0:
        return 0.5 * (1.0 - y * y)
    return (1.0 - math.cosh(ha * y) / math.cosh(ha)) / (ha * ha)


def hartmann_exact_mean_velocity(hartmann: float) -> float:
    ha = abs(hartmann)
    if ha == 0.0:
        return 1.0 / 3.0
    return (1.0 - math.tanh(ha) / ha) / (ha * ha)


def solve_hartmann_fd(
    *,
    hartmann: float,
    grid_size: int,
) -> tuple[list[float], list[float]]:
    _require_grid(grid_size)
    ha = abs(hartmann)
    dy = 2.0 / (grid_size - 1)
    interior = grid_size - 2
    offdiag = 1.0 / (dy * dy)
    diagonal = -2.0 * offdiag - ha * ha

    lower = [offdiag] * (interior - 1)
    main = [diagonal] * interior
    upper = [offdiag] * (interior - 1)
    rhs = [-1.0] * interior

    c_prime = [0.0] * max(0, interior - 1)
    d_prime = [0.0] * interior
    if interior > 1:
        c_prime[0] = upper[0] / main[0]
    d_prime[0] = rhs[0] / main[0]

    for index in range(1, interior):
        denominator = main[index] - lower[index - 1] * c_prime[index - 1]
        if abs(denominator) <= 1e-15:
            raise ValueError("degenerate Hartmann tridiagonal system")
        if index < interior - 1:
            c_prime[index] = upper[index] / denominator
        d_prime[index] = (rhs[index] - lower[index - 1] * d_prime[index - 1]) / denominator

    interior_solution = [0.0] * interior
    interior_solution[-1] = d_prime[-1]
    for index in range(interior - 2, -1, -1):
        interior_solution[index] = d_prime[index] - c_prime[index] * interior_solution[index + 1]

    y = [-1.0 + index * dy for index in range(grid_size)]
    velocity = [0.0, *interior_solution, 0.0]
    return y, velocity


def _l2_difference(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("profile lengths must match")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)) / len(left))


def _linf_difference(left: list[float], right: list[float]) -> float:
    return max(abs(a - b) for a, b in zip(left, right, strict=True))


def _trapezoid_mean(y: list[float], values: list[float]) -> float:
    if len(y) != len(values) or len(y) < 2:
        raise ValueError("invalid profile for trapezoidal mean")
    dy = y[1] - y[0]
    integral = dy * (0.5 * values[0] + sum(values[1:-1]) + 0.5 * values[-1])
    return integral / 2.0


def _case_result(*, case_id: str, hartmann: float, grid_size: int) -> HartmannCaseResult:
    y, numerical = solve_hartmann_fd(hartmann=hartmann, grid_size=grid_size)
    exact = [hartmann_exact_velocity(value, hartmann) for value in y]
    center_index = grid_size // 2
    mean_numerical = _trapezoid_mean(y, numerical)
    mean_exact = hartmann_exact_mean_velocity(hartmann)
    hydro_mean = hartmann_exact_mean_velocity(0.0)
    return HartmannCaseResult(
        case_id=case_id,
        hartmann=abs(hartmann),
        grid_size=grid_size,
        l2_velocity_error=_l2_difference(numerical, exact),
        linf_velocity_error=_linf_difference(numerical, exact),
        centerline_velocity=numerical[center_index],
        centerline_velocity_exact=hartmann_exact_velocity(0.0, hartmann),
        mean_velocity=mean_numerical,
        mean_velocity_exact=mean_exact,
        mean_velocity_relative_error=abs(mean_numerical - mean_exact) / max(abs(mean_exact), 1e-15),
        normalized_flow_retention_vs_hydrodynamic=mean_numerical / hydro_mean,
    )


def _observed_order(coarse_error: float, fine_error: float) -> float:
    if coarse_error <= 0.0 or fine_error <= 0.0:
        raise ValueError("convergence errors must be positive")
    return math.log(coarse_error / fine_error) / math.log(2.0)


def run_nsb_g5_benchmark(
    *,
    sweep_hartmann: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0, 5.0, 10.0),
    sweep_grid_size: int = 129,
    convergence_hartmann: float = 2.0,
    convergence_grids: tuple[int, int, int] = (33, 65, 129),
    spatial_order_floor: float = 1.8,
    finest_l2_limit: float = 1e-5,
    zero_field_l2_limit: float = 1e-12,
    field_sign_symmetry_l2_limit: float = 1e-14,
    mean_velocity_relative_error_limit: float = 5e-4,
) -> NSBG5Report:
    _require_grid(sweep_grid_size)
    if any(value < 0.0 for value in sweep_hartmann):
        raise ValueError("sweep_hartmann values must be nonnegative")
    if tuple(sorted(sweep_hartmann)) != sweep_hartmann or not sweep_hartmann or sweep_hartmann[0] != 0.0:
        raise ValueError("sweep_hartmann must be sorted and begin with zero")
    if convergence_grids[1] != 2 * convergence_grids[0] - 1 or convergence_grids[2] != 2 * convergence_grids[1] - 1:
        raise ValueError("convergence grids must halve spacing exactly")

    cases = tuple(
        _case_result(case_id=f"hartmann_{value:g}", hartmann=value, grid_size=sweep_grid_size)
        for value in sweep_hartmann
    )
    convergence_cases = tuple(
        _case_result(
            case_id=f"convergence_ha_{convergence_hartmann:g}_n_{grid}",
            hartmann=convergence_hartmann,
            grid_size=grid,
        )
        for grid in convergence_grids
    )
    errors = tuple(item.l2_velocity_error for item in convergence_cases)
    orders = (_observed_order(errors[0], errors[1]), _observed_order(errors[1], errors[2]))

    y_positive, positive = solve_hartmann_fd(hartmann=convergence_hartmann, grid_size=sweep_grid_size)
    y_negative, negative = solve_hartmann_fd(hartmann=-convergence_hartmann, grid_size=sweep_grid_size)
    if y_positive != y_negative:
        raise ValueError("field-sign symmetry grids do not match")
    sign_symmetry = _l2_difference(positive, negative)

    centerlines = tuple(case.centerline_velocity for case in cases)
    means = tuple(case.mean_velocity for case in cases)
    monotonic = all(centerlines[index + 1] < centerlines[index] for index in range(len(centerlines) - 1)) and all(
        means[index + 1] < means[index] for index in range(len(means) - 1)
    )
    zero_field = cases[0]
    spatial_pass = min(orders) >= spatial_order_floor and errors[-1] <= finest_l2_limit
    zero_field_pass = zero_field.l2_velocity_error <= zero_field_l2_limit
    symmetry_pass = sign_symmetry <= field_sign_symmetry_l2_limit
    profile_accuracy_pass = all(case.l2_velocity_error <= finest_l2_limit for case in cases[1:])
    flow_rate_accuracy_pass = max(case.mean_velocity_relative_error for case in cases) <= mean_velocity_relative_error_limit
    acceptance_pass = (
        spatial_pass
        and zero_field_pass
        and symmetry_pass
        and monotonic
        and profile_accuracy_pass
        and flow_rate_accuracy_pass
    )

    report = NSBG5Report(
        cases=cases,
        convergence=HartmannConvergenceSummary(
            hartmann=convergence_hartmann,
            grid_sizes=convergence_grids,
            l2_errors=errors,
            observed_orders=orders,
            spatial_order_floor=spatial_order_floor,
            finest_l2_limit=finest_l2_limit,
        ),
        acceptance=G5AcceptanceSummary(
            spatial_order_pass=spatial_pass,
            zero_field_hydrodynamic_limit_pass=zero_field_pass,
            field_sign_symmetry_pass=symmetry_pass,
            monotonic_magnetic_damping_pass=monotonic,
            profile_accuracy_pass=profile_accuracy_pass,
            flow_rate_accuracy_pass=flow_rate_accuracy_pass,
            zero_field_l2_limit=zero_field_l2_limit,
            field_sign_symmetry_l2_limit=field_sign_symmetry_l2_limit,
            mean_velocity_relative_error_limit=mean_velocity_relative_error_limit,
            field_sign_symmetry_l2=sign_symmetry,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g5_report(report: NSBG5Report) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
