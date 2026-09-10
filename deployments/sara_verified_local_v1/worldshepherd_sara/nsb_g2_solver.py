from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


TWO_PI = 2.0 * math.pi


class G2Outcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class G2CaseResult(BaseModel):
    case_id: str
    grid_size: int = Field(ge=8)
    viscosity: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    requested_dt: float = Field(gt=0.0)
    effective_dt: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    l2_vorticity_error: float = Field(ge=0.0)
    linf_vorticity_error: float = Field(ge=0.0)
    divergence_rms: float = Field(ge=0.0)
    kinetic_energy_initial: float = Field(ge=0.0)
    kinetic_energy_final: float = Field(ge=0.0)
    kinetic_energy_exact_final: float = Field(ge=0.0)
    kinetic_energy_relative_error: float = Field(ge=0.0)
    enstrophy_initial: float = Field(ge=0.0)
    enstrophy_final: float = Field(ge=0.0)
    enstrophy_exact_final: float = Field(ge=0.0)
    enstrophy_relative_error: float = Field(ge=0.0)
    dissipative_energy_monotonic: bool
    dissipative_enstrophy_monotonic: bool


class G2ConvergenceSummary(BaseModel):
    spatial_grid_sizes: tuple[int, int, int]
    spatial_errors: tuple[float, float, float]
    spatial_orders: tuple[float, float]
    spatial_order_floor: float
    temporal_grid_size: int
    temporal_dts: tuple[float, float, float]
    temporal_pair_differences: tuple[float, float]
    temporal_order: float
    temporal_order_floor: float
    divergence_limit: float
    energy_relative_error_limit: float
    enstrophy_relative_error_limit: float
    acceptance_pass: bool


