from __future__ import annotations

import pytest

from worldshepherd_sara.nsb_g5_hartmann import (
    NSBG5Report,
    hartmann_exact_mean_velocity,
    hartmann_exact_velocity,
    run_nsb_g5_benchmark,
    solve_hartmann_fd,
    verify_nsb_g5_report,
)
from worldshepherd_sara.qualification import CapabilityStatus


def test_default_g5_benchmark_passes_quasi_static_reference_gate():
    report = run_nsb_g5_benchmark()
    assert report.acceptance.acceptance_pass is True
    assert report.capability_status == CapabilityStatus.SIMULATED_ONLY
    assert report.quasi_static_hartmann_reference_solved is True
    assert report.full_mhd_solver_claimed is False
    assert report.induction_equation_solved is False
    assert report.plasma_solved is False


def test_hydrodynamic_zero_field_limit_is_poiseuille():
    report = run_nsb_g5_benchmark()
    zero = report.cases[0]
    assert zero.hartmann == 0.0
    assert zero.l2_velocity_error < 1e-12
    assert zero.centerline_velocity == pytest.approx(0.5, abs=1e-12)
    assert hartmann_exact_mean_velocity(0.0) == pytest.approx(1.0 / 3.0)
    assert hartmann_exact_velocity(0.0, 0.0) == pytest.approx(0.5)


def test_hartmann_spatial_convergence_is_second_order():
    report = run_nsb_g5_benchmark()
    assert min(report.convergence.observed_orders) >= 1.8
    errors = report.convergence.l2_errors
    assert errors[2] < errors[1] < errors[0]
    assert errors[-1] <= report.convergence.finest_l2_limit


def test_magnetic_damping_is_monotonic_for_fixed_pressure_gradient():
    report = run_nsb_g5_benchmark()
    centerlines = [case.centerline_velocity for case in report.cases]
    means = [case.mean_velocity for case in report.cases]
    assert all(centerlines[index + 1] < centerlines[index] for index in range(len(centerlines) - 1))
    assert all(means[index + 1] < means[index] for index in range(len(means) - 1))
    assert report.acceptance.monotonic_magnetic_damping_pass is True


def test_field_sign_symmetry_matches_quasi_static_b_squared_reference():
    y_positive, positive = solve_hartmann_fd(hartmann=2.0, grid_size=65)
    y_negative, negative = solve_hartmann_fd(hartmann=-2.0, grid_size=65)
    assert y_positive == y_negative
    assert positive == pytest.approx(negative, abs=1e-15)
    assert run_nsb_g5_benchmark().acceptance.field_sign_symmetry_pass is True


def test_flow_rate_matches_analytic_reference_over_sweep():
    report = run_nsb_g5_benchmark()
    assert report.acceptance.flow_rate_accuracy_pass is True
    assert max(case.mean_velocity_relative_error for case in report.cases) <= 5e-4


def test_report_is_deterministic_hash_bound_and_tamper_detectable():
    first = run_nsb_g5_benchmark()
    second = run_nsb_g5_benchmark()
    assert first == second
    assert first.report_digest is not None
    assert first.report_digest.startswith("sha256:")
    assert verify_nsb_g5_report(first) is True

    tampered = first.model_copy(update={"benchmark_version": "tampered"})
    assert verify_nsb_g5_report(tampered) is False


def test_fail_closed_model_rejects_mhd_plasma_or_physical_promotion():
    report = run_nsb_g5_benchmark()
    payload = report.model_dump(mode="json")
    payload["full_mhd_solver_claimed"] = True
    with pytest.raises(ValueError):
        NSBG5Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["plasma_solved"] = True
    with pytest.raises(ValueError):
        NSBG5Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["adaptive_em_control_validated"] = True
    with pytest.raises(ValueError):
        NSBG5Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["laboratory_validation_performed"] = True
    with pytest.raises(ValueError):
        NSBG5Report.model_validate(payload)


def test_even_or_too_small_grids_fail_closed():
    with pytest.raises(ValueError):
        solve_hartmann_fd(hartmann=1.0, grid_size=32)
    with pytest.raises(ValueError):
        solve_hartmann_fd(hartmann=1.0, grid_size=3)


def test_unsorted_or_negative_hartmann_sweep_fails_closed():
    with pytest.raises(ValueError):
        run_nsb_g5_benchmark(sweep_hartmann=(0.0, 2.0, 1.0))
    with pytest.raises(ValueError):
        run_nsb_g5_benchmark(sweep_hartmann=(-1.0, 0.0, 1.0))
