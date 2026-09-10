from __future__ import annotations

import pytest

from worldshepherd_sara.nsb_g8_independent_magnetic import (
    NSBG8Report,
    finite_difference_ohm_lorentz_operator,
    run_nsb_g8_benchmark,
    verify_nsb_g8_report,
)


@pytest.fixture(scope="module")
def report():
    return run_nsb_g8_benchmark()


def test_default_g8_gate_passes_and_digest_verifies(report):
    assert report.acceptance.acceptance_pass is True
    assert verify_nsb_g8_report(report) is True
    assert report.report_digest is not None
    assert report.report_digest.startswith("sha256:")


def test_independent_fd_replication_is_second_order(report):
    assert min(report.acceptance.spatial_orders) >= 1.9
    assert report.resolution_results[-1].l2_error <= 5e-3
    assert report.resolution_results[-1].relative_l2_error <= 3e-3


def test_orientation_null_and_maximum_cases_are_reproduced(report):
    parallel = report.orientation_results[0]
    perpendicular = report.orientation_results[1]
    assert parallel.orientation_fraction == pytest.approx(1.0, abs=1e-15)
    assert parallel.joule_dissipation_rate > 0.0
    assert perpendicular.orientation_fraction == pytest.approx(0.0, abs=1e-15)
    assert perpendicular.joule_dissipation_rate <= 1e-12
    assert perpendicular.fd_rms <= 1e-12


def test_joule_dissipation_matches_negative_lorentz_work(report):
    results = (*report.resolution_results, *report.orientation_results)
    assert max(result.work_identity_abs_error for result in results) <= 1e-12


def test_field_reversal_and_zero_magnetic_limits(report):
    assert report.field_sign_symmetry_l2 <= 1e-12
    assert report.zero_magnetic_operator_l2 <= 1e-12
    assert report.zero_magnetic_dissipation <= 1e-12


def test_public_fd_operator_rejects_bad_shapes_and_negative_damping():
    u = [[0.0] * 16 for _ in range(16)]
    v = [[0.0] * 16 for _ in range(16)]
    with pytest.raises(ValueError):
        finite_difference_ohm_lorentz_operator(
            u=u,
            v=v[:-1],
            field_angle_rad=0.0,
            magnetic_damping=0.7,
        )
    with pytest.raises(ValueError):
        finite_difference_ohm_lorentz_operator(
            u=u,
            v=v,
            field_angle_rad=0.0,
            magnetic_damping=-0.1,
        )


def test_report_tampering_breaks_digest(report):
    tampered = report.model_copy(update={"benchmark_version": "tampered"})
    assert verify_nsb_g8_report(tampered) is False


def test_claim_promotion_fails_closed(report):
    payload = report.model_dump(mode="json")
    payload["induction_equation_solved"] = True
    with pytest.raises(ValueError):
        NSBG8Report.model_validate(payload)

    payload = report.model_dump(mode="json")
    payload["spectral_magnetic_operator_called"] = True
    with pytest.raises(ValueError):
        NSBG8Report.model_validate(payload)


def test_non_factor_two_resolution_sequence_is_rejected():
    with pytest.raises(ValueError):
        run_nsb_g8_benchmark(resolution_grids=(32, 48, 96))


def test_field_angle_is_continuous_not_discrete(report):
    arbitrary = report.orientation_results[-1]
    assert arbitrary.field_angle_rad == pytest.approx(0.37)
    assert 0.0 < arbitrary.orientation_fraction < 1.0
    assert arbitrary.l2_error <= report.acceptance.orientation_l2_limit
