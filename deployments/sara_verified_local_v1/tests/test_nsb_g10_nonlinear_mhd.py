from __future__ import annotations

import pytest

from worldshepherd_sara.nsb_g10_nonlinear_mhd import (
    NSBG10Report,
    _aligned_initial,
    integrate_periodic_mhd,
    run_nsb_g10_benchmark,
    verify_nsb_g10_report,
)


@pytest.fixture(scope="module")
def report() -> NSBG10Report:
    return run_nsb_g10_benchmark()


def test_g10_acceptance_passes(report: NSBG10Report) -> None:
    assert report.acceptance.acceptance_pass
    assert report.nonlinear_2d_mhd_implemented
    assert report.induction_equation_evolved
    assert report.reciprocal_lorentz_backreaction_evolved


def test_aligned_alfvenic_case_has_nontrivial_cancelling_terms(report: NSBG10Report) -> None:
    case = report.exact_case
    assert case.nonlinear_advection_rms_initial > 1e-3
    assert case.lorentz_curl_rms_initial > 1e-3
    assert case.nonlinear_cancellation_rms_initial <= report.acceptance.cancellation_limit
    assert max(case.vorticity_l2_error, case.magnetic_potential_l2_error) <= report.acceptance.exact_l2_limit


def test_nonlinear_case_closes_instantaneous_energy_budget(report: NSBG10Report) -> None:
    case = report.nonlinear_case
    assert case.nonlinear_rhs_rms_initial >= report.acceptance.nonlinear_rhs_floor
    assert case.instantaneous_energy_budget_residual <= report.acceptance.energy_budget_limit
    assert case.total_energy_final < case.total_energy_initial
    assert case.viscous_dissipation_initial > 0.0
    assert case.resistive_dissipation_initial > 0.0


def test_divergence_and_means_are_controlled(report: NSBG10Report) -> None:
    assert report.exact_case.velocity_divergence_rms <= report.acceptance.divergence_limit
    assert report.exact_case.magnetic_divergence_rms <= report.acceptance.divergence_limit
    assert report.nonlinear_case.velocity_divergence_rms_final <= report.acceptance.divergence_limit
    assert report.nonlinear_case.magnetic_divergence_rms_final <= report.acceptance.divergence_limit
    assert report.nonlinear_case.mean_vorticity_drift <= 1e-12
    assert report.nonlinear_case.mean_magnetic_potential_drift <= 1e-12


def test_ideal_invariants_remain_bounded(report: NSBG10Report) -> None:
    ideal = report.ideal_invariant_case
    assert ideal.total_energy_relative_drift <= report.acceptance.ideal_invariant_drift_limit
    assert ideal.cross_helicity_relative_drift <= report.acceptance.ideal_invariant_drift_limit
    assert ideal.magnetic_potential_variance_relative_drift <= report.acceptance.ideal_invariant_drift_limit


def test_zero_magnetic_potential_remains_zero() -> None:
    omega, _ = _aligned_initial(16)
    zero = [[0.0] * 16 for _ in range(16)]
    _, a_final, _, _ = integrate_periodic_mhd(
        initial_vorticity=omega,
        initial_magnetic_potential=zero,
        viscosity=0.02,
        resistivity=0.02,
        dt=0.001,
        final_time=0.005,
    )
    assert max(abs(value) for row in a_final for value in row) <= 1e-14


def test_report_digest_detects_tampering(report: NSBG10Report) -> None:
    assert verify_nsb_g10_report(report)
    payload = report.model_dump(mode="json")
    payload["exact_case"]["vorticity_l2_error"] += 1e-3
    tampered = NSBG10Report.model_validate(payload)
    assert not verify_nsb_g10_report(tampered)


def test_claims_fail_closed(report: NSBG10Report) -> None:
    payload = report.model_dump(mode="json")
    payload["plasma_solved"] = True
    with pytest.raises(ValueError):
        NSBG10Report.model_validate(payload)
