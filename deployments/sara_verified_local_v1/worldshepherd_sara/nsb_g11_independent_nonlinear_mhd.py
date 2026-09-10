from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .nsb_g3_solver import TWO_PI, _fft2, _field_mean, _field_rms, _ifft2_real, _l2_difference, _require_radix2, _wavenumbers
from .nsb_g10_nonlinear_mhd import integrate_periodic_mhd as integrate_spectral_mhd
from .qualification import CapabilityStatus, canonical_digest


class G11AlignedCase(BaseModel):
    grid_size: int = Field(ge=8)
    nonlinear_advection_rms: float = Field(ge=0.0)
    lorentz_curl_rms: float = Field(ge=0.0)
    nonlinear_cancellation_rms: float = Field(ge=0.0)
    induction_advection_rms: float = Field(ge=0.0)
    velocity_divergence_rms: float = Field(ge=0.0)
    magnetic_divergence_rms: float = Field(ge=0.0)


class G11CrossMethodPoint(BaseModel):
    grid_size: int = Field(ge=8)
    dt: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    vorticity_l2_difference: float = Field(ge=0.0)
    magnetic_potential_l2_difference: float = Field(ge=0.0)
    combined_relative_difference: float = Field(ge=0.0)


class G11CrossMethodCase(BaseModel):
    points: tuple[G11CrossMethodPoint, ...]
    observed_orders: tuple[float, ...]
    finest_combined_relative_difference: float = Field(ge=0.0)
    fd_total_energy_initial: float = Field(ge=0.0)
    fd_total_energy_final: float = Field(ge=0.0)
    spectral_total_energy_final: float = Field(ge=0.0)
    final_total_energy_relative_difference: float = Field(ge=0.0)
    fd_velocity_divergence_rms: float = Field(ge=0.0)
    fd_magnetic_divergence_rms: float = Field(ge=0.0)


class G11AcceptanceSummary(BaseModel):
    spatial_order_floor: float = Field(gt=0.0)
    cross_method_relative_limit: float = Field(gt=0.0)
    cancellation_limit: float = Field(gt=0.0)
    divergence_limit: float = Field(gt=0.0)
    energy_relative_limit: float = Field(gt=0.0)
    dissipative_energy_drop_floor: float = Field(gt=0.0)
    cross_method_pass: bool
    cancellation_pass: bool
    geometry_pass: bool
    energy_pass: bool
    acceptance_pass: bool


