from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


TWO_PI = 2.0 * math.pi
ModeSpec = tuple[str, float, int, int, float]


class G8ResolutionResult(BaseModel):
    grid_size: int = Field(ge=16)
    target_rms: float = Field(ge=0.0)
    fd_rms: float = Field(ge=0.0)
    l2_error: float = Field(ge=0.0)
    relative_l2_error: float = Field(ge=0.0)
    max_abs_error: float = Field(ge=0.0)
    joule_dissipation_rate: float = Field(ge=0.0)
    lorentz_work_dissipation_rate: float = Field(ge=0.0)
    work_identity_abs_error: float = Field(ge=0.0)


class G8OrientationResult(BaseModel):
    case_id: str
    grid_size: int = Field(ge=16)
    kx: int
    ky: int
    field_angle_rad: float
    orientation_fraction: float = Field(ge=0.0, le=1.0)
    target_rms: float = Field(ge=0.0)
    fd_rms: float = Field(ge=0.0)
    l2_error: float = Field(ge=0.0)
    joule_dissipation_rate: float = Field(ge=0.0)
    lorentz_work_dissipation_rate: float = Field(ge=0.0)
    work_identity_abs_error: float = Field(ge=0.0)


class G8AcceptanceSummary(BaseModel):
    spatial_order_floor: float = Field(gt=0.0)
    spatial_orders: tuple[float, float]
    finest_l2_limit: float = Field(gt=0.0)
    finest_relative_l2_limit: float = Field(gt=0.0)
    orientation_l2_limit: float = Field(gt=0.0)
    null_sink_limit: float = Field(gt=0.0)
    field_sign_l2_limit: float = Field(gt=0.0)
    work_identity_limit: float = Field(gt=0.0)
    spatial_convergence_pass: bool
    orientation_replication_pass: bool
    field_perpendicular_null_pass: bool
    field_parallel_max_pass: bool
    field_sign_symmetry_pass: bool
    zero_magnetic_limit_pass: bool
    joule_work_identity_pass: bool
    acceptance_pass: bool