class NSBG2Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G2-001"
    benchmark_version: str = "0.7"
    formulation: str = "2D periodic incompressible Navier-Stokes vorticity equation"
    manufactured_solution: str = "Taylor-Green vortex"
    spatial_scheme: str = "second-order centered finite differences"
    temporal_scheme: str = "explicit midpoint RK2"
    velocity_reconstruction: str = "Taylor-Green manufactured-mode projection"
    cases: tuple[G2CaseResult, ...]
    convergence: G2ConvergenceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    actual_pde_time_integration_performed: bool = True
    general_purpose_cfd_solver_claimed: bool = False
    navier_stokes_singularity_reproduced: bool = False
    mhd_or_plasma_solved: bool = False
    laboratory_validation_performed: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G2 integrates a bounded 2D manufactured incompressible Navier-Stokes reference problem only.",
        "Velocity reconstruction is specialized to the Taylor-Green manufactured mode; this is not a general-purpose CFD solver.",
        "Passing G2 does not reproduce, validate, or refute any finite-time singularity construction.",
        "No MHD, plasma, laboratory, propulsion, shielding, stealth, cloaking, or operational capability is established.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG2Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v0.7 must remain SIMULATED_ONLY")
        prohibited = (
            self.general_purpose_cfd_solver_claimed,
            self.navier_stokes_singularity_reproduced,
            self.mhd_or_plasma_solved,
            self.laboratory_validation_performed,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v0.7 cannot promote unsupported physical or singularity claims")
        if not self.actual_pde_time_integration_performed:
            raise ValueError("G2 report must represent an executed PDE time integration")
        return self


def _grid_spacing(grid_size: int) -> float:
    return TWO_PI / grid_size


def _initial_vorticity(grid_size: int) -> list[list[float]]:
    dx = _grid_spacing(grid_size)
    return [
        [
            2.0 * math.sin(i * dx) * math.sin(j * dx)
            for j in range(grid_size)
        ]
        for i in range(grid_size)
    ]


def _exact_vorticity(grid_size: int, viscosity: float, time_value: float) -> list[list[float]]:
    dx = _grid_spacing(grid_size)
    amplitude = math.exp(-2.0 * viscosity * time_value)
    return [
        [
            2.0 * amplitude * math.sin(i * dx) * math.sin(j * dx)
            for j in range(grid_size)
        ]
        for i in range(grid_size)
    ]


def _mode_amplitude(vorticity: list[list[float]]) -> float:
    grid_size = len(vorticity)
    dx = _grid_spacing(grid_size)
    numerator = 0.0
    denominator = 0.0
    for i in range(grid_size):
        sine_x = math.sin(i * dx)
        for j in range(grid_size):
            basis = sine_x * math.sin(j * dx)
            numerator += vorticity[i][j] * basis
            denominator += 2.0 * basis * basis
    if denominator <= 0.0:
        raise ValueError("degenerate Taylor-Green projection")
    return numerator / denominator


def _velocity_from_mode(vorticity: list[list[float]]) -> tuple[list[list[float]], list[list[float]]]:
    grid_size = len(vorticity)
    dx = _grid_spacing(grid_size)
    amplitude = _mode_amplitude(vorticity)
    velocity_x = [[0.0] * grid_size for _ in range(grid_size)]
    velocity_y = [[0.0] * grid_size for _ in range(grid_size)]
    for i in range(grid_size):
        x_value = i * dx
        sine_x = math.sin(x_value)
        cosine_x = math.cos(x_value)
        for j in range(grid_size):
            y_value = j * dx
            sine_y = math.sin(y_value)
            cosine_y = math.cos(y_value)
            velocity_x[i][j] = amplitude * sine_x * cosine_y
            velocity_y[i][j] = -amplitude * cosine_x * sine_y
    return velocity_x, velocity_y


def _rhs(vorticity: list[list[float]], viscosity: float) -> list[list[float]]:
    grid_size = len(vorticity)
    dx = _grid_spacing(grid_size)
    inv_2dx = 1.0 / (2.0 * dx)
    inv_dx2 = 1.0 / (dx * dx)
    velocity_x, velocity_y = _velocity_from_mode(vorticity)
    result = [[0.0] * grid_size for _ in range(grid_size)]

    for i in range(grid_size):
        ip = (i + 1) % grid_size
        im = (i - 1) % grid_size
        for j in range(grid_size):
            jp = (j + 1) % grid_size
            jm = (j - 1) % grid_size
            dwdx = (vorticity[ip][j] - vorticity[im][j]) * inv_2dx
            dwdy = (vorticity[i][jp] - vorticity[i][jm]) * inv_2dx
            laplacian = (
                vorticity[ip][j]
                + vorticity[im][j]
                + vorticity[i][jp]
                + vorticity[i][jm]
                - 4.0 * vorticity[i][j]
            ) * inv_dx2
            result[i][j] = (
                -velocity_x[i][j] * dwdx
                - velocity_y[i][j] * dwdy
                + viscosity * laplacian
            )
    return result


def _add_scaled(
    left: list[list[float]],
    right: list[list[float]],
    scale: float,
) -> list[list[float]]:
    grid_size = len(left)
    return [
        [left[i][j] + scale * right[i][j] for j in range(grid_size)]
        for i in range(grid_size)
    ]


def _midpoint_step(vorticity: list[list[float]], dt: float, viscosity: float) -> list[list[float]]:
    k1 = _rhs(vorticity, viscosity)
    midpoint = _add_scaled(vorticity, k1, 0.5 * dt)
    k2 = _rhs(midpoint, viscosity)
    return _add_scaled(vorticity, k2, dt)


def integrate_taylor_green(
    *,
    grid_size: int,
    viscosity: float,
    dt: float,
    final_time: float,
) -> tuple[list[list[float]], float, int]:
    if grid_size < 8:
        raise ValueError("grid_size must be >= 8")
    if viscosity <= 0.0:
        raise ValueError("viscosity must be positive for the G2 dissipative reference")
    if dt <= 0.0 or final_time <= 0.0:
        raise ValueError("dt and final_time must be positive")

    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    dx = _grid_spacing(grid_size)
    diffusion_limit = 0.24 * dx * dx / viscosity
    advective_limit = 0.45 * dx
    if effective_dt > min(diffusion_limit, advective_limit):
        raise ValueError("requested timestep exceeds conservative explicit G2 stability bound")

    vorticity = _initial_vorticity(grid_size)
    for _ in range(steps):
        vorticity = _midpoint_step(vorticity, effective_dt, viscosity)
    return vorticity, effective_dt, steps


def _l2_difference(left: list[list[float]], right: list[list[float]]) -> float:
    grid_size = len(left)
    total = sum(
        (left[i][j] - right[i][j]) ** 2
        for i in range(grid_size)
        for j in range(grid_size)
    )
    return math.sqrt(total / (grid_size * grid_size))


def _linf_difference(left: list[list[float]], right: list[list[float]]) -> float:
    grid_size = len(left)
    return max(
        abs(left[i][j] - right[i][j])
        for i in range(grid_size)
        for j in range(grid_size)
    )


def _divergence_rms(
    velocity_x: list[list[float]],
    velocity_y: list[list[float]],
) -> float:
    grid_size = len(velocity_x)
    dx = _grid_spacing(grid_size)
    inv_2dx = 1.0 / (2.0 * dx)
    total = 0.0
    for i in range(grid_size):
        ip = (i + 1) % grid_size
        im = (i - 1) % grid_size
        for j in range(grid_size):
            jp = (j + 1) % grid_size
            jm = (j - 1) % grid_size
            divergence = (
                (velocity_x[ip][j] - velocity_x[im][j])
                + (velocity_y[i][jp] - velocity_y[i][jm])
            ) * inv_2dx
            total += divergence * divergence
    return math.sqrt(total / (grid_size * grid_size))


def _kinetic_energy(
    velocity_x: list[list[float]],
    velocity_y: list[list[float]],
) -> float:
    grid_size = len(velocity_x)
    total = sum(
        velocity_x[i][j] ** 2 + velocity_y[i][j] ** 2
        for i in range(grid_size)
        for j in range(grid_size)
    )
    return 0.5 * total / (grid_size * grid_size)


def _enstrophy(vorticity: list[list[float]]) -> float:
    grid_size = len(vorticity)
    total = sum(
        vorticity[i][j] ** 2
        for i in range(grid_size)
        for j in range(grid_size)
    )
    return 0.5 * total / (grid_size * grid_size)


def _case_result(
    *,
    case_id: str,
    grid_size: int,
    viscosity: float,
    dt: float,
    final_time: float,
) -> tuple[G2CaseResult, list[list[float]]]:
    numerical, effective_dt, steps = integrate_taylor_green(
        grid_size=grid_size,
        viscosity=viscosity,
        dt=dt,
        final_time=final_time,
    )
    exact = _exact_vorticity(grid_size, viscosity, final_time)
    velocity_x, velocity_y = _velocity_from_mode(numerical)
    initial_velocity_x, initial_velocity_y = _velocity_from_mode(_initial_vorticity(grid_size))

    energy_initial = _kinetic_energy(initial_velocity_x, initial_velocity_y)
    energy_final = _kinetic_energy(velocity_x, velocity_y)
    amplitude_exact = math.exp(-2.0 * viscosity * final_time)
    energy_exact = 0.25 * amplitude_exact * amplitude_exact
    enstrophy_initial = _enstrophy(_initial_vorticity(grid_size))
    enstrophy_final = _enstrophy(numerical)
    enstrophy_exact = 0.5 * amplitude_exact * amplitude_exact

    return (
        G2CaseResult(
            case_id=case_id,
            grid_size=grid_size,
            viscosity=viscosity,
            final_time=final_time,
            requested_dt=dt,
            effective_dt=effective_dt,
            steps=steps,
            l2_vorticity_error=_l2_difference(numerical, exact),
            linf_vorticity_error=_linf_difference(numerical, exact),
            divergence_rms=_divergence_rms(velocity_x, velocity_y),
            kinetic_energy_initial=energy_initial,
            kinetic_energy_final=energy_final,
            kinetic_energy_exact_final=energy_exact,
            kinetic_energy_relative_error=abs(energy_final - energy_exact) / max(energy_exact, 1e-15),
            enstrophy_initial=enstrophy_initial,
            enstrophy_final=enstrophy_final,
            enstrophy_exact_final=enstrophy_exact,
            enstrophy_relative_error=abs(enstrophy_final - enstrophy_exact) / max(enstrophy_exact, 1e-15),
            dissipative_energy_monotonic=energy_final <= energy_initial,
            dissipative_enstrophy_monotonic=enstrophy_final <= enstrophy_initial,
        ),
        numerical,
    )


def _observed_order(coarse_error: float, fine_error: float, refinement_ratio: float = 2.0) -> float:
    if coarse_error <= 0.0 or fine_error <= 0.0:
        raise ValueError("convergence errors must be positive")
    return math.log(coarse_error / fine_error) / math.log(refinement_ratio)


def run_nsb_g2_benchmark(
    *,
    viscosity: float = 0.05,
    spatial_final_time: float = 0.05,
    spatial_dt: float = 0.0005,
    spatial_grids: tuple[int, int, int] = (12, 24, 48),
    temporal_grid: int = 24,
    temporal_final_time: float = 0.4,
    temporal_dts: tuple[float, float, float] = (0.04, 0.02, 0.01),
    spatial_order_floor: float = 1.8,
    temporal_order_floor: float = 1.8,
    divergence_limit: float = 1e-12,
    energy_relative_error_limit: float = 0.01,
    enstrophy_relative_error_limit: float = 0.01,
) -> NSBG2Report:
    if spatial_grids[1] != 2 * spatial_grids[0] or spatial_grids[2] != 2 * spatial_grids[1]:
        raise ValueError("G2 spatial grids must use exact 2x refinement")
    if not (
        math.isclose(temporal_dts[0], 2.0 * temporal_dts[1], rel_tol=0.0, abs_tol=1e-15)
        and math.isclose(temporal_dts[1], 2.0 * temporal_dts[2], rel_tol=0.0, abs_tol=1e-15)
    ):
        raise ValueError("G2 temporal dts must use exact 2x refinement")

    spatial_cases: list[G2CaseResult] = []
    for grid_size in spatial_grids:
        case, _ = _case_result(
            case_id=f"spatial_n{grid_size}",
            grid_size=grid_size,
            viscosity=viscosity,
            dt=spatial_dt,
            final_time=spatial_final_time,
        )
        spatial_cases.append(case)

    spatial_errors = tuple(case.l2_vorticity_error for case in spatial_cases)
    spatial_orders = (
        _observed_order(spatial_errors[0], spatial_errors[1]),
        _observed_order(spatial_errors[1], spatial_errors[2]),
    )

    temporal_cases: list[G2CaseResult] = []
    temporal_fields: list[list[list[float]]] = []
    for dt in temporal_dts:
        case, field = _case_result(
            case_id=f"temporal_dt_{dt:g}",
            grid_size=temporal_grid,
            viscosity=viscosity,
            dt=dt,
            final_time=temporal_final_time,
        )
        temporal_cases.append(case)
        temporal_fields.append(field)

    pair_differences = (
        _l2_difference(temporal_fields[0], temporal_fields[1]),
        _l2_difference(temporal_fields[1], temporal_fields[2]),
    )
    temporal_order = _observed_order(pair_differences[0], pair_differences[1])

    all_cases = tuple(spatial_cases + temporal_cases)
    acceptance_pass = (
        min(spatial_orders) >= spatial_order_floor
        and temporal_order >= temporal_order_floor
        and max(case.divergence_rms for case in all_cases) <= divergence_limit
        and max(case.kinetic_energy_relative_error for case in all_cases) <= energy_relative_error_limit
        and max(case.enstrophy_relative_error for case in all_cases) <= enstrophy_relative_error_limit
        and all(case.dissipative_energy_monotonic for case in all_cases)
        and all(case.dissipative_enstrophy_monotonic for case in all_cases)
    )

    report = NSBG2Report(
        cases=all_cases,
        convergence=G2ConvergenceSummary(
            spatial_grid_sizes=spatial_grids,
            spatial_errors=spatial_errors,
            spatial_orders=spatial_orders,
            spatial_order_floor=spatial_order_floor,
            temporal_grid_size=temporal_grid,
            temporal_dts=temporal_dts,
            temporal_pair_differences=pair_differences,
            temporal_order=temporal_order,
            temporal_order_floor=temporal_order_floor,
            divergence_limit=divergence_limit,
            energy_relative_error_limit=energy_relative_error_limit,
            enstrophy_relative_error_limit=enstrophy_relative_error_limit,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g2_report(report: NSBG2Report) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
