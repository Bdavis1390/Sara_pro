from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .nsb_g3_solver import integrate_periodic_vorticity
from .qualification import CapabilityStatus, canonical_digest


TWO_PI = 2.0 * math.pi


class G4ManufacturedCase(BaseModel):
    grid_size: int = Field(ge=8)
    streamfunction_l2_error: float = Field(ge=0.0)
    velocity_x_l2_error: float = Field(ge=0.0)
    velocity_y_l2_error: float = Field(ge=0.0)
    poisson_residual_rms: float = Field(ge=0.0)
    divergence_rms: float = Field(ge=0.0)
    poisson_iterations: int = Field(ge=1)


class G4CrossSolverResult(BaseModel):
    grid_size: int = Field(ge=8)
    viscosity: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    requested_dt: float = Field(gt=0.0)
    effective_dt: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    fd_vs_spectral_l2_difference: float = Field(ge=0.0)
    fd_vs_spectral_relative_rms: float = Field(ge=0.0)
    fd_state_change_rms: float = Field(ge=0.0)
    mean_vorticity_drift: float = Field(ge=0.0)
    divergence_rms_final: float = Field(ge=0.0)
    poisson_residual_rms_final: float = Field(ge=0.0)
    kinetic_energy_initial: float = Field(ge=0.0)
    kinetic_energy_final: float = Field(ge=0.0)
    enstrophy_initial: float = Field(ge=0.0)
    enstrophy_final: float = Field(ge=0.0)
    energy_nonincreasing: bool
    enstrophy_nonincreasing: bool


class G4AcceptanceSummary(BaseModel):
    manufactured_grids: tuple[int, int, int]
    streamfunction_orders: tuple[float, float]
    velocity_x_orders: tuple[float, float]
    velocity_y_orders: tuple[float, float]
    spatial_order_floor: float = Field(gt=0.0)
    poisson_residual_limit: float = Field(gt=0.0)
    divergence_limit: float = Field(gt=0.0)
    cross_solver_relative_limit: float = Field(gt=0.0)
    mean_vorticity_drift_limit: float = Field(gt=0.0)
    state_change_floor: float = Field(gt=0.0)
    acceptance_pass: bool


