import pytest

from worldshepherd_sara.nsb_g16_electrothermal_driver import (
    G16DriverConfig,
    NSBG16Report,
    _inductance_matrix,
    _invert_matrix,
    run_nsb_g16_benchmark,
    verify_nsb_g16_report,
)
from worldshepherd_sara.nsb_g15_finite_geometry_em import G15Geometry


@pytest.fixture(scope="module")
def report():
    return run_nsb_g16_benchmark()


def test_g16_default_report_passes_and_verifies(report):
    assert report.acceptance.acceptance_pass
    assert report.acceptance.circuit_pass
    assert report.acceptance.step_response_pass
    assert report.acceptance.thermal_pass
    assert report.acceptance.bandwidth_limit_detection_pass
    assert report.acceptance.closed_loop_pass
    assert verify_nsb_g16_report(report)


def test_g16_inductance_matrix_is_symmetric_and_invertible():
    matrix = _inductance_matrix(G15Geometry())
    assert len(matrix) == 8
    for i in range(8):
        assert matrix[i][i] > 0.0
        for j in range(8):
            assert matrix[i][j] == pytest.approx(matrix[j][i], rel=1e-12, abs=1e-15)
    inverse = _invert_matrix(matrix)
    assert len(inverse) == 8


def test_g16_step_response_is_bounded(report):
    case = report.step_response_case
    assert case.final_relative_current_error <= report.acceptance.step_error_limit
    assert case.settling_time_s is not None
    assert case.settling_time_s <= report.acceptance.step_settling_limit_s
    assert case.max_abs_voltage_v <= report.driver.driver_voltage_limit_v + 1e-12
    assert case.max_abs_current_a <= report.driver.current_limit_a + 1e-12


def test_g16_thermal_dwell_remains_below_limit(report):
    case = report.thermal_case
    assert case.temperature_rise_k > 0.0
    assert case.final_resistance_ratio > 1.0
    assert case.peak_temperature_k < case.thermal_limit_k


def test_g16_detects_unreachable_fast_command(report):
    case = report.bandwidth_case
    assert case.rms_tracking_error_fraction >= 0.20
    assert case.correctly_flagged_bandwidth_limited


def test_g16_dynamic_closed_loop_retains_control_effect(report):
    case = report.closed_loop_case
    assert case.target_modal_energy_reduction_fraction >= report.acceptance.target_reduction_floor
    assert case.dynamic_driver_vs_ideal_relative_gap <= report.acceptance.ideal_gap_limit
    assert case.enstrophy_reduction_fraction > 0.0
    assert case.max_abs_current_a <= report.driver.current_limit_a + 1e-12
    assert case.max_abs_voltage_v <= report.driver.driver_voltage_limit_v + 1e-12


def test_g16_digest_detects_tampering(report):
    tampered = report.model_copy(
        update={
            "step_response_case": report.step_response_case.model_copy(
                update={"final_relative_current_error": report.step_response_case.final_relative_current_error + 0.01}
            )
        }
    )
    assert not verify_nsb_g16_report(tampered)


def test_g16_fail_closed_measured_lcr_claim(report):
    payload = report.model_dump(mode="json")
    payload["measured_lcr_parameters_used"] = True
    with pytest.raises(ValueError):
        NSBG16Report.model_validate(payload)


def test_g16_rejects_nonpositive_driver_limit():
    with pytest.raises(ValueError):
        G16DriverConfig(driver_voltage_limit_v=0.0)
