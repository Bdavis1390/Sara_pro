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
    assert report.benchmark_version == "1.5.2"
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


def _max_conditioned_ideal_drift(case) -> float:
    return max(
        case.total_energy_relative_drift,
        case.cross_helicity_normalized_drift,
        case.magnetic_potential_variance_relative_drift,
    )


def test_ideal_invariants_remain_bounded(report: NSBG10Report) -> None:
    ideal = report.ideal_invariant_case
    assert ideal.dt == pytest.approx(0.000125)
    assert ideal.steps == 80
    assert ideal.total_energy_relative_drift <= report.acceptance.ideal_invariant_drift_limit
    assert ideal.cross_helicity_normalized_drift <= report.acceptance.ideal_invariant_drift_limit
    assert ideal.magnetic_potential_variance_relative_drift <= report.acceptance.ideal_invariant_drift_limit


def test_cross_helicity_metric_remains_well_conditioned_near_zero(report: NSBG10Report) -> None:
    coarse = report.ideal_temporal_refinement[0]
    limit = report.acceptance.ideal_invariant_drift_limit

    # #245 historical negative evidence is retained in the issue and benchmark
    # documentation. Do not require a particular roundoff-sized legacy drift
    # to reproduce across Python/CPU/runner combinations. Instead prove the
    # denominator pathology directly: the initial invariant is effectively
    # zero while the physical Cauchy-Schwarz scale is many orders larger.
    assert abs(coarse.cross_helicity_initial) <= 1e-12
    legacy_scale = max(abs(coarse.cross_helicity_initial), 1e-12)
    assert coarse.cross_helicity_scale / legacy_scale >= 1e8
    assert coarse.cross_helicity_relative_drift == pytest.approx(
        coarse.cross_helicity_absolute_drift / legacy_scale
    )
    assert coarse.cross_helicity_absolute_drift <= 1e-14

    # Acceptance uses the Cauchy-Schwarz energy scale for cross helicity,
    # preserving the same 2e-5 limit without hiding the legacy diagnostic.
    assert coarse.cross_helicity_scale > 1e-3
    assert coarse.cross_helicity_normalized_drift <= limit
    assert "2*sqrt" in report.acceptance.cross_helicity_acceptance_metric


def test_ideal_invariant_temporal_refinement_is_recorded(report: NSBG10Report) -> None:
    coarse, refined, fine = report.ideal_temporal_refinement
    assert (coarse.dt, refined.dt, fine.dt) == pytest.approx((0.00025, 0.000125, 0.0000625))
    assert (coarse.steps, refined.steps, fine.steps) == (40, 80, 160)
    assert coarse.final_time == refined.final_time == fine.final_time == pytest.approx(0.01)

    limit = report.acceptance.ideal_invariant_drift_limit
    for case in (coarse, refined, fine):
        assert _max_conditioned_ideal_drift(case) <= limit

    # Energy and magnetic-potential variance are not near a zero denominator,
    # so their RK2 refinement trend remains directly observable.
    assert refined.total_energy_relative_drift < coarse.total_energy_relative_drift
    assert fine.total_energy_relative_drift < refined.total_energy_relative_drift
    assert refined.magnetic_potential_variance_relative_drift < coarse.magnetic_potential_variance_relative_drift
    assert fine.magnetic_potential_variance_relative_drift < refined.magnetic_potential_variance_relative_drift


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
