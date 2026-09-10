from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


TWO_PI = 2.0 * math.pi


class G3Outcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class G3PoissonResult(BaseModel):
    grid_size: int = Field(ge=8)
    streamfunction_l2_error: float = Field(ge=0.0)
    velocity_x_l2_error: float = Field(ge=0.0)
    velocity_y_l2_error: float = Field(ge=0.0)
    divergence_rms: float = Field(ge=0.0)
    poisson_residual_rms: float = Field(ge=0.0)


class G3TaylorGreenResult(BaseModel):
    case_id: str
    grid_size: int = Field(ge=8)
    viscosity: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    requested_dt: float = Field(gt=0.0)
    effective_dt: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    vorticity_l2_error: float = Field(ge=0.0)
    divergence_rms: float = Field(ge=0.0)
    poisson_residual_rms: float = Field(ge=0.0)
    kinetic_energy_initial: float = Field(ge=0.0)
    kinetic_energy_final: float = Field(ge=0.0)
    enstrophy_initial: float = Field(ge=0.0)
    enstrophy_final: float = Field(ge=0.0)


class G3NonlinearResult(BaseModel):
    grid_size: int = Field(ge=8)
    viscosity: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    requested_dt: float = Field(gt=0.0)
    effective_dt: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    nonlinear_rhs_rms_initial: float = Field(ge=0.0)
    state_change_rms: float = Field(ge=0.0)
    mean_vorticity_initial: float
    mean_vorticity_final: float
    mean_vorticity_drift: float = Field(ge=0.0)
    divergence_rms_final: float = Field(ge=0.0)
    poisson_residual_rms_final: float = Field(ge=0.0)
    kinetic_energy_initial: float = Field(ge=0.0)
    kinetic_energy_final: float = Field(ge=0.0)
    enstrophy_initial: float = Field(ge=0.0)
    enstrophy_final: float = Field(ge=0.0)
    energy_nonincreasing: bool
    enstrophy_nonincreasing: bool


class G3AcceptanceSummary(BaseModel):
    poisson_error_limit: float = Field(gt=0.0)
    divergence_limit: float = Field(gt=0.0)
    temporal_order_floor: float = Field(gt=0.0)
    taylor_green_error_limit: float = Field(gt=0.0)
    mean_vorticity_drift_limit: float = Field(gt=0.0)
    nonlinear_rhs_floor: float = Field(gt=0.0)
    nonlinear_state_change_floor: float = Field(gt=0.0)
    temporal_orders: tuple[float, float]
    acceptance_pass: bool