class NSBG4Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G4-001"
    benchmark_version: str = "0.9"
    formulation: str = "2D periodic finite-difference vorticity-streamfunction cross-solver gate"
    poisson_solver: str = "periodic SOR on second-order five-point Laplacian"
    spatial_derivatives: str = "second-order centered finite differences"
    temporal_scheme: str = "explicit midpoint RK2"
    comparison_reference: str = "WS-NSB v0.8 G3 Fourier spectral periodic integrator"
    manufactured_cases: tuple[G4ManufacturedCase, ...]
    cross_solver: G4CrossSolverResult
    acceptance: G4AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    numerically_distinct_second_formulation_implemented: bool = True
    cross_solver_comparison_performed: bool = True
    external_independent_replication_claimed: bool = False
    three_dimensional_solver_claimed: bool = False
    general_purpose_cfd_solver_claimed: bool = False
    navier_stokes_singularity_reproduced: bool = False
    mhd_or_plasma_solved: bool = False
    laboratory_validation_performed: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G4 adds a numerically distinct finite-difference formulation inside the same Worldshepherd codebase.",
        "Cross-solver agreement is internal numerical replication, not external independent replication or peer review.",
        "G4 remains limited to bounded 2D periodic incompressible reference problems and does not establish a 3D/general CFD capability.",
        "Passing G4 does not reproduce, validate, or refute a finite-time Navier-Stokes singularity and establishes no MHD, plasma, laboratory, propulsion, shielding, stealth, cloaking, or operational capability.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG4Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v0.9 must remain SIMULATED_ONLY")
        if not self.numerically_distinct_second_formulation_implemented:
            raise ValueError("G4 requires the finite-difference formulation")
        if not self.cross_solver_comparison_performed:
            raise ValueError("G4 requires cross-solver comparison")
        prohibited = (
            self.external_independent_replication_claimed,
            self.three_dimensional_solver_claimed,
            self.general_purpose_cfd_solver_claimed,
            self.navier_stokes_singularity_reproduced,
            self.mhd_or_plasma_solved,
            self.laboratory_validation_performed,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v0.9 cannot promote unsupported external, physical, 3D, or singularity claims")
        return self


def _require_grid(grid_size: int) -> None:
    if grid_size < 8 or grid_size % 2:
        raise ValueError("G4 requires an even grid_size >= 8")


def _mean(field: list[list[float]]) -> float:
    n = len(field)
    return sum(value for row in field for value in row) / (n * n)


def _rms(field: list[list[float]]) -> float:
    n = len(field)
    return math.sqrt(sum(value * value for row in field for value in row) / (n * n))


def _l2_difference(left: list[list[float]], right: list[list[float]]) -> float:
    n = len(left)
    return math.sqrt(sum((left[i][j] - right[i][j]) ** 2 for i in range(n) for j in range(n)) / (n * n))


def _add_scaled(left: list[list[float]], right: list[list[float]], scale: float) -> list[list[float]]:
    n = len(left)
    return [[left[i][j] + scale * right[i][j] for j in range(n)] for i in range(n)]


def _poisson_residual_rms(psi: list[list[float]], vorticity: list[list[float]]) -> float:
    n = len(psi)
    dx = TWO_PI / n
    inv_dx2 = 1.0 / (dx * dx)
    total = 0.0
    for i in range(n):
        ip = (i + 1) % n
        im = (i - 1) % n
        for j in range(n):
            jp = (j + 1) % n
            jm = (j - 1) % n
            minus_laplacian = (
                4.0 * psi[i][j]
                - psi[ip][j]
                - psi[im][j]
                - psi[i][jp]
                - psi[i][jm]
            ) * inv_dx2
            error = minus_laplacian - vorticity[i][j]
            total += error * error
    return math.sqrt(total / (n * n))


def solve_periodic_poisson_fd(
    vorticity: list[list[float]],
    *,
    tolerance: float = 1e-10,
    max_iterations: int = 20000,
    relaxation: float = 1.6,
) -> tuple[list[list[float]], float, int]:
    n = len(vorticity)
    _require_grid(n)
    if any(len(row) != n for row in vorticity):
        raise ValueError("vorticity must be square")
    if abs(_mean(vorticity)) > 1e-12:
        raise ValueError("periodic Poisson solve requires near-zero mean vorticity")
    if tolerance <= 0.0 or max_iterations < 1:
        raise ValueError("invalid Poisson convergence controls")
    if not 0.0 < relaxation < 2.0:
        raise ValueError("SOR relaxation must be in (0, 2)")

    dx = TWO_PI / n
    dx2 = dx * dx
    psi = [[0.0] * n for _ in range(n)]
    residual = math.inf

    for iteration in range(1, max_iterations + 1):
        for i in range(n):
            ip = (i + 1) % n
            im = (i - 1) % n
            for j in range(n):
                jp = (j + 1) % n
                jm = (j - 1) % n
                target = 0.25 * (
                    psi[ip][j]
                    + psi[im][j]
                    + psi[i][jp]
                    + psi[i][jm]
                    + dx2 * vorticity[i][j]
                )
                psi[i][j] = (1.0 - relaxation) * psi[i][j] + relaxation * target

        gauge = _mean(psi)
        for i in range(n):
            for j in range(n):
                psi[i][j] -= gauge

        if iteration % 10 == 0:
            residual = _poisson_residual_rms(psi, vorticity)
            if residual <= tolerance:
                return psi, residual, iteration

    residual = _poisson_residual_rms(psi, vorticity)
    raise ValueError(f"periodic SOR Poisson solve failed to converge: residual={residual:.6e}")


def _velocity_from_vorticity_fd(
    vorticity: list[list[float]],
    *,
    poisson_tolerance: float = 1e-10,
) -> tuple[list[list[float]], list[list[float]], list[list[float]], float, int]:
    psi, residual, iterations = solve_periodic_poisson_fd(vorticity, tolerance=poisson_tolerance)
    n = len(vorticity)
    dx = TWO_PI / n
    inv_2dx = 1.0 / (2.0 * dx)
    u = [[0.0] * n for _ in range(n)]
    v = [[0.0] * n for _ in range(n)]
    for i in range(n):
        ip = (i + 1) % n
        im = (i - 1) % n
        for j in range(n):
            jp = (j + 1) % n
            jm = (j - 1) % n
            u[i][j] = (psi[i][jp] - psi[i][jm]) * inv_2dx
            v[i][j] = -(psi[ip][j] - psi[im][j]) * inv_2dx
    return u, v, psi, residual, iterations


def reconstruct_periodic_velocity_fd(
    vorticity: list[list[float]],
) -> tuple[list[list[float]], list[list[float]]]:
    u, v, _, _, _ = _velocity_from_vorticity_fd(vorticity)
    return u, v


def _divergence_rms(u: list[list[float]], v: list[list[float]]) -> float:
    n = len(u)
    dx = TWO_PI / n
    inv_2dx = 1.0 / (2.0 * dx)
    total = 0.0
    for i in range(n):
        ip = (i + 1) % n
        im = (i - 1) % n
        for j in range(n):
            jp = (j + 1) % n
            jm = (j - 1) % n
            divergence = (
                u[ip][j] - u[im][j] + v[i][jp] - v[i][jm]
            ) * inv_2dx
            total += divergence * divergence
    return math.sqrt(total / (n * n))


def _rhs_fd(
    vorticity: list[list[float]],
    viscosity: float,
    *,
    poisson_tolerance: float,
) -> tuple[list[list[float]], list[list[float]], list[list[float]], float, int]:
    u, v, _, residual, iterations = _velocity_from_vorticity_fd(
        vorticity,
        poisson_tolerance=poisson_tolerance,
    )
    n = len(vorticity)
    dx = TWO_PI / n
    inv_2dx = 1.0 / (2.0 * dx)
    inv_dx2 = 1.0 / (dx * dx)
    rhs = [[0.0] * n for _ in range(n)]
    for i in range(n):
        ip = (i + 1) % n
        im = (i - 1) % n
        for j in range(n):
            jp = (j + 1) % n
            jm = (j - 1) % n
            dwdx = (vorticity[ip][j] - vorticity[im][j]) * inv_2dx
            dwdy = (vorticity[i][jp] - vorticity[i][jm]) * inv_2dx
            laplacian = (
                vorticity[ip][j]
                + vorticity[im][j]
                + vorticity[i][jp]
                + vorticity[i][jm]
                - 4.0 * vorticity[i][j]
            ) * inv_dx2
            rhs[i][j] = -(u[i][j] * dwdx + v[i][j] * dwdy) + viscosity * laplacian
    return rhs, u, v, residual, iterations


def _stability_bound(vorticity: list[list[float]], viscosity: float) -> float:
    u, v, _, _, _ = _velocity_from_vorticity_fd(vorticity, poisson_tolerance=1e-9)
    n = len(vorticity)
    dx = TWO_PI / n
    max_speed = max(math.hypot(u[i][j], v[i][j]) for i in range(n) for j in range(n))
    advective = math.inf if max_speed <= 1e-15 else 0.35 * dx / max_speed
    diffusive = math.inf if viscosity <= 0.0 else 0.20 * dx * dx / viscosity
    return min(advective, diffusive)


def integrate_periodic_vorticity_fd(
    *,
    initial_vorticity: list[list[float]],
    viscosity: float,
    dt: float,
    final_time: float,
    poisson_tolerance: float = 1e-10,
) -> tuple[list[list[float]], float, int, float, int]:
    n = len(initial_vorticity)
    _require_grid(n)
    if any(len(row) != n for row in initial_vorticity):
        raise ValueError("initial_vorticity must be square")
    if viscosity <= 0.0 or dt <= 0.0 or final_time <= 0.0:
        raise ValueError("viscosity, dt, and final_time must be positive")
    if abs(_mean(initial_vorticity)) > 1e-12:
        raise ValueError("periodic vorticity integration requires near-zero mean vorticity")

    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    if effective_dt > _stability_bound(initial_vorticity, viscosity):
        raise ValueError("requested timestep exceeds conservative G4 finite-difference stability bound")

    vorticity = [row[:] for row in initial_vorticity]
    peak_poisson_residual = 0.0
    peak_poisson_iterations = 0
    for _ in range(steps):
        k1, _, _, residual1, iterations1 = _rhs_fd(
            vorticity,
            viscosity,
            poisson_tolerance=poisson_tolerance,
        )
        midpoint = _add_scaled(vorticity, k1, 0.5 * effective_dt)
        k2, _, _, residual2, iterations2 = _rhs_fd(
            midpoint,
            viscosity,
            poisson_tolerance=poisson_tolerance,
        )
        vorticity = _add_scaled(vorticity, k2, effective_dt)
        peak_poisson_residual = max(peak_poisson_residual, residual1, residual2)
        peak_poisson_iterations = max(peak_poisson_iterations, iterations1, iterations2)
    return vorticity, effective_dt, steps, peak_poisson_residual, peak_poisson_iterations


def _kinetic_energy(u: list[list[float]], v: list[list[float]]) -> float:
    n = len(u)
    return 0.5 * sum(u[i][j] ** 2 + v[i][j] ** 2 for i in range(n) for j in range(n)) / (n * n)


def _enstrophy(vorticity: list[list[float]]) -> float:
    n = len(vorticity)
    return 0.5 * sum(value * value for row in vorticity for value in row) / (n * n)


def _manufactured_case(grid_size: int) -> G4ManufacturedCase:
    _require_grid(grid_size)
    dx = TWO_PI / grid_size
    psi_exact: list[list[float]] = []
    omega: list[list[float]] = []
    u_exact: list[list[float]] = []
    v_exact: list[list[float]] = []
    for i in range(grid_size):
        x = i * dx
        psi_row: list[float] = []
        omega_row: list[float] = []
        u_row: list[float] = []
        v_row: list[float] = []
        for j in range(grid_size):
            y = j * dx
            phase = 2.0 * x - y
            psi_row.append(math.sin(x) * math.sin(y) + 0.15 * math.cos(phase))
            omega_row.append(2.0 * math.sin(x) * math.sin(y) + 0.75 * math.cos(phase))
            u_row.append(math.sin(x) * math.cos(y) + 0.15 * math.sin(phase))
            v_row.append(-math.cos(x) * math.sin(y) + 0.30 * math.sin(phase))
        psi_exact.append(psi_row)
        omega.append(omega_row)
        u_exact.append(u_row)
        v_exact.append(v_row)

    u, v, psi, residual, iterations = _velocity_from_vorticity_fd(
        omega,
        poisson_tolerance=1e-11,
    )
    return G4ManufacturedCase(
        grid_size=grid_size,
        streamfunction_l2_error=_l2_difference(psi, psi_exact),
        velocity_x_l2_error=_l2_difference(u, u_exact),
        velocity_y_l2_error=_l2_difference(v, v_exact),
        poisson_residual_rms=residual,
        divergence_rms=_divergence_rms(u, v),
        poisson_iterations=iterations,
    )


def _mixed_mode_initial(grid_size: int) -> list[list[float]]:
    dx = TWO_PI / grid_size
    return [
        [
            2.0 * math.sin(i * dx) * math.sin(j * dx)
            + 0.6 * math.cos(2.0 * i * dx + j * dx)
            + 0.4 * math.sin(i * dx - 2.0 * j * dx)
            for j in range(grid_size)
        ]
        for i in range(grid_size)
    ]


def _cross_solver_case(
    *,
    grid_size: int = 16,
    viscosity: float = 0.01,
    dt: float = 0.005,
    final_time: float = 0.05,
) -> G4CrossSolverResult:
    initial = _mixed_mode_initial(grid_size)
    fd_final, effective_dt, steps, _, _ = integrate_periodic_vorticity_fd(
        initial_vorticity=initial,
        viscosity=viscosity,
        dt=dt,
        final_time=final_time,
    )
    spectral_final, _, _ = integrate_periodic_vorticity(
        initial_vorticity=initial,
        viscosity=viscosity,
        dt=dt,
        final_time=final_time,
    )
    u_initial, v_initial, _, _, _ = _velocity_from_vorticity_fd(initial)
    u_final, v_final, _, residual_final, _ = _velocity_from_vorticity_fd(fd_final)
    difference = _l2_difference(fd_final, spectral_final)
    reference_rms = max(_rms(spectral_final), 1e-15)
    mean_initial = _mean(initial)
    mean_final = _mean(fd_final)
    energy_initial = _kinetic_energy(u_initial, v_initial)
    energy_final = _kinetic_energy(u_final, v_final)
    enstrophy_initial = _enstrophy(initial)
    enstrophy_final = _enstrophy(fd_final)
    return G4CrossSolverResult(
        grid_size=grid_size,
        viscosity=viscosity,
        final_time=final_time,
        requested_dt=dt,
        effective_dt=effective_dt,
        steps=steps,
        fd_vs_spectral_l2_difference=difference,
        fd_vs_spectral_relative_rms=difference / reference_rms,
        fd_state_change_rms=_l2_difference(fd_final, initial),
        mean_vorticity_drift=abs(mean_final - mean_initial),
        divergence_rms_final=_divergence_rms(u_final, v_final),
        poisson_residual_rms_final=residual_final,
        kinetic_energy_initial=energy_initial,
        kinetic_energy_final=energy_final,
        enstrophy_initial=enstrophy_initial,
        enstrophy_final=enstrophy_final,
        energy_nonincreasing=energy_final <= energy_initial * (1.0 + 1e-10),
        enstrophy_nonincreasing=enstrophy_final <= enstrophy_initial * (1.0 + 1e-10),
    )


def _observed_order(coarse_error: float, fine_error: float) -> float:
    if coarse_error <= 0.0 or fine_error <= 0.0:
        raise ValueError("convergence errors must be positive")
    return math.log(coarse_error / fine_error) / math.log(2.0)


def run_nsb_g4_benchmark(
    *,
    manufactured_grids: tuple[int, int, int] = (8, 16, 32),
    spatial_order_floor: float = 1.8,
    poisson_residual_limit: float = 1e-9,
    divergence_limit: float = 1e-10,
    cross_solver_relative_limit: float = 0.005,
    mean_vorticity_drift_limit: float = 1e-12,
    state_change_floor: float = 0.01,
) -> NSBG4Report:
    if manufactured_grids[1] != 2 * manufactured_grids[0] or manufactured_grids[2] != 2 * manufactured_grids[1]:
        raise ValueError("G4 manufactured grids must use exact factor-two refinement")

    manufactured_cases = tuple(_manufactured_case(grid) for grid in manufactured_grids)
    stream_errors = tuple(case.streamfunction_l2_error for case in manufactured_cases)
    ux_errors = tuple(case.velocity_x_l2_error for case in manufactured_cases)
    uy_errors = tuple(case.velocity_y_l2_error for case in manufactured_cases)
    stream_orders = (_observed_order(stream_errors[0], stream_errors[1]), _observed_order(stream_errors[1], stream_errors[2]))
    ux_orders = (_observed_order(ux_errors[0], ux_errors[1]), _observed_order(ux_errors[1], ux_errors[2]))
    uy_orders = (_observed_order(uy_errors[0], uy_errors[1]), _observed_order(uy_errors[1], uy_errors[2]))
    cross = _cross_solver_case()

    manufactured_ok = (
        min(stream_orders) >= spatial_order_floor
        and min(ux_orders) >= spatial_order_floor
        and min(uy_orders) >= spatial_order_floor
        and max(case.poisson_residual_rms for case in manufactured_cases) <= poisson_residual_limit
        and max(case.divergence_rms for case in manufactured_cases) <= divergence_limit
    )
    cross_ok = (
        cross.fd_vs_spectral_relative_rms <= cross_solver_relative_limit
        and cross.mean_vorticity_drift <= mean_vorticity_drift_limit
        and cross.fd_state_change_rms >= state_change_floor
        and cross.divergence_rms_final <= divergence_limit
        and cross.poisson_residual_rms_final <= poisson_residual_limit
        and cross.energy_nonincreasing
        and cross.enstrophy_nonincreasing
    )
    acceptance_pass = manufactured_ok and cross_ok

    report = NSBG4Report(
        manufactured_cases=manufactured_cases,
        cross_solver=cross,
        acceptance=G4AcceptanceSummary(
            manufactured_grids=manufactured_grids,
            streamfunction_orders=stream_orders,
            velocity_x_orders=ux_orders,
            velocity_y_orders=uy_orders,
            spatial_order_floor=spatial_order_floor,
            poisson_residual_limit=poisson_residual_limit,
            divergence_limit=divergence_limit,
            cross_solver_relative_limit=cross_solver_relative_limit,
            mean_vorticity_drift_limit=mean_vorticity_drift_limit,
            state_change_floor=state_change_floor,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g4_report(report: NSBG4Report) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
