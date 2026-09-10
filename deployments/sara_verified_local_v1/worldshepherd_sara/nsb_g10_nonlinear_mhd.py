from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .nsb_g3_solver import (
    TWO_PI,
    _fft2,
    _field_mean,
    _field_rms,
    _ifft2_real,
    _l2_difference,
    _require_radix2,
    _spectral_divergence_rms,
    _two_thirds_dealias,
    _velocity_and_streamfunction,
    _wavenumbers,
)
from .qualification import CapabilityStatus, canonical_digest


class G10ExactCase(BaseModel):
    grid_size: int = Field(ge=8)
    viscosity: float = Field(ge=0.0)
    resistivity: float = Field(ge=0.0)
    final_time: float = Field(gt=0.0)
    dt: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    vorticity_l2_error: float = Field(ge=0.0)
    magnetic_potential_l2_error: float = Field(ge=0.0)
    nonlinear_advection_rms_initial: float = Field(ge=0.0)
    lorentz_curl_rms_initial: float = Field(ge=0.0)
    nonlinear_cancellation_rms_initial: float = Field(ge=0.0)
    velocity_divergence_rms: float = Field(ge=0.0)
    magnetic_divergence_rms: float = Field(ge=0.0)


class G10NonlinearCase(BaseModel):
    grid_size: int = Field(ge=8)
    viscosity: float = Field(gt=0.0)
    resistivity: float = Field(gt=0.0)
    final_time: float = Field(gt=0.0)
    dt: float = Field(gt=0.0)
    steps: int = Field(ge=1)
    nonlinear_rhs_rms_initial: float = Field(ge=0.0)
    kinetic_energy_initial: float = Field(ge=0.0)
    kinetic_energy_final: float = Field(ge=0.0)
    magnetic_energy_initial: float = Field(ge=0.0)
    magnetic_energy_final: float = Field(ge=0.0)
    total_energy_initial: float = Field(ge=0.0)
    total_energy_final: float = Field(ge=0.0)
    viscous_dissipation_initial: float = Field(ge=0.0)
    resistive_dissipation_initial: float = Field(ge=0.0)
    instantaneous_energy_budget_residual: float = Field(ge=0.0)
    cross_helicity_initial: float
    cross_helicity_final: float
    magnetic_potential_variance_initial: float = Field(ge=0.0)
    magnetic_potential_variance_final: float = Field(ge=0.0)
    mean_vorticity_drift: float = Field(ge=0.0)
    mean_magnetic_potential_drift: float = Field(ge=0.0)
    velocity_divergence_rms_final: float = Field(ge=0.0)
    magnetic_divergence_rms_final: float = Field(ge=0.0)


class G10IdealInvariantCase(BaseModel):
    grid_size: int = Field(ge=8)
    final_time: float = Field(gt=0.0)
    dt: float = Field(gt=0.0)
    total_energy_relative_drift: float = Field(ge=0.0)
    cross_helicity_relative_drift: float = Field(ge=0.0)
    magnetic_potential_variance_relative_drift: float = Field(ge=0.0)


class G10AcceptanceSummary(BaseModel):
    exact_l2_limit: float = Field(gt=0.0)
    cancellation_limit: float = Field(gt=0.0)
    divergence_limit: float = Field(gt=0.0)
    energy_budget_limit: float = Field(gt=0.0)
    nonlinear_rhs_floor: float = Field(gt=0.0)
    nonlinear_energy_drop_floor: float = Field(gt=0.0)
    ideal_invariant_drift_limit: float = Field(gt=0.0)
    exact_solution_pass: bool
    nonlinear_cancellation_pass: bool
    geometry_pass: bool
    energy_budget_pass: bool
    nonlinear_evolution_pass: bool
    ideal_invariants_pass: bool
    acceptance_pass: bool


class NSBG10Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G10-001"
    benchmark_version: str = "1.5"
    formulation: str = "bounded 2D periodic incompressible nonlinear resistive MHD in vorticity-vector-potential form"
    equations: tuple[str, str] = (
        "domega/dt = -u.grad(omega) + B.grad(j) + nu*laplacian(omega)",
        "da/dt = -u.grad(a) + eta*laplacian(a)",
    )
    magnetic_convention: str = "B=(d_y a,-d_x a), j=-laplacian(a)"
    temporal_scheme: str = "explicit midpoint RK2"
    spatial_scheme: str = "Fourier pseudo-spectral derivatives with two-thirds dealiased nonlinear products"
    exact_case: G10ExactCase
    nonlinear_case: G10NonlinearCase
    ideal_invariant_case: G10IdealInvariantCase
    acceptance: G10AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    nonlinear_2d_mhd_implemented: bool = True
    induction_equation_evolved: bool = True
    reciprocal_lorentz_backreaction_evolved: bool = True
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
        "G10 implements a bounded 2D periodic incompressible nonlinear resistive-MHD reference in vorticity/vector-potential form.",
        "It evolves magnetic induction and reciprocal Lorentz backreaction but does not establish compressible, 3D, Hall, two-fluid, kinetic, or plasma capability.",
        "The periodic domain is a numerical reference, not a claim of general magnetofluid boundary-condition capability.",
        "Passing G10 does not establish adaptive electromagnetic control or laboratory, propulsion, shielding, stealth, cloaking, or operational capability.",
        "Passing G10 does not reproduce, validate, or refute a finite-time Navier-Stokes singularity construction.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG10Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.5 must remain SIMULATED_ONLY")
        if not all((self.nonlinear_2d_mhd_implemented, self.induction_equation_evolved, self.reciprocal_lorentz_backreaction_evolved)):
            raise ValueError("G10 report must represent the complete bounded nonlinear MHD reference")
        prohibited = (
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
            raise ValueError("WS-NSB v1.5 cannot promote unsupported physical or higher-fidelity MHD claims")
        return self


def _spectral_derivatives(field):
    n = len(field)
    hat = _fft2(field)
    modes = _wavenumbers(n)
    dx_hat = [[0.0j] * n for _ in range(n)]
    dy_hat = [[0.0j] * n for _ in range(n)]
    lap_hat = [[0.0j] * n for _ in range(n)]
    for i, kx in enumerate(modes):
        for j, ky in enumerate(modes):
            value = hat[i][j]
            k2 = kx * kx + ky * ky
            dx_hat[i][j] = 1j * kx * value
            dy_hat[i][j] = 1j * ky * value
            lap_hat[i][j] = -k2 * value
    return _ifft2_real(dx_hat), _ifft2_real(dy_hat), _ifft2_real(lap_hat)


def _magnetic_state(a):
    da_dx, da_dy, lap_a = _spectral_derivatives(a)
    bx = da_dy
    by = [[-value for value in row] for row in da_dx]
    current = [[-value for value in row] for row in lap_a]
    return bx, by, current


def _add_scaled_pair(omega, a, domega, da, scale):
    n = len(omega)
    return (
        [[omega[i][j] + scale * domega[i][j] for j in range(n)] for i in range(n)],
        [[a[i][j] + scale * da[i][j] for j in range(n)] for i in range(n)],
    )


def _rhs(omega, a, *, viscosity: float, resistivity: float):
    if viscosity < 0.0 or resistivity < 0.0:
        raise ValueError("viscosity and resistivity must be nonnegative")
    n = len(omega)
    if len(a) != n or any(len(row) != n for row in omega) or any(len(row) != n for row in a):
        raise ValueError("omega and a must be equal square fields")
    u, v, _ = _velocity_and_streamfunction(omega)
    dw_dx, dw_dy, lap_w = _spectral_derivatives(omega)
    da_dx, da_dy, lap_a = _spectral_derivatives(a)
    bx = da_dy
    by = [[-value for value in row] for row in da_dx]
    current = [[-value for value in row] for row in lap_a]
    dj_dx, dj_dy, _ = _spectral_derivatives(current)
    adv_w = [[-(u[i][j] * dw_dx[i][j] + v[i][j] * dw_dy[i][j]) for j in range(n)] for i in range(n)]
    lorentz = [[bx[i][j] * dj_dx[i][j] + by[i][j] * dj_dy[i][j] for j in range(n)] for i in range(n)]
    adv_a = [[-(u[i][j] * da_dx[i][j] + v[i][j] * da_dy[i][j]) for j in range(n)] for i in range(n)]
    adv_w = _two_thirds_dealias(adv_w)
    lorentz = _two_thirds_dealias(lorentz)
    adv_a = _two_thirds_dealias(adv_a)
    domega = [[adv_w[i][j] + lorentz[i][j] + viscosity * lap_w[i][j] for j in range(n)] for i in range(n)]
    da_dt = [[adv_a[i][j] + resistivity * lap_a[i][j] for j in range(n)] for i in range(n)]
    return domega, da_dt, {"advection_w": adv_w, "lorentz": lorentz, "advection_a": adv_a}


def _midpoint_step(omega, a, *, dt: float, viscosity: float, resistivity: float):
    k1w, k1a, _ = _rhs(omega, a, viscosity=viscosity, resistivity=resistivity)
    mw, ma = _add_scaled_pair(omega, a, k1w, k1a, 0.5 * dt)
    k2w, k2a, _ = _rhs(mw, ma, viscosity=viscosity, resistivity=resistivity)
    return _add_scaled_pair(omega, a, k2w, k2a, dt)


def integrate_periodic_mhd(*, initial_vorticity, initial_magnetic_potential, viscosity: float, resistivity: float, dt: float, final_time: float):
    n = len(initial_vorticity)
    _require_radix2(n)
    if len(initial_magnetic_potential) != n:
        raise ValueError("initial fields must have matching dimensions")
    if dt <= 0.0 or final_time <= 0.0:
        raise ValueError("dt and final_time must be positive")
    if abs(_field_mean(initial_vorticity)) > 1e-12:
        raise ValueError("periodic streamfunction inversion requires near-zero mean vorticity")
    steps = max(1, round(final_time / dt))
    effective_dt = final_time / steps
    omega = [row[:] for row in initial_vorticity]
    a = [row[:] for row in initial_magnetic_potential]
    for _ in range(steps):
        omega, a = _midpoint_step(omega, a, dt=effective_dt, viscosity=viscosity, resistivity=resistivity)
        if not all(math.isfinite(value) for row in omega for value in row) or not all(math.isfinite(value) for row in a for value in row):
            raise ValueError("G10 integration became non-finite")
    return omega, a, effective_dt, steps


def _energetics(omega, a, viscosity: float, resistivity: float):
    n = len(omega)
    u, v, _ = _velocity_and_streamfunction(omega)
    bx, by, current = _magnetic_state(a)
    kinetic = 0.5 * sum(u[i][j] ** 2 + v[i][j] ** 2 for i in range(n) for j in range(n)) / (n * n)
    magnetic = 0.5 * sum(bx[i][j] ** 2 + by[i][j] ** 2 for i in range(n) for j in range(n)) / (n * n)
    cross = sum(u[i][j] * bx[i][j] + v[i][j] * by[i][j] for i in range(n) for j in range(n)) / (n * n)
    a_var = 0.5 * sum(value * value for row in a for value in row) / (n * n)
    viscous = viscosity * sum(value * value for row in omega for value in row) / (n * n)
    resistive = resistivity * sum(value * value for row in current for value in row) / (n * n)
    return {"kinetic": kinetic, "magnetic": magnetic, "total": kinetic + magnetic, "cross": cross, "a_var": a_var, "viscous": viscous, "resistive": resistive}


def _energy_tendency_from_rhs(omega, a, viscosity: float, resistivity: float, epsilon: float = 1e-6) -> float:
    domega, da, _ = _rhs(omega, a, viscosity=viscosity, resistivity=resistivity)
    pw, pa = _add_scaled_pair(omega, a, domega, da, epsilon)
    mw, ma = _add_scaled_pair(omega, a, domega, da, -epsilon)
    return (_energetics(pw, pa, viscosity, resistivity)["total"] - _energetics(mw, ma, viscosity, resistivity)["total"]) / (2.0 * epsilon)


def _aligned_initial(n: int):
    _require_radix2(n)
    dx = TWO_PI / n
    psi = [[math.sin(i * dx) * math.sin(j * dx) + 0.2 * math.sin(2 * i * dx + j * dx) for j in range(n)] for i in range(n)]
    psi_hat = _fft2(psi)
    modes = _wavenumbers(n)
    omega_hat = [[0.0j] * n for _ in range(n)]
    for i, kx in enumerate(modes):
        for j, ky in enumerate(modes):
            omega_hat[i][j] = (kx * kx + ky * ky) * psi_hat[i][j]
    return _ifft2_real(omega_hat), psi


def _mixed_initial(n: int):
    _require_radix2(n)
    dx = TWO_PI / n
    omega = [[math.sin(i * dx) * math.cos(2 * j * dx) + 0.45 * math.cos(2 * i * dx + j * dx) + 0.25 * math.sin(3 * i * dx - 2 * j * dx) for j in range(n)] for i in range(n)]
    a = [[0.7 * math.cos(i * dx - j * dx) + 0.3 * math.sin(2 * i * dx + 2 * j * dx) + 0.18 * math.cos(3 * i * dx + j * dx) for j in range(n)] for i in range(n)]
    return omega, a


def _exact_case(n: int = 32, diffusivity: float = 0.02, dt: float = 0.001, final_time: float = 0.05):
    omega0, a0 = _aligned_initial(n)
    _, _, c0 = _rhs(omega0, a0, viscosity=diffusivity, resistivity=diffusivity)
    cancellation = [[c0["advection_w"][i][j] + c0["lorentz"][i][j] for j in range(n)] for i in range(n)]
    omega, a, effective_dt, steps = integrate_periodic_mhd(initial_vorticity=omega0, initial_magnetic_potential=a0, viscosity=diffusivity, resistivity=diffusivity, dt=dt, final_time=final_time)
    a0_hat, w0_hat = _fft2(a0), _fft2(omega0)
    modes = _wavenumbers(n)
    aeh = [[0.0j] * n for _ in range(n)]
    weh = [[0.0j] * n for _ in range(n)]
    for i, kx in enumerate(modes):
        for j, ky in enumerate(modes):
            decay = math.exp(-diffusivity * (kx * kx + ky * ky) * final_time)
            aeh[i][j] = a0_hat[i][j] * decay
            weh[i][j] = w0_hat[i][j] * decay
    u, v, _ = _velocity_and_streamfunction(omega)
    bx, by, _ = _magnetic_state(a)
    return G10ExactCase(grid_size=n, viscosity=diffusivity, resistivity=diffusivity, final_time=final_time, dt=effective_dt, steps=steps, vorticity_l2_error=_l2_difference(omega, _ifft2_real(weh)), magnetic_potential_l2_error=_l2_difference(a, _ifft2_real(aeh)), nonlinear_advection_rms_initial=_field_rms(c0["advection_w"]), lorentz_curl_rms_initial=_field_rms(c0["lorentz"]), nonlinear_cancellation_rms_initial=_field_rms(cancellation), velocity_divergence_rms=_spectral_divergence_rms(u, v), magnetic_divergence_rms=_spectral_divergence_rms(bx, by))


def _nonlinear_case(n: int = 32, viscosity: float = 0.01, resistivity: float = 0.015, dt: float = 0.0005, final_time: float = 0.02):
    omega0, a0 = _mixed_initial(n)
    e0 = _energetics(omega0, a0, viscosity, resistivity)
    dw0, da0, _ = _rhs(omega0, a0, viscosity=viscosity, resistivity=resistivity)
    rhs_norm = math.sqrt(_field_rms(dw0) ** 2 + _field_rms(da0) ** 2)
    budget_residual = abs(_energy_tendency_from_rhs(omega0, a0, viscosity, resistivity) + e0["viscous"] + e0["resistive"])
    omega, a, effective_dt, steps = integrate_periodic_mhd(initial_vorticity=omega0, initial_magnetic_potential=a0, viscosity=viscosity, resistivity=resistivity, dt=dt, final_time=final_time)
    ef = _energetics(omega, a, viscosity, resistivity)
    u, v, _ = _velocity_and_streamfunction(omega)
    bx, by, _ = _magnetic_state(a)
    return G10NonlinearCase(grid_size=n, viscosity=viscosity, resistivity=resistivity, final_time=final_time, dt=effective_dt, steps=steps, nonlinear_rhs_rms_initial=rhs_norm, kinetic_energy_initial=e0["kinetic"], kinetic_energy_final=ef["kinetic"], magnetic_energy_initial=e0["magnetic"], magnetic_energy_final=ef["magnetic"], total_energy_initial=e0["total"], total_energy_final=ef["total"], viscous_dissipation_initial=e0["viscous"], resistive_dissipation_initial=e0["resistive"], instantaneous_energy_budget_residual=budget_residual, cross_helicity_initial=e0["cross"], cross_helicity_final=ef["cross"], magnetic_potential_variance_initial=e0["a_var"], magnetic_potential_variance_final=ef["a_var"], mean_vorticity_drift=abs(_field_mean(omega) - _field_mean(omega0)), mean_magnetic_potential_drift=abs(_field_mean(a) - _field_mean(a0)), velocity_divergence_rms_final=_spectral_divergence_rms(u, v), magnetic_divergence_rms_final=_spectral_divergence_rms(bx, by))


def _relative_drift(initial: float, final: float) -> float:
    return abs(final - initial) / max(abs(initial), 1e-12)


def _ideal_case(n: int = 32, dt: float = 0.00025, final_time: float = 0.01):
    omega0, a0 = _mixed_initial(n)
    e0 = _energetics(omega0, a0, 0.0, 0.0)
    omega, a, effective_dt, _ = integrate_periodic_mhd(initial_vorticity=omega0, initial_magnetic_potential=a0, viscosity=0.0, resistivity=0.0, dt=dt, final_time=final_time)
    ef = _energetics(omega, a, 0.0, 0.0)
    return G10IdealInvariantCase(grid_size=n, final_time=final_time, dt=effective_dt, total_energy_relative_drift=_relative_drift(e0["total"], ef["total"]), cross_helicity_relative_drift=_relative_drift(e0["cross"], ef["cross"]), magnetic_potential_variance_relative_drift=_relative_drift(e0["a_var"], ef["a_var"]))


def run_nsb_g10_benchmark(*, exact_l2_limit: float = 2e-5, cancellation_limit: float = 1e-10, divergence_limit: float = 1e-10, energy_budget_limit: float = 2e-8, nonlinear_rhs_floor: float = 1e-2, nonlinear_energy_drop_floor: float = 1e-5, ideal_invariant_drift_limit: float = 2e-5) -> NSBG10Report:
    exact, nonlinear, ideal = _exact_case(), _nonlinear_case(), _ideal_case()
    exact_pass = max(exact.vorticity_l2_error, exact.magnetic_potential_l2_error) <= exact_l2_limit
    cancellation_pass = exact.nonlinear_advection_rms_initial > 1e-3 and exact.lorentz_curl_rms_initial > 1e-3 and exact.nonlinear_cancellation_rms_initial <= cancellation_limit
    geometry_pass = max(exact.velocity_divergence_rms, exact.magnetic_divergence_rms, nonlinear.velocity_divergence_rms_final, nonlinear.magnetic_divergence_rms_final) <= divergence_limit
    energy_budget_pass = nonlinear.instantaneous_energy_budget_residual <= energy_budget_limit
    nonlinear_pass = nonlinear.nonlinear_rhs_rms_initial >= nonlinear_rhs_floor and nonlinear.total_energy_final <= nonlinear.total_energy_initial - nonlinear_energy_drop_floor and nonlinear.viscous_dissipation_initial > 0.0 and nonlinear.resistive_dissipation_initial > 0.0 and nonlinear.mean_vorticity_drift <= 1e-12 and nonlinear.mean_magnetic_potential_drift <= 1e-12
    ideal_pass = max(ideal.total_energy_relative_drift, ideal.cross_helicity_relative_drift, ideal.magnetic_potential_variance_relative_drift) <= ideal_invariant_drift_limit
    acceptance_pass = all((exact_pass, cancellation_pass, geometry_pass, energy_budget_pass, nonlinear_pass, ideal_pass))
    report = NSBG10Report(exact_case=exact, nonlinear_case=nonlinear, ideal_invariant_case=ideal, acceptance=G10AcceptanceSummary(exact_l2_limit=exact_l2_limit, cancellation_limit=cancellation_limit, divergence_limit=divergence_limit, energy_budget_limit=energy_budget_limit, nonlinear_rhs_floor=nonlinear_rhs_floor, nonlinear_energy_drop_floor=nonlinear_energy_drop_floor, ideal_invariant_drift_limit=ideal_invariant_drift_limit, exact_solution_pass=exact_pass, nonlinear_cancellation_pass=cancellation_pass, geometry_pass=geometry_pass, energy_budget_pass=energy_budget_pass, nonlinear_evolution_pass=nonlinear_pass, ideal_invariants_pass=ideal_pass, acceptance_pass=acceptance_pass))
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g10_report(report: NSBG10Report) -> bool:
    return report.report_digest == canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
