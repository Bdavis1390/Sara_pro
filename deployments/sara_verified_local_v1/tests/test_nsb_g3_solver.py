from __future__ import annotations

import pytest

from worldshepherd_sara.nsb_g3_solver import (
    NSBG3Report,
    integrate_periodic_vorticity,
    reconstruct_periodic_velocity,
    run_nsb_g3_benchmark,
    verify_nsb_g3_report,
)
from worldshepherd_sara.qualification import CapabilityStatus


def test_default_g3_benchmark_passes_bounded_acceptance_gate():
    report = run_nsb_g3_benchmark()
    assert report.acceptance.acceptance_pass is True
    assert report.capability_status == CapabilityStatus.SIMULATED_ONLY
    assert report.mode_general_periodic_solver_implemented is True
    assert report.radix2_fft_poisson_solve_performed is True
    assert report.two_thirds_dealiasing_enabled is True


def test_manufactured_multimode_poisson_reconstruction_is_spectral_accuracy():
    report = run_nsb_g3_benchmark()
    result = report.poisson_result
    assert result.streamfunction_l2_error < 1e-10
    assert result.velocity_x_l2_error < 1e-10
    assert result.velocity_y_l2_error < 1e-10
    assert result.poisson_residual_rms < 1e-10
    assert result.divergence_rms < 1e-10


def test_taylor_green_temporal_convergence_is_second_order():
    report = run_nsb_g3_benchmark()
    assert min(report.acceptance.temporal_orders) >= 1.8
    errors = [case.vorticity_l2_error for case in report.taylor_green_cases]
    assert errors[2] < errors[1] < errors[0]
    assert errors[-1] < 1e-6


def test_general_periodic_reconstruction_is_not_taylor_green_specific():
    n = 16
    import math

    dx = 2.0 * math.pi / n
    vorticity = [
        [
            0.7 * math.cos(2.0 * i * dx + j * dx)
            + 0.3 * math.sin(i * dx - 3.0 * j * dx)
            for j in range(n)
        ]
        for i in range(n)
    ]
    u, v = reconstruct_periodic_velocity(vorticity)
    assert max(abs(value) for row in u for value in row) > 0.05
    assert max(abs(value) for row in v for value in row) > 0.05


def test_nonlinear_mixed_mode_case_has_real_advection_and_dissipation():
    result = run_nsb_g3_benchmark().nonlinear_result
    assert result.nonlinear_rhs_rms_initial > 0.01
    assert result.state_change_rms > 0.001
    assert result.mean_vorticity_drift < 1e-12
    assert result.divergence_rms_final < 1e-10
    assert result.poisson_residual_rms_final < 1e-10
    assert result.energy_nonincreasing is True
    assert result.enstrophy_nonincreasing is True


def test_report_is_deterministic_hash_bound_and_tamper_detectable():
    first = run_nsb_g3_benchmark()
    second = run_nsb_g3_benchmark()
    assert first == second
    assert first.report_digest is not None
    assert first.report_digest.startswith("sha256:")
    assert verify_nsb_g3_report(first) is True

    tampered = first.model_copy(update={"benchmark_version": "tampered"})
    assert verify_nsb_g3_report(tampered) is False


def test_fail_closed_model_rejects_unsupported_claim_promotion():
    report = run_nsb_g3_benchmark()
    payload = report.model_dump(mode="json")
    payload["navier_stokes_singularity_reproduced"] = True
    with pytest.raises(ValueError):
        NSBG3Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["general_purpose_cfd_solver_claimed"] = True
    with pytest.raises(ValueError):
        NSBG3Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["mhd_or_plasma_solved"] = True
    with pytest.raises(ValueError):
        NSBG3Report.model_validate(payload)


def test_non_radix2_grid_fails_closed():
    with pytest.raises(ValueError):
        run_nsb_g3_benchmark(grid_size=24)


def test_nonzero_mean_vorticity_fails_periodic_streamfunction_inversion():
    initial = [[1.0 for _ in range(16)] for _ in range(16)]
    with pytest.raises(ValueError):
        integrate_periodic_vorticity(
            initial_vorticity=initial,
            viscosity=0.01,
            dt=0.001,
            final_time=0.01,
        )


def test_unstable_timestep_fails_closed():
    n = 16
    import math

    dx = 2.0 * math.pi / n
    initial = [
        [2.0 * math.sin(i * dx) * math.sin(j * dx) for j in range(n)]
        for i in range(n)
    ]
    with pytest.raises(ValueError):
        integrate_periodic_vorticity(
            initial_vorticity=initial,
            viscosity=0.05,
            dt=1.0,
            final_time=1.0,
        )
