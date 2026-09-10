from __future__ import annotations

import pytest

from worldshepherd_sara.nsb_g6_transient_hartmann import (
    NSBG6Report,
    integrate_transient_hartmann,
    run_nsb_g6_benchmark,
    transient_hartmann_exact_velocity,
    verify_nsb_g6_report,
)


@pytest.fixture(scope="module")
def report():
    return run_nsb_g6_benchmark()


def test_default_g6_gate_passes_and_digest_verifies(report):
    assert report.acceptance.acceptance_pass is True
    assert verify_nsb_g6_report(report) is True
    assert report.report_digest is not None
    assert report.report_digest.startswith("sha256:")


def test_spatial_and_temporal_convergence_are_second_order(report):
    assert min(report.convergence.spatial_orders) >= 1.8
    assert min(report.convergence.temporal_orders) >= 1.8
    assert report.convergence.spatial_errors[-1] <= 1e-5
    assert report.convergence.temporal_errors[-1] <= 5e-5


def test_energy_budget_closes_and_magnetic_sink_is_controlled(report):
    assert report.acceptance.energy_budget_pass is True
    assert report.cases[0].cumulative_em_dissipation == pytest.approx(0.0, abs=1e-14)
    assert all(case.cumulative_em_dissipation > 1e-14 for case in report.cases[1:])
    assert max(case.energy_budget_abs_residual for case in report.cases) <= 1e-10


def test_magnetic_damping_is_monotonic_in_reference_sweep(report):
    centerlines = [case.centerline_velocity for case in report.cases]
    means = [case.mean_velocity for case in report.cases]
    assert all(b < a for a, b in zip(centerlines, centerlines[1:]))
    assert all(b < a for a, b in zip(means, means[1:]))


def test_field_sign_symmetry_and_steady_limit_pass(report):
    assert report.acceptance.field_sign_symmetry_l2 <= 1e-14
    assert report.acceptance.steady_limit_l2 <= 1e-5


def test_exact_transient_respects_initial_and_wall_conditions():
    for ha in (0.0, 1.0, 5.0):
        assert transient_hartmann_exact_velocity(0.25, ha, 0.0) == 0.0
        assert transient_hartmann_exact_velocity(-1.0, ha, 0.2) == pytest.approx(0.0, abs=1e-14)
        assert transient_hartmann_exact_velocity(1.0, ha, 0.2) == pytest.approx(0.0, abs=1e-14)


def test_report_tampering_breaks_digest(report):
    tampered = report.model_copy(update={"benchmark_version": "tampered"})
    assert verify_nsb_g6_report(tampered) is False


def test_claim_promotion_fails_closed(report):
    payload = report.model_dump(mode="json")
    payload["plasma_solved"] = True
    with pytest.raises(ValueError):
        NSBG6Report.model_validate(payload)


def test_invalid_even_grid_is_rejected():
    with pytest.raises(ValueError):
        integrate_transient_hartmann(hartmann=2.0, grid_size=32, dt=0.01, final_time=0.1)