class NSBG11Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G11-001"
    benchmark_version: str = "1.6"
    formulation: str = "independent 2D periodic incompressible nonlinear resistive-MHD replication"
    independent_spatial_scheme: str = "second-order centered finite differences with Arakawa Jacobian"
    elliptic_solver: str = "periodic discrete-Laplacian inversion using the finite-difference Fourier symbol"
    temporal_scheme: str = "explicit midpoint RK2"
    reference_solver: str = "G10 Fourier pseudo-spectral nonlinear MHD"
    aligned_case: G11AlignedCase
    cross_method_case: G11CrossMethodCase
    acceptance: G11AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    independent_nonlinear_mhd_replication_implemented: bool = True
    arakawa_jacobian_used: bool = True
    finite_difference_dynamics_used: bool = True
    nonlinear_2d_mhd_cross_method_agreement_demonstrated: bool = True
    independent_third_party_validation_claimed: bool = False
    compressible_mhd_claimed: bool = False
    three_dimensional_mhd_claimed: bool = False
    hall_two_fluid_or_kinetic_solved: bool = False
    plasma_solved: bool = False
    adaptive_em_control_validated: bool = False
    laboratory_validation_performed: bool = False
    navier_stokes_singularity_reproduced: bool = False
    propulsion_or_shielding_validated: bool = False
    operational_validation_performed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G11 is an internal cross-method replication of the bounded G10 2D periodic incompressible nonlinear resistive-MHD reference.",
        "The G11 evolution uses finite-difference dynamics and an Arakawa Jacobian; the Fourier transform is used only to invert the discrete periodic Poisson operator.",
        "G11 is not independent third-party validation and does not establish compressible, 3D, Hall, two-fluid, kinetic, or plasma capability.",
        "Passing G11 does not establish adaptive electromagnetic control, laboratory validation, propulsion, shielding, stealth, cloaking, or operational capability.",
        "Passing G11 does not reproduce, validate, or refute a finite-time Navier-Stokes singularity construction.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG11Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.6 must remain SIMULATED_ONLY")
        if not all((
            self.independent_nonlinear_mhd_replication_implemented,
            self.arakawa_jacobian_used,
            self.finite_difference_dynamics_used,
            self.nonlinear_2d_mhd_cross_method_agreement_demonstrated,
        )):
            raise ValueError("G11 report must represent the executed internal cross-method replication")
        prohibited = (
            self.independent_third_party_validation_claimed,
            self.compressible_mhd_claimed,
            self.three_dimensional_mhd_claimed,
            self.hall_two_fluid_or_kinetic_solved,
            self.plasma_solved,
            self.adaptive_em_control_validated,
            self.laboratory_validation_performed,
            self.navier_stokes_singularity_reproduced,
            self.propulsion_or_shielding_validated,
            self.operational_validation_performed,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v1.6 cannot promote unsupported external, physical, or higher-fidelity claims")
        return self


def _dx(field):
    n = len(field)
    h = TWO_PI / n
    return [[(field[(i + 1) % n][j] - field[(i - 1) % n][j]) / (2.0 * h) for j in range(n)] for i in range(n)]


def _dy(field):
    n = len(field)
    h = TWO_PI / n
    return [[(field[i][(j + 1) % n] - field[i][(j - 1) % n]) / (2.0 * h) for j in range(n)] for i in range(n)]


def _lap(field):
    n = len(field)
    h2 = (TWO_PI / n) ** 2
    return [[
        (field[(i + 1) % n][j] + field[(i - 1) % n][j] + field[i][(j + 1) % n] + field[i][(j - 1) % n] - 4.0 * field[i][j]) / h2
        for j in range(n)
    ] for i in range(n)]


def _solve_minus_laplacian(rhs):
    n = len(rhs)
    _require_radix2(n)
    if any(len(row) != n for row in rhs):
        raise ValueError("G11 fields must be square")
    rhs_hat = _fft2(rhs)
    modes = _wavenumbers(n)
    h = TWO_PI / n
    solution_hat = [[0.0j] * n for _ in range(n)]
    for i, kx in enumerate(modes):
        for j, ky in enumerate(modes):
            symbol = 4.0 * (math.sin(0.5 * kx * h) ** 2 + math.sin(0.5 * ky * h) ** 2) / (h * h)
            solution_hat[i][j] = 0.0j if symbol <= 1e-15 else rhs_hat[i][j] / symbol
    return _ifft2_real(solution_hat)


def _arakawa_jacobian(f, g):
    n = len(f)
    h2 = (TWO_PI / n) ** 2
    out = [[0.0] * n for _ in range(n)]
    scale = 1.0 / (12.0 * h2)
    for i in range(n):
        ip, im = (i + 1) % n, (i - 1) % n
        for j in range(n):
            jp, jm = (j + 1) % n, (j - 1) % n
            j1 = (
                (f[ip][j] - f[im][j]) * (g[i][jp] - g[i][jm])
                - (f[i][jp] - f[i][jm]) * (g[ip][j] - g[im][j])
            )
            j2 = (
                f[ip][j] * (g[ip][jp] - g[ip][jm])
                - f[im][j] * (g[im][jp] - g[im][jm])
                - f[i][jp] * (g[ip][jp] - g[im][jp])
                + f[i][jm] * (g[ip][jm] - g[im][jm])
            )
            j3 = (
                g[i][jp] * (f[ip][jp] - f[im][jp])
                - g[i][jm] * (f[ip][jm] - f[im][jm])
                - g[ip][j] * (f[ip][jp] - f[ip][jm])
                + g[im][j] * (f[im][jp] - f[im][jm])
            )
            out[i][j] = scale * (j1 + j2 + j3)
    return out


def _velocity_fd(omega):
    psi = _solve_minus_laplacian(omega)
    psi_x, psi_y = _dx(psi), _dy(psi)
    u = psi_y
    v = [[-value for value in row] for row in psi_x]
    return u, v, psi


def _magnetic_fd(a):
    ax, ay = _dx(a), _dy(a)
    bx = ay
    by = [[-value for value in row] for row in ax]
    current = [[-value for value in row] for row in _lap(a)]
    return bx, by, current


def _divergence_rms(x, y):
    dx_x, dy_y = _dx(x), _dy(y)
    n = len(x)
    return math.sqrt(sum((dx_x[i][j] + dy_y[i][j]) ** 2 for i in range(n) for j in range(n)) / (n * n))


def _add_scaled_pair(omega, a, domega, da, scale):
    n = len(omega)
    return (
        [[omega[i][j] + scale * domega[i][j] for j in range(n)] for i in range(n)],
        [[a[i][j] + scale * da[i][j] for j in range(n)] for i in range(n)],
    )


def _rhs_fd(omega, a, *, viscosity: float, resistivity: float):
    if viscosity < 0.0 or resistivity < 0.0:
        raise ValueError("viscosity and resistivity must be nonnegative")
    n = len(omega)
    _require_radix2(n)
    if len(a) != n or any(len(row) != n for row in omega) or any(len(row) != n for row in a):
        raise ValueError("omega and a must be equal square fields")
    _, _, psi = _velocity_fd(omega)
    _, _, current = _magnetic_fd(a)
    adv_w = _arakawa_jacobian(psi, omega)
    lorentz_raw = _arakawa_jacobian(a, current)
    lorentz = [[-value for value in row] for row in lorentz_raw]
    adv_a = _arakawa_jacobian(psi, a)
    lap_w, lap_a = _lap(omega), _lap(a)
    domega = [[adv_w[i][j] + lorentz[i][j] + viscosity * lap_w[i][j] for j in range(n)] for i in range(n)]
    da = [[adv_a[i][j] + resistivity * lap_a[i][j] for j in range(n)] for i in range(n)]
    return domega, da, {"advection_w": adv_w, "lorentz": lorentz, "advection_a": adv_a}


def _midpoint_step_fd(omega, a, *, dt: float, viscosity: float, resistivity: float):
    k1w, k1a, _ = _rhs_fd(omega, a, viscosity=viscosity, resistivity=resistivity)
    mw, ma = _add_scaled_pair(omega, a, k1w, k1a, 0.5 * dt)
    k2w, k2a, _ = _rhs_fd(mw, ma, viscosity=viscosity, resistivity=resistivity)
    return _add_scaled_pair(omega, a, k2w, k2a, dt)


def integrate_fd_mhd(*, initial_vorticity, initial_magnetic_potential, viscosity: float, resistivity: float, dt: float, final_time: float):
    n = len(initial_vorticity)
    _require_radix2(n)
    if len(initial_magnetic_potential) != n:
        raise ValueError("initial fields must have matching dimensions")
    if dt <= 0.0 or final_time <= 0.0:
        raise ValueError("dt and final_time must be positive")
    if abs(_field_mean(initial_vorticity)) > 1e-12:
        raise ValueError("periodic discrete Poisson inversion requires near-zero mean vorticity")
    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    omega = [row[:] for row in initial_vorticity]
    a = [row[:] for row in initial_magnetic_potential]
    for _ in range(steps):
        omega, a = _midpoint_step_fd(omega, a, dt=effective_dt, viscosity=viscosity, resistivity=resistivity)
        if not all(math.isfinite(value) for row in omega for value in row) or not all(math.isfinite(value) for row in a for value in row):
            raise ValueError("G11 finite-difference integration became non-finite")
    return omega, a, effective_dt, steps


def _energetics_fd(omega, a):
    n = len(omega)
    u, v, _ = _velocity_fd(omega)
    bx, by, _ = _magnetic_fd(a)
    kinetic = 0.5 * sum(u[i][j] ** 2 + v[i][j] ** 2 for i in range(n) for j in range(n)) / (n * n)
    magnetic = 0.5 * sum(bx[i][j] ** 2 + by[i][j] ** 2 for i in range(n) for j in range(n)) / (n * n)
    return kinetic + magnetic


def _spectral_total_energy(omega, a):
    from .nsb_g10_nonlinear_mhd import _energetics
    return _energetics(omega, a, 0.0, 0.0)["total"]


def _mixed_initial(n: int):
    _require_radix2(n)
    h = TWO_PI / n
    omega = [[
        math.sin(i * h) * math.cos(2 * j * h)
        + 0.45 * math.cos(2 * i * h + j * h)
        + 0.25 * math.sin(3 * i * h - 2 * j * h)
        for j in range(n)
    ] for i in range(n)]
    a = [[
        0.7 * math.cos(i * h - j * h)
        + 0.3 * math.sin(2 * i * h + 2 * j * h)
        + 0.18 * math.cos(3 * i * h + j * h)
        for j in range(n)
    ] for i in range(n)]
    return omega, a


def _aligned_case(n: int = 32):
    h = TWO_PI / n
    psi = [[math.sin(i * h) * math.sin(j * h) + 0.2 * math.sin(2 * i * h + j * h) for j in range(n)] for i in range(n)]
    omega = [[-value for value in row] for row in _lap(psi)]
    a = [row[:] for row in psi]
    _, _, terms = _rhs_fd(omega, a, viscosity=0.0, resistivity=0.0)
    cancellation = [[terms["advection_w"][i][j] + terms["lorentz"][i][j] for j in range(n)] for i in range(n)]
    u, v, _ = _velocity_fd(omega)
    bx, by, _ = _magnetic_fd(a)
    return G11AlignedCase(
        grid_size=n,
        nonlinear_advection_rms=_field_rms(terms["advection_w"]),
        lorentz_curl_rms=_field_rms(terms["lorentz"]),
        nonlinear_cancellation_rms=_field_rms(cancellation),
        induction_advection_rms=_field_rms(terms["advection_a"]),
        velocity_divergence_rms=_divergence_rms(u, v),
        magnetic_divergence_rms=_divergence_rms(bx, by),
    )


def _cross_point(n: int, *, viscosity: float = 0.01, resistivity: float = 0.015, dt: float = 0.00025, final_time: float = 0.004):
    omega0, a0 = _mixed_initial(n)
    fd_w, fd_a, effective_dt, _ = integrate_fd_mhd(
        initial_vorticity=omega0,
        initial_magnetic_potential=a0,
        viscosity=viscosity,
        resistivity=resistivity,
        dt=dt,
        final_time=final_time,
    )
    sp_w, sp_a, _, _ = integrate_spectral_mhd(
        initial_vorticity=omega0,
        initial_magnetic_potential=a0,
        viscosity=viscosity,
        resistivity=resistivity,
        dt=dt,
        final_time=final_time,
    )
    ew = _l2_difference(fd_w, sp_w)
    ea = _l2_difference(fd_a, sp_a)
    denom = math.sqrt(_field_rms(sp_w) ** 2 + _field_rms(sp_a) ** 2)
    combined = math.sqrt(ew * ew + ea * ea) / max(denom, 1e-15)
    return G11CrossMethodPoint(
        grid_size=n,
        dt=effective_dt,
        final_time=final_time,
        vorticity_l2_difference=ew,
        magnetic_potential_l2_difference=ea,
        combined_relative_difference=combined,
    )


def _cross_method_case():
    points = tuple(_cross_point(n) for n in (16, 32, 64))
    orders = tuple(math.log(points[i].combined_relative_difference / points[i + 1].combined_relative_difference, 2.0) for i in range(len(points) - 1))
    n = 64
    omega0, a0 = _mixed_initial(n)
    e0 = _energetics_fd(omega0, a0)
    fd_w, fd_a, _, _ = integrate_fd_mhd(initial_vorticity=omega0, initial_magnetic_potential=a0, viscosity=0.01, resistivity=0.015, dt=0.00025, final_time=0.01)
    sp_w, sp_a, _, _ = integrate_spectral_mhd(initial_vorticity=omega0, initial_magnetic_potential=a0, viscosity=0.01, resistivity=0.015, dt=0.00025, final_time=0.01)
    efd = _energetics_fd(fd_w, fd_a)
    esp = _spectral_total_energy(sp_w, sp_a)
    u, v, _ = _velocity_fd(fd_w)
    bx, by, _ = _magnetic_fd(fd_a)
    return G11CrossMethodCase(
        points=points,
        observed_orders=orders,
        finest_combined_relative_difference=points[-1].combined_relative_difference,
        fd_total_energy_initial=e0,
        fd_total_energy_final=efd,
        spectral_total_energy_final=esp,
        final_total_energy_relative_difference=abs(efd - esp) / max(abs(esp), 1e-15),
        fd_velocity_divergence_rms=_divergence_rms(u, v),
        fd_magnetic_divergence_rms=_divergence_rms(bx, by),
    )


def run_nsb_g11_benchmark(
    *,
    spatial_order_floor: float = 1.6,
    cross_method_relative_limit: float = 0.01,
    cancellation_limit: float = 1e-10,
    divergence_limit: float = 1e-10,
    energy_relative_limit: float = 0.01,
    dissipative_energy_drop_floor: float = 1e-5,
) -> NSBG11Report:
    aligned = _aligned_case()
    cross = _cross_method_case()
    cross_pass = min(cross.observed_orders) >= spatial_order_floor and cross.finest_combined_relative_difference <= cross_method_relative_limit
    cancellation_pass = (
        aligned.nonlinear_advection_rms > 1e-3
        and aligned.lorentz_curl_rms > 1e-3
        and aligned.nonlinear_cancellation_rms <= cancellation_limit
        and aligned.induction_advection_rms <= cancellation_limit
    )
    geometry_pass = max(
        aligned.velocity_divergence_rms,
        aligned.magnetic_divergence_rms,
        cross.fd_velocity_divergence_rms,
        cross.fd_magnetic_divergence_rms,
    ) <= divergence_limit
    energy_pass = (
        cross.fd_total_energy_final <= cross.fd_total_energy_initial - dissipative_energy_drop_floor
        and cross.final_total_energy_relative_difference <= energy_relative_limit
    )
    acceptance_pass = all((cross_pass, cancellation_pass, geometry_pass, energy_pass))
    report = NSBG11Report(
        aligned_case=aligned,
        cross_method_case=cross,
        acceptance=G11AcceptanceSummary(
            spatial_order_floor=spatial_order_floor,
            cross_method_relative_limit=cross_method_relative_limit,
            cancellation_limit=cancellation_limit,
            divergence_limit=divergence_limit,
            energy_relative_limit=energy_relative_limit,
            dissipative_energy_drop_floor=dissipative_energy_drop_floor,
            cross_method_pass=cross_pass,
            cancellation_pass=cancellation_pass,
            geometry_pass=geometry_pass,
            energy_pass=energy_pass,
            acceptance_pass=acceptance_pass,
        ),
        nonlinear_2d_mhd_cross_method_agreement_demonstrated=acceptance_pass,
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g11_report(report: NSBG11Report) -> bool:
    return report.report_digest == canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