class NSBG8Report(BaseModel):
    qualification_id: str = "WS-NSB-2026-G8-001"
    benchmark_version: str = "1.3"
    formulation: str = "independent finite-difference Ohm-Lorentz replication of the G7 low-Rm imposed-field magnetic operator"
    physical_scope: str = "strictly 2D periodic, z-invariant, homogeneous low-Rm imposed-field reference"
    normalized_ohm_law: str = "j_z = u*B_y - v*B_x"
    normalized_lorentz_force: str = "f = Lambda*j_z*(-B_y, B_x)"
    vorticity_operator: str = "curl(f)_z = Lambda*(B_x*d_x(j_z) + B_y*d_y(j_z))"
    joule_identity: str = "D_J = Lambda*<j_z^2> = -<u dot f>"
    spatial_scheme: str = "second-order centered finite differences on a periodic grid"
    reference_target: str = "analytical Fourier-mode decay operator -Lambda*(k_parallel^2/|k|^2)*omega"
    resolution_results: tuple[G8ResolutionResult, ...]
    orientation_results: tuple[G8OrientationResult, ...]
    field_sign_symmetry_l2: float = Field(ge=0.0)
    zero_magnetic_operator_l2: float = Field(ge=0.0)
    zero_magnetic_dissipation: float = Field(ge=0.0)
    acceptance: G8AcceptanceSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    independent_fd_ohm_lorentz_replication_implemented: bool = True
    analytical_reference_target_used: bool = True
    spectral_magnetic_operator_called: bool = False
    current_potential_poisson_solved: bool = False
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
        "G8 is an internal numerically distinct replication of the bounded G7 low-Rm imposed-field magnetic operator.",
        "The finite-difference path does not call the G7 spectral magnetic operator; the comparison target is derived analytically mode by mode.",
        "In this strict 2D in-plane-field reference, induced current is purely z-directed and charge conservation is automatic under z invariance; no electric-potential Poisson solve is claimed.",
        "Passing G8 does not establish finite-Rm induction physics, general MHD, Hall-MHD, two-fluid, kinetic, plasma, adaptive electromagnetic control, laboratory, propulsion, shielding, stealth, cloaking, or operational capability.",
        "Passing G8 does not reproduce, validate, or refute any finite-time Navier-Stokes singularity construction.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "NSBG8Report":
        if self.capability_status != CapabilityStatus.SIMULATED_ONLY:
            raise ValueError("WS-NSB v1.3 must remain SIMULATED_ONLY")
        if not self.independent_fd_ohm_lorentz_replication_implemented or not self.analytical_reference_target_used:
            raise ValueError("G8 must represent the complete independent finite-difference replication gate")
        if self.spectral_magnetic_operator_called:
            raise ValueError("G8 independence is invalid if the G7 spectral magnetic operator is called")
        prohibited = (
            self.current_potential_poisson_solved,
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
            raise ValueError("WS-NSB v1.3 cannot promote unsupported MHD, plasma, physical, singularity, or operational claims")
        return self


def _validate_grid(grid_size: int) -> None:
    if grid_size < 16 or grid_size % 2:
        raise ValueError("G8 requires an even periodic grid_size >= 16")


def _field_mean(field: list[list[float]]) -> float:
    n = len(field)
    return sum(value for row in field for value in row) / (n * n)


def _field_rms(field: list[list[float]]) -> float:
    return math.sqrt(_field_mean([[value * value for value in row] for row in field]))


def _l2_difference(left: list[list[float]], right: list[list[float]]) -> float:
    n = len(left)
    if n != len(right) or any(len(row) != n for row in left) or any(len(row) != n for row in right):
        raise ValueError("G8 fields must be square and have matching shapes")
    return math.sqrt(
        sum((left[i][j] - right[i][j]) ** 2 for i in range(n) for j in range(n)) / (n * n)
    )


def _max_abs_difference(left: list[list[float]], right: list[list[float]]) -> float:
    n = len(left)
    return max(abs(left[i][j] - right[i][j]) for i in range(n) for j in range(n))


def _centered_dx(field: list[list[float]], spacing: float) -> list[list[float]]:
    n = len(field)
    return [
        [
            (field[(i + 1) % n][j] - field[(i - 1) % n][j]) / (2.0 * spacing)
            for j in range(n)
        ]
        for i in range(n)
    ]


def _centered_dy(field: list[list[float]], spacing: float) -> list[list[float]]:
    n = len(field)
    return [
        [
            (field[i][(j + 1) % n] - field[i][(j - 1) % n]) / (2.0 * spacing)
            for j in range(n)
        ]
        for i in range(n)
    ]


def _validate_modes(grid_size: int, modes: tuple[ModeSpec, ...]) -> None:
    _validate_grid(grid_size)
    if not modes:
        raise ValueError("G8 requires at least one analytical mode")
    for kind, amplitude, kx, ky, _phase in modes:
        if kind not in {"sin", "cos"}:
            raise ValueError("mode kind must be sin or cos")
        if amplitude == 0.0:
            raise ValueError("mode amplitude must be nonzero")
        if kx == 0 and ky == 0:
            raise ValueError("zero wavenumber mode is not allowed")
        if 4 * max(abs(kx), abs(ky)) >= grid_size:
            raise ValueError("analytical modes must remain comfortably resolved on the G8 grid")


def _analytic_velocity_and_vorticity(
    grid_size: int,
    modes: tuple[ModeSpec, ...],
) -> tuple[list[list[float]], list[list[float]], list[list[float]]]:
    _validate_modes(grid_size, modes)
    spacing = TWO_PI / grid_size
    u = [[0.0] * grid_size for _ in range(grid_size)]
    v = [[0.0] * grid_size for _ in range(grid_size)]
    omega = [[0.0] * grid_size for _ in range(grid_size)]

    for i in range(grid_size):
        x = i * spacing
        for j in range(grid_size):
            y = j * spacing
            for kind, amplitude, kx, ky, phase in modes:
                argument = kx * x + ky * y + phase
                if kind == "sin":
                    streamfunction = amplitude * math.sin(argument)
                    directional_derivative = amplitude * math.cos(argument)
                else:
                    streamfunction = amplitude * math.cos(argument)
                    directional_derivative = -amplitude * math.sin(argument)
                u[i][j] += ky * directional_derivative
                v[i][j] -= kx * directional_derivative
                omega[i][j] += (kx * kx + ky * ky) * streamfunction
    return u, v, omega


def _orientation_fraction(kx: int, ky: int, field_angle_rad: float) -> float:
    k2 = kx * kx + ky * ky
    if k2 <= 0:
        raise ValueError("orientation reference requires nonzero wavevector")
    bx = math.cos(field_angle_rad)
    by = math.sin(field_angle_rad)
    k_parallel = bx * kx + by * ky
    fraction = (k_parallel * k_parallel) / k2
    return min(1.0, max(0.0, fraction))


def _analytical_magnetic_target(
    grid_size: int,
    modes: tuple[ModeSpec, ...],
    *,
    field_angle_rad: float,
    magnetic_damping: float,
) -> list[list[float]]:
    _validate_modes(grid_size, modes)
    if magnetic_damping < 0.0:
        raise ValueError("magnetic_damping must be nonnegative")
    spacing = TWO_PI / grid_size
    bx = math.cos(field_angle_rad)
    by = math.sin(field_angle_rad)
    target = [[0.0] * grid_size for _ in range(grid_size)]

    for i in range(grid_size):
        x = i * spacing
        for j in range(grid_size):
            y = j * spacing
            for kind, amplitude, kx, ky, phase in modes:
                argument = kx * x + ky * y + phase
                streamfunction = amplitude * (
                    math.sin(argument) if kind == "sin" else math.cos(argument)
                )
                k2 = kx * kx + ky * ky
                omega_mode = k2 * streamfunction
                k_parallel = bx * kx + by * ky
                target[i][j] -= magnetic_damping * (k_parallel * k_parallel / k2) * omega_mode
    return target


def finite_difference_ohm_lorentz_operator(
    *,
    u: list[list[float]],
    v: list[list[float]],
    field_angle_rad: float,
    magnetic_damping: float,
) -> tuple[list[list[float]], float, float]:
    if magnetic_damping < 0.0:
        raise ValueError("magnetic_damping must be nonnegative")
    n = len(u)
    _validate_grid(n)
    if len(v) != n or any(len(row) != n for row in u) or any(len(row) != n for row in v):
        raise ValueError("u and v must be matching square fields")

    spacing = TWO_PI / n
    bx = math.cos(field_angle_rad)
    by = math.sin(field_angle_rad)
    current_z = [
        [by * u[i][j] - bx * v[i][j] for j in range(n)]
        for i in range(n)
    ]
    force_x = [
        [-magnetic_damping * by * current_z[i][j] for j in range(n)]
        for i in range(n)
    ]
    force_y = [
        [magnetic_damping * bx * current_z[i][j] for j in range(n)]
        for i in range(n)
    ]

    d_force_y_dx = _centered_dx(force_y, spacing)
    d_force_x_dy = _centered_dy(force_x, spacing)
    vorticity_tendency = [
        [d_force_y_dx[i][j] - d_force_x_dy[i][j] for j in range(n)]
        for i in range(n)
    ]

    joule_dissipation = magnetic_damping * _field_mean(
        [[current_z[i][j] ** 2 for j in range(n)] for i in range(n)]
    )
    lorentz_work_dissipation = -_field_mean(
        [
            [u[i][j] * force_x[i][j] + v[i][j] * force_y[i][j] for j in range(n)]
            for i in range(n)
        ]
    )
    return vorticity_tendency, joule_dissipation, lorentz_work_dissipation


def _resolution_case(
    *,
    grid_size: int,
    modes: tuple[ModeSpec, ...],
    field_angle_rad: float,
    magnetic_damping: float,
) -> G8ResolutionResult:
    u, v, _omega = _analytic_velocity_and_vorticity(grid_size, modes)
    target = _analytical_magnetic_target(
        grid_size,
        modes,
        field_angle_rad=field_angle_rad,
        magnetic_damping=magnetic_damping,
    )
    fd, joule, work = finite_difference_ohm_lorentz_operator(
        u=u,
        v=v,
        field_angle_rad=field_angle_rad,
        magnetic_damping=magnetic_damping,
    )
    target_rms = _field_rms(target)
    error = _l2_difference(fd, target)
    return G8ResolutionResult(
        grid_size=grid_size,
        target_rms=target_rms,
        fd_rms=_field_rms(fd),
        l2_error=error,
        relative_l2_error=error / max(target_rms, 1e-15),
        max_abs_error=_max_abs_difference(fd, target),
        joule_dissipation_rate=joule,
        lorentz_work_dissipation_rate=work,
        work_identity_abs_error=abs(joule - work),
    )


def _orientation_case(
    *,
    case_id: str,
    grid_size: int,
    kx: int,
    ky: int,
    field_angle_rad: float,
    magnetic_damping: float,
) -> G8OrientationResult:
    modes: tuple[ModeSpec, ...] = (("sin", 1.0, kx, ky, 0.2),)
    u, v, _omega = _analytic_velocity_and_vorticity(grid_size, modes)
    target = _analytical_magnetic_target(
        grid_size,
        modes,
        field_angle_rad=field_angle_rad,
        magnetic_damping=magnetic_damping,
    )
    fd, joule, work = finite_difference_ohm_lorentz_operator(
        u=u,
        v=v,
        field_angle_rad=field_angle_rad,
        magnetic_damping=magnetic_damping,
    )
    return G8OrientationResult(
        case_id=case_id,
        grid_size=grid_size,
        kx=kx,
        ky=ky,
        field_angle_rad=field_angle_rad,
        orientation_fraction=_orientation_fraction(kx, ky, field_angle_rad),
        target_rms=_field_rms(target),
        fd_rms=_field_rms(fd),
        l2_error=_l2_difference(fd, target),
        joule_dissipation_rate=joule,
        lorentz_work_dissipation_rate=work,
        work_identity_abs_error=abs(joule - work),
    )


def _observed_order(coarse_error: float, fine_error: float) -> float:
    if coarse_error <= 0.0 or fine_error <= 0.0:
        raise ValueError("G8 convergence errors must be positive")
    return math.log(coarse_error / fine_error) / math.log(2.0)


def run_nsb_g8_benchmark(
    *,
    resolution_grids: tuple[int, int, int] = (32, 64, 128),
    field_angle_rad: float = 0.37,
    magnetic_damping: float = 0.7,
    spatial_order_floor: float = 1.9,
    finest_l2_limit: float = 5e-3,
    finest_relative_l2_limit: float = 3e-3,
    orientation_l2_limit: float = 5e-3,
    null_sink_limit: float = 1e-12,
    field_sign_l2_limit: float = 1e-12,
    work_identity_limit: float = 1e-12,
) -> NSBG8Report:
    if magnetic_damping <= 0.0:
        raise ValueError("default G8 benchmark requires positive magnetic_damping")
    if not (
        resolution_grids[1] == 2 * resolution_grids[0]
        and resolution_grids[2] == 2 * resolution_grids[1]
    ):
        raise ValueError("G8 resolution_grids must use exact factor-two refinement")
    for grid_size in resolution_grids:
        _validate_grid(grid_size)

    mixed_modes: tuple[ModeSpec, ...] = (
        ("sin", 1.0, 2, 1, 0.2),
        ("cos", 0.35, 1, 3, -0.4),
        ("sin", 0.25, 3, -2, 0.1),
    )
    resolution_results = tuple(
        _resolution_case(
            grid_size=grid_size,
            modes=mixed_modes,
            field_angle_rad=field_angle_rad,
            magnetic_damping=magnetic_damping,
        )
        for grid_size in resolution_grids
    )
    spatial_orders = (
        _observed_order(resolution_results[0].l2_error, resolution_results[1].l2_error),
        _observed_order(resolution_results[1].l2_error, resolution_results[2].l2_error),
    )

    kx, ky = 2, 1
    field_parallel = math.atan2(ky, kx)
    field_perpendicular = field_parallel + 0.5 * math.pi
    orientation_results = (
        _orientation_case(
            case_id="field_parallel_to_k_max_damping",
            grid_size=resolution_grids[-1],
            kx=kx,
            ky=ky,
            field_angle_rad=field_parallel,
            magnetic_damping=magnetic_damping,
        ),
        _orientation_case(
            case_id="field_perpendicular_to_k_null",
            grid_size=resolution_grids[-1],
            kx=kx,
            ky=ky,
            field_angle_rad=field_perpendicular,
            magnetic_damping=magnetic_damping,
        ),
        _orientation_case(
            case_id="field_x_axis_oblique_k",
            grid_size=resolution_grids[-1],
            kx=kx,
            ky=ky,
            field_angle_rad=0.0,
            magnetic_damping=magnetic_damping,
        ),
        _orientation_case(
            case_id="field_arbitrary_oblique",
            grid_size=resolution_grids[-1],
            kx=kx,
            ky=ky,
            field_angle_rad=field_angle_rad,
            magnetic_damping=magnetic_damping,
        ),
    )

    symmetry_grid = resolution_grids[1]
    u_sym, v_sym, _ = _analytic_velocity_and_vorticity(symmetry_grid, mixed_modes)
    positive_field, _, _ = finite_difference_ohm_lorentz_operator(
        u=u_sym,
        v=v_sym,
        field_angle_rad=field_angle_rad,
        magnetic_damping=magnetic_damping,
    )
    reversed_field, _, _ = finite_difference_ohm_lorentz_operator(
        u=u_sym,
        v=v_sym,
        field_angle_rad=field_angle_rad + math.pi,
        magnetic_damping=magnetic_damping,
    )
    field_sign_symmetry_l2 = _l2_difference(positive_field, reversed_field)

    zero_magnetic, zero_joule, zero_work = finite_difference_ohm_lorentz_operator(
        u=u_sym,
        v=v_sym,
        field_angle_rad=field_angle_rad,
        magnetic_damping=0.0,
    )
    zero_field = [[0.0] * symmetry_grid for _ in range(symmetry_grid)]
    zero_magnetic_operator_l2 = _l2_difference(zero_magnetic, zero_field)
    zero_magnetic_dissipation = max(zero_joule, zero_work)

    max_orientation_error = max(case.l2_error for case in orientation_results)
    max_work_error = max(
        [
            *(case.work_identity_abs_error for case in resolution_results),
            *(case.work_identity_abs_error for case in orientation_results),
            abs(zero_joule - zero_work),
        ]
    )

    spatial_pass = (
        min(spatial_orders) >= spatial_order_floor
        and resolution_results[-1].l2_error <= finest_l2_limit
        and resolution_results[-1].relative_l2_error <= finest_relative_l2_limit
    )
    orientation_pass = max_orientation_error <= orientation_l2_limit
    parallel_case = orientation_results[0]
    perpendicular_case = orientation_results[1]
    perpendicular_pass = (
        perpendicular_case.orientation_fraction <= 1e-15
        and perpendicular_case.joule_dissipation_rate <= null_sink_limit
        and perpendicular_case.fd_rms <= null_sink_limit
    )
    parallel_pass = (
        abs(parallel_case.orientation_fraction - 1.0) <= 1e-15
        and parallel_case.joule_dissipation_rate > 0.0
        and parallel_case.fd_rms > 0.0
    )
    sign_pass = field_sign_symmetry_l2 <= field_sign_l2_limit
    zero_pass = (
        zero_magnetic_operator_l2 <= null_sink_limit
        and zero_magnetic_dissipation <= null_sink_limit
    )
    work_pass = max_work_error <= work_identity_limit
    acceptance_pass = all(
        (
            spatial_pass,
            orientation_pass,
            perpendicular_pass,
            parallel_pass,
            sign_pass,
            zero_pass,
            work_pass,
        )
    )

    report = NSBG8Report(
        resolution_results=resolution_results,
        orientation_results=orientation_results,
        field_sign_symmetry_l2=field_sign_symmetry_l2,
        zero_magnetic_operator_l2=zero_magnetic_operator_l2,
        zero_magnetic_dissipation=zero_magnetic_dissipation,
        acceptance=G8AcceptanceSummary(
            spatial_order_floor=spatial_order_floor,
            spatial_orders=spatial_orders,
            finest_l2_limit=finest_l2_limit,
            finest_relative_l2_limit=finest_relative_l2_limit,
            orientation_l2_limit=orientation_l2_limit,
            null_sink_limit=null_sink_limit,
            field_sign_l2_limit=field_sign_l2_limit,
            work_identity_limit=work_identity_limit,
            spatial_convergence_pass=spatial_pass,
            orientation_replication_pass=orientation_pass,
            field_perpendicular_null_pass=perpendicular_pass,
            field_parallel_max_pass=parallel_pass,
            field_sign_symmetry_pass=sign_pass,
            zero_magnetic_limit_pass=zero_pass,
            joule_work_identity_pass=work_pass,
            acceptance_pass=acceptance_pass,
        ),
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_nsb_g8_report(report: NSBG8Report) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected
