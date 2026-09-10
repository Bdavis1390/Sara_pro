from __future__ import annotations

import pytest

from worldshepherd_sara.nsb_g7_qs_anisotropic import (
    NSBG7Report,
    _magnetic_dissipation_rate,
    _single_mode_initial,
    integrate_qs_periodic_vorticity,
    run_nsb_g7_benchmark,
    verify_nsb_g7_report,
)


@pytest.fixture(scope="module")
def report():
    return run_nsb_g7_benchmark()


def test_default_g7_gate_passes_and_digest_verifies(report):
    assert report.acceptance.acceptance_pass is True
    assert verify_nsb_g7_report(report) is True
    assert report.report_digest is not None
    assert report.report_digest.startswith("sha256:")


def test_single_mode_temporal_convergence_is_second_order(report):
    assert min(report.acceptance.temporal_orders) >= 1.8
    assert report.temporal_cases[-1].vorticity_l2_error <= report.acceptance.finest_mode_l2_limit


def test_orientation_dependent_decay_matches_reference(report):
    assert report.acceptance.orientation_decay_pass is True
    assert report.acceptance.max_orientation_rate_error <= report.acceptance.max_orientation_rate_error_limit
    fractions = [case.orientation_fraction for case in report.mode_cases]
    assert fractions[0] == 0.0
    assert fractions[-1] == 1.0
    assert report.mode_cases[3].exact_magnetic_decay_rate > report.mode_cases[1].exact_magnetic_decay_rate


def test_parallel_mode_has_null_joule_sink_and_transverse_mode_is_maximal(report):
    parallel = report.mode_cases[0]
    transverse = report.mode_cases[-1]
    assert parallel.magnetic_dissipation_rate_initial <= report.acceptance.parallel_mode_sink_limit
    assert abs(parallel.measured_magnetic_decay_rate) <= report.acceptance.max_orientation_rate_error_limit
    assert transverse.magnetic_dissipation_rate_initial > 0.0
    assert transverse.exact_magnetic_decay_rate == pytest.approx(transverse.magnetic_damping)


def test_zero_magnetic_limit_and_nonlinear_sink_pass(report):
    assert report.acceptance.zero_magnetic_limit_pass is True
    assert report.acceptance.nonlinear_magnetic_sink_pass is True
    assert report.nonlinear_result.magnetic_energy_final < report.nonlinear_result.zero_field_energy_final
    assert report.nonlinear_result.magnetic_dissipation_rate_initial > 0.0


def test_geometry_and_mean_vorticity_controls_pass(report):
    assert report.acceptance.conservation_geometry_pass is True
    assert report.nonlinear_result.divergence_rms_final <= report.acceptance.divergence_limit
    assert report.nonlinear_result.poisson_residual_rms_final <= report.acceptance.poisson_residual_limit
    assert report.nonlinear_result.mean_vorticity_drift <= 1e-12


def test_magnetic_dissipation_is_nonnegative_and_orientation_sensitive():
    parallel = _single_mode_initial(16, k_parallel=0, k_transverse=2)
    transverse = _single_mode_initial(16, k_parallel=2, k_transverse=0)
    assert _magnetic_dissipation_rate(parallel, 1.0) == pytest.approx(0.0, abs=1e-14)
    assert _magnetic_dissipation_rate(transverse, 1.0) > 0.0


def test_report_tampering_breaks_digest(report):
    tampered = report.model_copy(update={"benchmark_version": "tampered"})
    assert verify_nsb_g7_report(tampered) is False


def test_claim_promotion_fails_closed(report):
    payload = report.model_dump(mode="json")
    payload["plasma_solved"] = True
    with pytest.raises(ValueError):
        NSBG7Report.model_validate(payload)


def test_negative_magnetic_damping_is_rejected():
    initial = _single_mode_initial(16, k_parallel=1, k_transverse=1)
    with pytest.raises(ValueError):
        integrate_qs_periodic_vorticity(
            initial_vorticity=initial,
            viscosity=0.03,
            magnetic_damping=-0.1,
            dt=0.01,
            final_time=0.1,
        )