class NSBG3Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G3-001"
    benchmark_version: str = "0.8"
    formulation: str = "2D periodic incompressible Navier-Stokes vorticity-streamfunction"
    poisson_solver: str = "radix-2 Fourier streamfunction inversion"
    spatial_derivatives: str = "Fourier spectral derivatives"
    temporal_scheme: str = "explicit midpoint RK2"
    nonlinear_treatment: str = "pseudo-spectral advection with two-thirds dealiasing"
    poisson_result: G3PoissonResult
    taylor_green_cases: tuple[G3TaylorGreenResult, ...]
    nonlinear_result: G3NonlinearResult
    acceptance: G3AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    mode_general_periodic_solver_implemented: bool = True
    radix2_fft_poisson_solve_performed: bool = True
    two_thirds_dealiasing_enabled: bool = True
    three_dimensional_solver_claimed: bool = False
    general_purpose_cfd_solver_claimed: bool = False
    navier_stokes_singularity_reproduced: bool = False
    mhd_or_plasma_solved: bool = False
    laboratory_validation_performed: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G3 is a mode-general 2D periodic incompressible vorticity-streamfunction solver on radix-2 grids.",
        "It does not establish a 3D or general-purpose CFD capability and does not support non-periodic boundaries.",
        "Passing G3 does not reproduce, validate, or refute any finite-time Navier-Stokes singularity construction.",
        "No MHD, plasma, laboratory, propulsion, shielding, stealth, cloaking, or operational capability is established.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG3Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v0.8 must remain SIMULATED_ONLY")
        if not self.mode_general_periodic_solver_implemented:
            raise ValueError("G3 must represent an executed mode-general periodic solver")
        if not self.radix2_fft_poisson_solve_performed or not self.two_thirds_dealiasing_enabled:
            raise ValueError("G3 requires Fourier Poisson inversion and two-thirds dealiasing")
        prohibited = (
            self.three_dimensional_solver_claimed,
            self.general_purpose_cfd_solver_claimed,
            self.navier_stokes_singularity_reproduced,
            self.mhd_or_plasma_solved,
            self.laboratory_validation_performed,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v0.8 cannot promote unsupported physical, 3D, or singularity claims")
        return self


def _require_radix2(grid_size: int) -> None:
    if grid_size < 8 or grid_size & (grid_size - 1):
        raise ValueError("G3 requires radix-2 grid_size >= 8")


def _fft1d(values: list[complex] | tuple[complex, ...], *, inverse: bool = False) -> list[complex]:
    n = len(values)
    _require_radix2(n)
    data = [complex(value) for value in values]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            data[i], data[j] = data[j], data[i]

    length = 2
    sign = 1.0 if inverse else -1.0
    while length <= n:
        angle = sign * TWO_PI / length
        root = complex(math.cos(angle), math.sin(angle))
        half = length // 2
        for start in range(0, n, length):
            weight = 1.0 + 0.0j
            for index in range(start, start + half):
                even = data[index]
                odd = data[index + half] * weight
                data[index] = even + odd
                data[index + half] = even - odd
                weight *= root
        length *= 2
    if inverse:
        data = [value / n for value in data]
    return data


def _fft2(field: list[list[float]] | list[list[complex]], *, inverse: bool = False) -> list[list[complex]]:
    n = len(field)
    _require_radix2(n)
    if any(len(row) != n for row in field):
        raise ValueError("G3 fields must be square")
    rows = [_fft1d(row, inverse=inverse) for row in field]
    result = [[0.0j] * n for _ in range(n)]
    for column in range(n):
        transformed = _fft1d([rows[row][column] for row in range(n)], inverse=inverse)
        for row in range(n):
            result[row][column] = transformed[row]
    return result


def _ifft2_real(spectrum: list[list[complex]]) -> list[list[float]]:
    transformed = _fft2(spectrum, inverse=True)
    return [[value.real for value in row] for row in transformed]


def _wavenumbers(grid_size: int) -> tuple[int, ...]:
    _require_radix2(grid_size)
    return tuple(index if index < grid_size // 2 else index - grid_size for index in range(grid_size))


def _field_mean(field: list[list[float]]) -> float:
    n = len(field)
    return sum(value for row in field for value in row) / (n * n)


def _field_rms(field: list[list[float]]) -> float:
    n = len(field)
    return math.sqrt(sum(value * value for row in field for value in row) / (n * n))


def _l2_difference(left: list[list[float]], right: list[list[float]]) -> float:
    n = len(left)
    return math.sqrt(
        sum((left[i][j] - right[i][j]) ** 2 for i in range(n) for j in range(n)) / (n * n)
    )


def _add_scaled(left: list[list[float]], right: list[list[float]], scale: float) -> list[list[float]]:
    n = len(left)
    return [[left[i][j] + scale * right[i][j] for j in range(n)] for i in range(n)]


def _velocity_and_streamfunction(
    vorticity: list[list[float]],
) -> tuple[list[list[float]], list[list[float]], list[list[float]]]:
    n = len(vorticity)
    _require_radix2(n)
    omega_hat = _fft2(vorticity)
    modes = _wavenumbers(n)
    psi_hat = [[0.0j] * n for _ in range(n)]
    u_hat = [[0.0j] * n for _ in range(n)]
    v_hat = [[0.0j] * n for _ in range(n)]
    for i, kx in enumerate(modes):
        for j, ky in enumerate(modes):
            k2 = kx * kx + ky * ky
            psi = 0.0j if k2 == 0 else omega_hat[i][j] / k2
            psi_hat[i][j] = psi
            u_hat[i][j] = 1j * ky * psi
            v_hat[i][j] = -1j * kx * psi
    return _ifft2_real(u_hat), _ifft2_real(v_hat), _ifft2_real(psi_hat)


def reconstruct_periodic_velocity(
    vorticity: list[list[float]],
) -> tuple[list[list[float]], list[list[float]]]:
    u, v, _ = _velocity_and_streamfunction(vorticity)
    return u, v


def _spectral_divergence_rms(u: list[list[float]], v: list[list[float]]) -> float:
    n = len(u)
    u_hat = _fft2(u)
    v_hat = _fft2(v)
    modes = _wavenumbers(n)
    divergence_hat = [[0.0j] * n for _ in range(n)]
    for i, kx in enumerate(modes):
        for j, ky in enumerate(modes):
            divergence_hat[i][j] = 1j * kx * u_hat[i][j] + 1j * ky * v_hat[i][j]
    return _field_rms(_ifft2_real(divergence_hat))


def _poisson_residual_rms(vorticity: list[list[float]], streamfunction: list[list[float]]) -> float:
    n = len(vorticity)
    psi_hat = _fft2(streamfunction)
    modes = _wavenumbers(n)
    reconstructed_hat = [[0.0j] * n for _ in range(n)]
    for i, kx in enumerate(modes):
        for j, ky in enumerate(modes):
            reconstructed_hat[i][j] = (kx * kx + ky * ky) * psi_hat[i][j]
    reconstructed = _ifft2_real(reconstructed_hat)
    mean_vorticity = _field_mean(vorticity)
    target = [[vorticity[i][j] - mean_vorticity for j in range(n)] for i in range(n)]
    return _l2_difference(reconstructed, target)


def _two_thirds_dealias(field: list[list[float]]) -> list[list[float]]:
    n = len(field)
    spectrum = _fft2(field)
    modes = _wavenumbers(n)
    cutoff = n // 3
    for i, kx in enumerate(modes):
        for j, ky in enumerate(modes):
            if abs(kx) > cutoff or abs(ky) > cutoff:
                spectrum[i][j] = 0.0j
    return _ifft2_real(spectrum)


def _rhs_components(
    vorticity: list[list[float]],
    viscosity: float,
) -> tuple[list[list[float]], list[list[float]], list[list[float]], list[list[float]]]:
    n = len(vorticity)
    omega_hat = _fft2(vorticity)
    modes = _wavenumbers(n)
    u_hat = [[0.0j] * n for _ in range(n)]
    v_hat = [[0.0j] * n for _ in range(n)]
    dwdx_hat = [[0.0j] * n for _ in range(n)]
    dwdy_hat = [[0.0j] * n for _ in range(n)]
    lap_hat = [[0.0j] * n for _ in range(n)]

    for i, kx in enumerate(modes):
        for j, ky in enumerate(modes):
            omega = omega_hat[i][j]
            k2 = kx * kx + ky * ky
            psi = 0.0j if k2 == 0 else omega / k2
            u_hat[i][j] = 1j * ky * psi
            v_hat[i][j] = -1j * kx * psi
            dwdx_hat[i][j] = 1j * kx * omega
            dwdy_hat[i][j] = 1j * ky * omega
            lap_hat[i][j] = -k2 * omega

    u = _ifft2_real(u_hat)
    v = _ifft2_real(v_hat)
    dwdx = _ifft2_real(dwdx_hat)
    dwdy = _ifft2_real(dwdy_hat)
    laplacian = _ifft2_real(lap_hat)
    nonlinear = [
        [-(u[i][j] * dwdx[i][j] + v[i][j] * dwdy[i][j]) for j in range(n)]
        for i in range(n)
    ]
    nonlinear = _two_thirds_dealias(nonlinear)
    rhs = [[nonlinear[i][j] + viscosity * laplacian[i][j] for j in range(n)] for i in range(n)]
    return rhs, u, v, nonlinear


def _midpoint_step(vorticity: list[list[float]], dt: float, viscosity: float) -> list[list[float]]:
    k1, _, _, _ = _rhs_components(vorticity, viscosity)
    midpoint = _add_scaled(vorticity, k1, 0.5 * dt)
    k2, _, _, _ = _rhs_components(midpoint, viscosity)
    return _add_scaled(vorticity, k2, dt)


def _stability_bound(vorticity: list[list[float]], viscosity: float) -> float:
    n = len(vorticity)
    u, v, _ = _velocity_and_streamfunction(vorticity)
    max_speed = max(math.hypot(u[i][j], v[i][j]) for i in range(n) for j in range(n))
    dx = TWO_PI / n
    advective = math.inf if max_speed <= 1e-15 else 0.35 * dx / max_speed
    kmax = n // 2
    diffusive = math.inf if viscosity <= 0.0 else 0.5 / (viscosity * kmax * kmax)
    return min(advective, diffusive)


def integrate_periodic_vorticity(
    *,
    initial_vorticity: list[list[float]],
    viscosity: float,
    dt: float,
    final_time: float,
) -> tuple[list[list[float]], float, int]:
    n = len(initial_vorticity)
    _require_radix2(n)
    if any(len(row) != n for row in initial_vorticity):
        raise ValueError("initial_vorticity must be square")
    if viscosity <= 0.0:
        raise ValueError("G3 reference integration requires positive viscosity")
    if dt <= 0.0 or final_time <= 0.0:
        raise ValueError("dt and final_time must be positive")
    if abs(_field_mean(initial_vorticity)) > 1e-12:
        raise ValueError("periodic streamfunction inversion requires near-zero mean vorticity")

    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    if effective_dt > _stability_bound(initial_vorticity, viscosity):
        raise ValueError("requested timestep exceeds conservative G3 spectral stability bound")

    vorticity = [row[:] for row in initial_vorticity]
    for _ in range(steps):
        vorticity = _midpoint_step(vorticity, effective_dt, viscosity)
        if effective_dt > 1.05 * _stability_bound(vorticity, viscosity):
            raise ValueError("evolving flow exceeded conservative G3 spectral stability bound")
    return vorticity, effective_dt, steps


def _kinetic_energy(u: list[list[float]], v: list[list[float]]) -> float:
    n = len(u)
    return 0.5 * sum(u[i][j] ** 2 + v[i][j] ** 2 for i in range(n) for j in range(n)) / (n * n)


def _enstrophy(vorticity: list[list[float]]) -> float:
    n = len(vorticity)
    return 0.5 * sum(value * value for row in vorticity for value in row) / (n * n)


def _taylor_green_initial(grid_size: int) -> list[list[float]]:
    _require_radix2(grid_size)
    dx = TWO_PI / grid_size
    return [
        [2.0 * math.sin(i * dx) * math.sin(j * dx) for j in range(grid_size)]
        for i in range(grid_size)
    ]


def _taylor_green_exact(grid_size: int, viscosity: float, time_value: float) -> list[list[float]]:
    amplitude = math.exp(-2.0 * viscosity * time_value)
    return [[amplitude * value for value in row] for row in _taylor_green_initial(grid_size)]


def _mixed_mode_initial(grid_size: int) -> list[list[float]]:
    _require_radix2(grid_size)
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


def _manufactured_poisson_result(grid_size: int = 16) -> G3PoissonResult:
    _require_radix2(grid_size)
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
            psi_row.append(math.sin(2.0 * x) + 0.35 * math.cos(3.0 * y) + 0.2 * math.sin(x + 2.0 * y))
            omega_row.append(4.0 * math.sin(2.0 * x) + 3.15 * math.cos(3.0 * y) + math.sin(x + 2.0 * y))
            u_row.append(-1.05 * math.sin(3.0 * y) + 0.4 * math.cos(x + 2.0 * y))
            v_row.append(-2.0 * math.cos(2.0 * x) - 0.2 * math.cos(x + 2.0 * y))
        psi_exact.append(psi_row)
        omega.append(omega_row)
        u_exact.append(u_row)
        v_exact.append(v_row)

    u, v, psi = _velocity_and_streamfunction(omega)
    return G3PoissonResult(
        grid_size=grid_size,
        streamfunction_l2_error=_l2_difference(psi, psi_exact),
        velocity_x_l2_error=_l2_difference(u, u_exact),
        velocity_y_l2_error=_l2_difference(v, v_exact),
        divergence_rms=_spectral_divergence_rms(u, v),
        poisson_residual_rms=_poisson_residual_rms(omega, psi),
    )


def _taylor_green_case(
    *,
    case_id: str,
    grid_size: int,
    viscosity: float,
    dt: float,
    final_time: float,
) -> G3TaylorGreenResult:
    initial = _taylor_green_initial(grid_size)
    numerical, effective_dt, steps = integrate_periodic_vorticity(
        initial_vorticity=initial,
        viscosity=viscosity,
        dt=dt,
        final_time=final_time,
    )
    exact = _taylor_green_exact(grid_size, viscosity, final_time)
    u_initial, v_initial, _ = _velocity_and_streamfunction(initial)
    u_final, v_final, psi_final = _velocity_and_streamfunction(numerical)
    return G3TaylorGreenResult(
        case_id=case_id,
        grid_size=grid_size,
        viscosity=viscosity,
        final_time=final_time,
        requested_dt=dt,
        effective_dt=effective_dt,
        steps=steps,
        vorticity_l2_error=_l2_difference(numerical, exact),
        divergence_rms=_spectral_divergence_rms(u_final, v_final),
        poisson_residual_rms=_poisson_residual_rms(numerical, psi_final),
        kinetic_energy_initial=_kinetic_energy(u_initial, v_initial),
        kinetic_energy_final=_kinetic_energy(u_final, v_final),
        enstrophy_initial=_enstrophy(initial),
        enstrophy_final=_enstrophy(numerical),
    )


def _nonlinear_case(
    *,
    grid_size: int = 16,
    viscosity: float = 0.01,
    dt: float = 0.005,
    final_time: float = 0.05,
) -> G3NonlinearResult:
    initial = _mixed_mode_initial(grid_size)
    _, u_initial, v_initial, nonlinear_initial = _rhs_components(initial, viscosity)
    numerical, effective_dt, steps = integrate_periodic_vorticity(
        initial_vorticity=initial,
        viscosity=viscosity,
        dt=dt,
        final_time=final_time,
    )
    u_final, v_final, psi_final = _velocity_and_streamfunction(numerical)
    energy_initial = _kinetic_energy(u_initial, v_initial)
    energy_final = _kinetic_energy(u_final, v_final)
    enstrophy_initial = _enstrophy(initial)
    enstrophy_final = _enstrophy(numerical)
    mean_initial = _field_mean(initial)
    mean_final = _field_mean(numerical)
    return G3NonlinearResult(
        grid_size=grid_size,
        viscosity=viscosity,
        final_time=final_time,
        requested_dt=dt,
        effective_dt=effective_dt,
        steps=steps,
        nonlinear_rhs_rms_initial=_field_rms(nonlinear_initial),
        state_change_rms=_l2_difference(numerical, initial),
        mean_vorticity_initial=mean_initial,
        mean_vorticity_final=mean_final,
        mean_vorticity_drift=abs(mean_final - mean_initial),
        divergence_rms_final=_spectral_divergence_rms(u_final, v_final),
        poisson_residual_rms_final=_poisson_residual_rms(numerical, psi_final),
        kinetic_energy_initial=energy_initial,
        kinetic_energy_final=energy_final,
        enstrophy_initial=enstrophy_initial,
        enstrophy_final=enstrophy_final,
        energy_nonincreasing=energy_final <= energy_initial * (1.0 + 1e-10),
        enstrophy_nonincreasing=enstrophy_final <= enstrophy_initial * (1.0 + 1e-10),
    )


def _observed_order(coarse_error: float, fine_error: float, refinement_ratio: float = 2.0) -> float:
    if coarse_error <= 0.0 or fine_error <= 0.0:
        raise ValueError("convergence errors must be positive")
    return math.log(coarse_error / fine_error) / math.log(refinement_ratio)


def run_nsb_g3_benchmark(
    *,
    grid_size: int = 16,
    viscosity: float = 0.05,
    final_time: float = 0.4,
    temporal_dts: tuple[float, float, float] = (0.04, 0.02, 0.01),
    poisson_error_limit: float = 1e-10,
    divergence_limit: float = 1e-10,
    temporal_order_floor: float = 1.8,
    taylor_green_error_limit: float = 1e-6,
    mean_vorticity_drift_limit: float = 1e-12,
    nonlinear_rhs_floor: float = 1e-2,
    nonlinear_state_change_floor: float = 1e-3,
) -> NSBG3Report:
    _require_radix2(grid_size)
    if not (temporal_dts[0] == 2.0 * temporal_dts[1] and temporal_dts[1] == 2.0 * temporal_dts[2]):
        raise ValueError("G3 temporal_dts must use exact factor-two refinement")

    poisson = _manufactured_poisson_result(grid_size)
    taylor_cases = tuple(
        _taylor_green_case(
            case_id=f"taylor_green_dt_{index}",
            grid_size=grid_size,
            viscosity=viscosity,
            dt=dt,
            final_time=final_time,
        )
        for index, dt in enumerate(temporal_dts)
    )
    errors = tuple(case.vorticity_l2_error for case in taylor_cases)
    temporal_orders = (
        _observed_order(errors[0], errors[1]),
        _observed_order(errors[1], errors[2]),
    )
    nonlinear = _nonlinear_case(grid_size=grid_size)

    poisson_ok = max(
        poisson.streamfunction_l2_error,
        poisson.velocity_x_l2_error,
        poisson.velocity_y_l2_error,
        poisson.poisson_residual_rms,
    ) <= poisson_error_limit
    divergence_ok = max(
        poisson.divergence_rms,
        *(case.divergence_rms for case in taylor_cases),
        nonlinear.divergence_rms_final,
    ) <= divergence_limit
    taylor_ok = (
        min(temporal_orders) >= temporal_order_floor
        and taylor_cases[-1].vorticity_l2_error <= taylor_green_error_limit
        and all(case.kinetic_energy_final <= case.kinetic_energy_initial for case in taylor_cases)
        and all(case.enstrophy_final <= case.enstrophy_initial for case in taylor_cases)
    )
    nonlinear_ok = (
        nonlinear.mean_vorticity_drift <= mean_vorticity_drift_limit
        and nonlinear.nonlinear_rhs_rms_initial >= nonlinear_rhs_floor
        and nonlinear.state_change_rms >= nonlinear_state_change_floor
        and nonlinear.energy_nonincreasing
        and nonlinear.enstrophy_nonincreasing
        and nonlinear.poisson_residual_rms_final <= poisson_error_limit
    )
    acceptance_pass = poisson_ok and divergence_ok and taylor_ok and nonlinear_ok

    report = NSBG3Report(
        poisson_result=poisson,
        taylor_green_cases=taylor_cases,
        nonlinear_result=nonlinear,
        acceptance=G3AcceptanceSummary(
            poisson_error_limit=poisson_error_limit,
            divergence_limit=divergence_limit,
            temporal_order_floor=temporal_order_floor,
            taylor_green_error_limit=taylor_green_error_limit,
            mean_vorticity_drift_limit=mean_vorticity_drift_limit,
            nonlinear_rhs_floor=nonlinear_rhs_floor,
            nonlinear_state_change_floor=nonlinear_state_change_floor,
            temporal_orders=temporal_orders,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g3_report(report: NSBG3Report) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
