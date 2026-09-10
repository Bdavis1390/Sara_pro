from __future__ import annotations

import math

import pytest

from worldshepherd_sara.nsb_g4_solver import (
    NSBG4Report,
    integrate_periodic_vorticity_fd,
    reconstruct_periodic_velocity_fd,
    run_nsb_g4_benchmark,
    solve_periodic_poisson_fd,
    verify_nsb_g4_report,
)
from worldshepherd_sara.qualification import CapabilityStatus


def test_default_g4_benchmark_passes_cross_solver_gate():
    report = run_nsb_g4_benchmark()
    assert report.acceptance.acceptance_pass is True
    assert report.capability_status == CapabilityStatus.SIMULATED_ONLY
    assert report.numerically_distinct_second_formulation_implemented is True
    assert report.cross_solver_comparison_performed is True
    assert report.external_independent_replication_claimed is False


def test_manufactured_finite_difference_poisson_converges_second_order():
    report = run_nsb_g4_benchmark()
    assert min(report.acceptance.streamfunction_orders) >= 1.8
    assert min(report.acceptance.velocity_x_orders) >= 1.8
    assert min(report.acceptance.velocity_y_orders) >= 1.8
    errors = [case.streamfunction_l2_error for case in report.manufactured_cases]
    assert errors[2] < errors[1] < errors[0]


def test_periodic_poisson_residual_and_divergence_are_bounded():
    report = run_nsb_g4_benchmark()
    for case in report.manufactured_cases:
        assert case.poisson_residual_rms <= report.acceptance.poisson_residual_limit
        assert case.divergence_rms <= report.acceptance.divergence_limit
        assert case.poisson_iterations > 0


def test_nonlinear_cross_solver_agreement_is_within_declared_bound():
    report = run_nsb_g4_benchmark()
    cross = report.cross_solver
    assert cross.fd_vs_spectral_relative_rms <= report.acceptance.cross_solver_relative_limit
    assert cross.fd_state_change_rms >= report.acceptance.state_change_floor
    assert cross.mean_vorticity_drift <= report.acceptance.mean_vorticity_drift_limit
    assert cross.energy_nonincreasing is True
    assert cross.enstrophy_nonincreasing is True


def test_fd_velocity_reconstruction_supports_non_taylor_green_modes():
    n = 16
    dx = 2.0 * math.pi / n
    omega = [
        [
            0.5 * math.cos(2.0 * i * dx + j * dx)
            + 0.25 * math.sin(i * dx - 2.0 * j * dx)
            for j in range(n)
        ]
        for i in range(n)
    ]
    u, v = reconstruct_periodic_velocity_fd(omega)
    assert max(abs(value) for row in u for value in row) > 0.01
    assert max(abs(value) for row in v for value in row) > 0.01


def test_report_is_deterministic_hash_bound_and_tamper_detectable():
    first = run_nsb_g4_benchmark()
    second = run_nsb_g4_benchmark()
    assert first == second
    assert first.report_digest is not None
    assert first.report_digest.startswith("sha256:")
    assert verify_nsb_g4_report(first) is True
    tampered = first.model_copy(update={"benchmark_version": "tampered"})
    assert verify_nsb_g4_report(tampered) is False


def test_fail_closed_model_rejects_external_or_physical_promotion():
    report = run_nsb_g4_benchmark()
    payload = report.model_dump(mode="json")
    payload["external_independent_replication_claimed"] = True
    with pytest.raises(ValueError):
        NSBG4Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["navier_stokes_singularity_reproduced"] = True
    with pytest.raises(ValueError):
        NSBG4Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["mhd_or_plasma_solved"] = True
    with pytest.raises(ValueError):
        NSBG4Report.model_validate(payload)


def test_nonzero_mean_vorticity_fails_periodic_poisson_solve():
    omega = [[1.0 for _ in range(16)] for _ in range(16)]
    with pytest.raises(ValueError):
        solve_periodic_poisson_fd(omega)


def test_unstable_fd_timestep_fails_closed():
    n = 16
    dx = 2.0 * math.pi / n
    omega = [
        [2.0 * math.sin(i * dx) * math.sin(j * dx) for j in range(n)]
        for i in range(n)
    ]
    with pytest.raises(ValueError):
        integrate_periodic_vorticity_fd(
            initial_vorticity=omega,
            viscosity=0.05,
            dt=1.0,
            final_time=1.0,
        )
