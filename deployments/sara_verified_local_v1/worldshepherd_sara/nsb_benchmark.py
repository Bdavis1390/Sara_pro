from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


Vec3 = tuple[float, float, float]
VectorField = Callable[[float, float, float], Vec3]


class NSBGate(str, Enum):
    G0_INSTRUMENTATION = "G0_INSTRUMENTATION"
    G1_SCALING = "G1_SCALING"


class ControlOutcome(str, Enum):
    SUPPRESSION = "SUPPRESSION"
    NEUTRAL = "NEUTRAL"
    AMPLIFICATION = "AMPLIFICATION"
    REDIRECTION = "REDIRECTION"


class VerificationEscalation(str, Enum):
    NORMAL = "NORMAL"
    REFINE_TIMESTEP = "REFINE_TIMESTEP"
    REFINE_TIMESTEP_AND_MESH = "REFINE_TIMESTEP_AND_MESH"
    REQUIRE_INDEPENDENT_SOLVER = "REQUIRE_INDEPENDENT_SOLVER"


class ResolutionDiagnostic(BaseModel):
    resolution: int = Field(ge=4)
    spacing_radians: float = Field(gt=0.0)
    vorticity_l2_error: float = Field(ge=0.0)
    known_divergence_l2_error: float = Field(ge=0.0)
    div_u_rms: float = Field(ge=0.0)
    div_b_rms: float = Field(ge=0.0)
    vortex_stretching_rms: float = Field(ge=0.0)
    em_vorticity_forcing_rms: float = Field(ge=0.0)


class ScalingDiagnostic(BaseModel):
    h_exponent: float = Field(gt=0.0, lt=0.01)
    radial_length_slope: float
    axial_length_slope: float
    peak_velocity_slope: float
    core_energy_slope: float
    angular_reynolds_slope: float
    target_radial_length_slope: float
    target_axial_length_slope: float
    target_peak_velocity_slope: float
    target_core_energy_slope: float
    target_angular_reynolds_slope: float
    max_absolute_slope_error: float = Field(ge=0.0)


class NSBSummary(BaseModel):
    vorticity_observed_orders: tuple[float, ...]
    divergence_observed_orders: tuple[float, ...]
    second_order_vorticity_convergence_observed: bool
    second_order_divergence_convergence_observed: bool
    scaling_instrumentation_passed: bool
    g0_passed: bool
    g1_passed: bool


class NSBBenchmarkReport(BaseModel):
    qualification_id: str = "WS-NSB-2026-001"
    benchmark_version: str = "0.6"
    gates: tuple[NSBGate, ...] = (
        NSBGate.G0_INSTRUMENTATION,
        NSBGate.G1_SCALING,
    )
    source_claim_status: str = "PUBLISHED_FORMALIZED_EXTERNAL_ACCEPTANCE_PENDING"
    resolutions: tuple[int, ...]
    diagnostics: tuple[ResolutionDiagnostic, ...]
    scaling: ScalingDiagnostic
    summary: NSBSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    pde_time_integration_performed: bool = False
    navier_stokes_blowup_reproduced: bool = False
    mhd_solver_used: bool = False
    plasma_solver_used: bool = False
    laboratory_validation_performed: bool = False
    propulsion_effect_validated: bool = False
    shielding_effect_validated: bool = False
    claims_boundary: tuple[str, ...] = (
        "WS-NSB v0.6 validates manufactured differential operators and asymptotic-scaling instrumentation only.",
        "No Navier-Stokes time integration or finite-time singularity reproduction is performed by this benchmark.",
        "No MHD solver, plasma solver, laboratory experiment, propulsion effect, or shielding effect is represented.",
        "A G0/G1 PASS is software evidence only and must not be promoted to a physical capability claim.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBBenchmarkReport":
        prohibited = (
            self.pde_time_integration_performed,
            self.navier_stokes_blowup_reproduced,
            self.mhd_solver_used,
            self.plasma_solver_used,
            self.laboratory_validation_performed,
            self.propulsion_effect_validated,
            self.shielding_effect_validated,
        )
        if any(prohibited):
            raise ValueError("WS-NSB v0.6 cannot promote PDE, singularity, MHD, plasma, laboratory, propulsion, or shielding claims")
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v0.6 must remain SIMULATED_ONLY")
        return self


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(value: Vec3, factor: float) -> Vec3:
    return (value[0] * factor, value[1] * factor, value[2] * factor)


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(value: Vec3) -> float:
    return math.sqrt(_dot(value, value))


def _rms(values: Iterable[float]) -> float:
    collected = tuple(values)
    if not collected:
        raise ValueError("RMS requires at least one value")
    return math.sqrt(sum(value * value for value in collected) / len(collected))


def _partial(field: VectorField, axis: int, x: float, y: float, z: float, step: float) -> Vec3:
    coordinates_plus = [x, y, z]
    coordinates_minus = [x, y, z]
    coordinates_plus[axis] += step
    coordinates_minus[axis] -= step
    plus = field(*coordinates_plus)
    minus = field(*coordinates_minus)
    return _scale(_sub(plus, minus), 1.0 / (2.0 * step))


def divergence(field: VectorField, x: float, y: float, z: float, step: float) -> float:
    dx = _partial(field, 0, x, y, z, step)
    dy = _partial(field, 1, x, y, z, step)
    dz = _partial(field, 2, x, y, z, step)
    return dx[0] + dy[1] + dz[2]


def curl(field: VectorField, x: float, y: float, z: float, step: float) -> Vec3:
    dx = _partial(field, 0, x, y, z, step)
    dy = _partial(field, 1, x, y, z, step)
    dz = _partial(field, 2, x, y, z, step)
    return (
        dy[2] - dz[1],
        dz[0] - dx[2],
        dx[1] - dy[0],
    )


def strain_tensor(field: VectorField, x: float, y: float, z: float, step: float) -> tuple[Vec3, Vec3, Vec3]:
    derivatives = (
        _partial(field, 0, x, y, z, step),
        _partial(field, 1, x, y, z, step),
        _partial(field, 2, x, y, z, step),
    )
    return tuple(
        tuple(0.5 * (derivatives[j][i] + derivatives[i][j]) for j in range(3))
        for i in range(3)
    )  # type: ignore[return-value]


def _matvec(matrix: tuple[Vec3, Vec3, Vec3], vector: Vec3) -> Vec3:
    return (
        _dot(matrix[0], vector),
        _dot(matrix[1], vector),
        _dot(matrix[2], vector),
    )


def manufactured_velocity(x: float, y: float, z: float) -> Vec3:
    """Unit ABC Beltrami flow: divergence-free and curl(u) = u exactly."""
    return (
        math.sin(z) + math.cos(y),
        math.sin(x) + math.cos(z),
        math.sin(y) + math.cos(x),
    )


def manufactured_magnetic_field(x: float, y: float, z: float) -> Vec3:
    """Divergence-free manufactured magnetic field."""
    return (math.sin(y), math.sin(z), math.sin(x))


def manufactured_divergent_field(x: float, y: float, z: float) -> Vec3:
    return (math.sin(x), math.sin(y), math.sin(z))


def manufactured_divergent_field_exact_divergence(x: float, y: float, z: float) -> float:
    return math.cos(x) + math.cos(y) + math.cos(z)


def manufactured_current_density(x: float, y: float, z: float) -> Vec3:
    """Analytic curl(B) for the manufactured magnetic field, with constants normalized to one."""
    return (-math.cos(z), -math.cos(x), -math.cos(y))


def manufactured_lorentz_proxy(x: float, y: float, z: float) -> Vec3:
    return _cross(
        manufactured_current_density(x, y, z),
        manufactured_magnetic_field(x, y, z),
    )


def _grid_points(resolution: int) -> Iterable[tuple[float, float, float]]:
    step = 2.0 * math.pi / resolution
    for i in range(resolution):
        x = i * step
        for j in range(resolution):
            y = j * step
            for k in range(resolution):
                yield x, y, k * step


def _resolution_diagnostic(resolution: int) -> ResolutionDiagnostic:
    step = 2.0 * math.pi / resolution
    vorticity_errors: list[float] = []
    divergence_errors: list[float] = []
    div_u_values: list[float] = []
    div_b_values: list[float] = []
    stretching_values: list[float] = []
    em_forcing_values: list[float] = []

    for x, y, z in _grid_points(resolution):
        numerical_vorticity = curl(manufactured_velocity, x, y, z, step)
        exact_vorticity = manufactured_velocity(x, y, z)
        vorticity_errors.append(_norm(_sub(numerical_vorticity, exact_vorticity)))

        numerical_known_divergence = divergence(
            manufactured_divergent_field,
            x,
            y,
            z,
            step,
        )
        exact_known_divergence = manufactured_divergent_field_exact_divergence(x, y, z)
        divergence_errors.append(numerical_known_divergence - exact_known_divergence)

        div_u_values.append(divergence(manufactured_velocity, x, y, z, step))
        div_b_values.append(divergence(manufactured_magnetic_field, x, y, z, step))

        strain = strain_tensor(manufactured_velocity, x, y, z, step)
        stretching_values.append(_dot(numerical_vorticity, _matvec(strain, numerical_vorticity)))

        em_curl = curl(manufactured_lorentz_proxy, x, y, z, step)
        em_forcing_values.append(_norm(em_curl))

    return ResolutionDiagnostic(
        resolution=resolution,
        spacing_radians=step,
        vorticity_l2_error=_rms(vorticity_errors),
        known_divergence_l2_error=_rms(divergence_errors),
        div_u_rms=_rms(div_u_values),
        div_b_rms=_rms(div_b_values),
        vortex_stretching_rms=_rms(stretching_values),
        em_vorticity_forcing_rms=_rms(em_forcing_values),
    )


def _observed_orders(
    diagnostics: tuple[ResolutionDiagnostic, ...],
    attribute: str,
) -> tuple[float, ...]:
    orders: list[float] = []
    for coarse, fine in zip(diagnostics[:-1], diagnostics[1:], strict=True):
        coarse_error = float(getattr(coarse, attribute))
        fine_error = float(getattr(fine, attribute))
        if coarse_error <= 0.0 or fine_error <= 0.0:
            raise ValueError("convergence-order calculation requires positive errors")
        ratio_h = coarse.spacing_radians / fine.spacing_radians
        if ratio_h <= 1.0:
            raise ValueError("diagnostics must progress from coarse to fine spacing")
        orders.append(math.log(coarse_error / fine_error) / math.log(ratio_h))
    return tuple(orders)


def _log_slope(xs: tuple[float, ...], ys: tuple[float, ...]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("log-slope fit requires equal-length sequences with at least two points")
    if any(value <= 0.0 for value in xs + ys):
        raise ValueError("log-slope fit requires strictly positive values")
    lx = tuple(math.log(value) for value in xs)
    ly = tuple(math.log(value) for value in ys)
    mean_x = sum(lx) / len(lx)
    mean_y = sum(ly) / len(ly)
    denominator = sum((value - mean_x) ** 2 for value in lx)
    if denominator <= 0.0:
        raise ValueError("degenerate log-slope input")
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(lx, ly, strict=True)) / denominator


def _scaling_diagnostic(h_exponent: float) -> ScalingDiagnostic:
    if not 0.0 < h_exponent < 0.01:
        raise ValueError("h_exponent must satisfy 0 < h < 0.01")

    tau = (0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001)
    targets = {
        "radial": 0.5,
        "axial": 0.5 - h_exponent,
        "velocity": -0.5 - h_exponent,
        "energy": 0.5 - 3.0 * h_exponent,
        "re_theta": -h_exponent,
    }

    radial = tuple(value ** targets["radial"] for value in tau)
    axial = tuple(value ** targets["axial"] for value in tau)
    velocity = tuple(value ** targets["velocity"] for value in tau)
    energy = tuple(value ** targets["energy"] for value in tau)
    re_theta = tuple(value ** targets["re_theta"] for value in tau)

    measured = {
        "radial": _log_slope(tau, radial),
        "axial": _log_slope(tau, axial),
        "velocity": _log_slope(tau, velocity),
        "energy": _log_slope(tau, energy),
        "re_theta": _log_slope(tau, re_theta),
    }
    max_error = max(abs(measured[key] - targets[key]) for key in targets)

    return ScalingDiagnostic(
        h_exponent=h_exponent,
        radial_length_slope=measured["radial"],
        axial_length_slope=measured["axial"],
        peak_velocity_slope=measured["velocity"],
        core_energy_slope=measured["energy"],
        angular_reynolds_slope=measured["re_theta"],
        target_radial_length_slope=targets["radial"],
        target_axial_length_slope=targets["axial"],
        target_peak_velocity_slope=targets["velocity"],
        target_core_energy_slope=targets["energy"],
        target_angular_reynolds_slope=targets["re_theta"],
        max_absolute_slope_error=max_error,
    )


def cancellation_condition(terms: Iterable[float], *, epsilon: float = 1e-15) -> float:
    """Scalar cancellation-conditioning proxy: sum(|Fi|) / (|sum(Fi)| + epsilon)."""
    values = tuple(float(value) for value in terms)
    if not values:
        raise ValueError("at least one term is required")
    if epsilon <= 0.0:
        raise ValueError("epsilon must be positive")
    return sum(abs(value) for value in values) / (abs(sum(values)) + epsilon)


def verification_escalation(kappa_balance: float) -> VerificationEscalation:
    if kappa_balance < 0.0 or not math.isfinite(kappa_balance):
        raise ValueError("kappa_balance must be finite and non-negative")
    if kappa_balance >= 1000.0:
        return VerificationEscalation.REQUIRE_INDEPENDENT_SOLVER
    if kappa_balance >= 100.0:
        return VerificationEscalation.REFINE_TIMESTEP_AND_MESH
    if kappa_balance >= 10.0:
        return VerificationEscalation.REFINE_TIMESTEP
    return VerificationEscalation.NORMAL


def classify_control_outcome(
    baseline_stretching: float,
    controlled_stretching: float,
    *,
    neutral_fraction: float = 0.05,
    redirected: bool = False,
) -> ControlOutcome:
    if baseline_stretching <= 0.0:
        raise ValueError("baseline_stretching must be positive")
    if controlled_stretching < 0.0:
        raise ValueError("controlled_stretching must be non-negative")
    if not 0.0 <= neutral_fraction < 1.0:
        raise ValueError("neutral_fraction must be in [0, 1)")
    if redirected:
        return ControlOutcome.REDIRECTION
    relative_change = (controlled_stretching - baseline_stretching) / baseline_stretching
    if relative_change < -neutral_fraction:
        return ControlOutcome.SUPPRESSION
    if relative_change > neutral_fraction:
        return ControlOutcome.AMPLIFICATION
    return ControlOutcome.NEUTRAL


def run_nsb_benchmark(
    *,
    resolutions: tuple[int, ...] = (8, 16, 32),
    h_exponent: float = 0.005,
) -> NSBBenchmarkReport:
    if len(resolutions) < 3:
        raise ValueError("at least three resolutions are required")
    if tuple(sorted(set(resolutions))) != resolutions:
        raise ValueError("resolutions must be strictly increasing and unique")
    if any(value < 4 for value in resolutions):
        raise ValueError("all resolutions must be >= 4")

    diagnostics = tuple(_resolution_diagnostic(value) for value in resolutions)
    vorticity_orders = _observed_orders(diagnostics, "vorticity_l2_error")
    divergence_orders = _observed_orders(diagnostics, "known_divergence_l2_error")
    second_order_vorticity = all(1.8 <= value <= 2.2 for value in vorticity_orders)
    second_order_divergence = all(1.8 <= value <= 2.2 for value in divergence_orders)
    scaling = _scaling_diagnostic(h_exponent)
    scaling_pass = scaling.max_absolute_slope_error <= 1e-10

    report = NSBBenchmarkReport(
        resolutions=resolutions,
        diagnostics=diagnostics,
        scaling=scaling,
        summary=NSBSummary(
            vorticity_observed_orders=vorticity_orders,
            divergence_observed_orders=divergence_orders,
            second_order_vorticity_convergence_observed=second_order_vorticity,
            second_order_divergence_convergence_observed=second_order_divergence,
            scaling_instrumentation_passed=scaling_pass,
            g0_passed=second_order_vorticity and second_order_divergence,
            g1_passed=scaling_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_benchmark_report(report: NSBBenchmarkReport) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
