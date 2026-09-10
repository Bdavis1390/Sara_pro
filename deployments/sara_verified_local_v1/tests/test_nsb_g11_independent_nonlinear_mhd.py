import pytest

from worldshepherd_sara.nsb_g11_independent_nonlinear_mhd import (
    NSBG11Report,
    integrate_fd_mhd,
    run_nsb_g11_benchmark,
    verify_nsb_g11_report,
)


REPORT = run_nsb_g11_benchmark()


def test_g11_default_report_passes_and_verifies():
    report = REPORT
    assert report.acceptance.acceptance_pass
    assert report.acceptance.cross_method_pass
    assert report.acceptance.cancellation_pass
    assert report.acceptance.geometry_pass
    assert report.acceptance.energy_pass
    assert verify_nsb_g11_report(report)


def test_g11_cross_method_converges_with_refinement():
    report = REPORT
    points = report.cross_method_case.points
    assert points[1].combined_relative_difference < points[0].combined_relative_difference
    assert points[2].combined_relative_difference < points[1].combined_relative_difference
    assert min(report.cross_method_case.observed_orders) >= report.acceptance.spatial_order_floor
    assert points[-1].combined_relative_difference <= report.acceptance.cross_method_relative_limit


def test_g11_aligned_alfvenic_case_cancels_nonlinearity():
    case = REPORT.aligned_case
    assert case.nonlinear_advection_rms > 1e-3
    assert case.lorentz_curl_rms > 1e-3
    assert case.nonlinear_cancellation_rms <= 1e-10
    assert case.induction_advection_rms <= 1e-10


def test_g11_geometry_and_energy_are_bounded():
    report = REPORT
    case = report.cross_method_case
    assert case.fd_velocity_divergence_rms <= report.acceptance.divergence_limit
    assert case.fd_magnetic_divergence_rms <= report.acceptance.divergence_limit
    assert case.fd_total_energy_final < case.fd_total_energy_initial
    assert case.final_total_energy_relative_difference <= report.acceptance.energy_relative_limit


def test_g11_integrator_rejects_invalid_dt():
    omega = [[0.0] * 8 for _ in range(8)]
    a = [[0.0] * 8 for _ in range(8)]
    with pytest.raises(ValueError):
        integrate_fd_mhd(
            initial_vorticity=omega,
            initial_magnetic_potential=a,
            viscosity=0.01,
            resistivity=0.01,
            dt=0.0,
            final_time=0.01,
        )


def test_g11_digest_detects_tampering():
    report = REPORT
    tampered = report.model_copy(
        update={
            "cross_method_case": report.cross_method_case.model_copy(
                update={"finest_combined_relative_difference": report.cross_method_case.finest_combined_relative_difference + 0.01}
            )
        }
    )
    assert not verify_nsb_g11_report(tampered)


def test_g11_fail_closed_external_validation_claim():
    payload = REPORT.model_dump(mode="json")
    payload["independent_third_party_validation_claimed"] = True
    with pytest.raises(ValueError):
        NSBG11Report.model_validate(payload)


def test_g11_fail_closed_plasma_claim():
    payload = REPORT.model_dump(mode="json")
    payload["plasma_solved"] = True
    with pytest.raises(ValueError):
        NSBG11Report.model_validate(payload)
