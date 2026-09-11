import pytest

from worldshepherd_sara.nsb_g13_actuator_forward_map import (
    NSBG13Report,
    allocate_modal_command,
    build_transfer_matrix,
    run_nsb_g13_benchmark,
    verify_nsb_g13_report,
)


def test_g13_default_report_passes_and_verifies():
    report = run_nsb_g13_benchmark()
    assert report.acceptance.acceptance_pass
    assert report.acceptance.nominal_reachability_pass
    assert report.acceptance.calibration_pass
    assert report.acceptance.single_fault_pass
    assert report.acceptance.saturation_detection_pass
    assert report.acceptance.closed_loop_pass
    assert verify_nsb_g13_report(report)


def test_g13_nominal_transfer_is_full_rank_and_low_residual():
    report = run_nsb_g13_benchmark()
    case = report.nominal_case
    assert case.effective_rank == 3
    assert case.transfer_condition_number <= report.acceptance.condition_number_limit
    assert case.relative_residual <= report.acceptance.nominal_residual_limit
    assert case.max_abs_actuator_command <= case.actuator_limit + 1e-12


def test_g13_calibration_improves_gain_drift_residual():
    case = run_nsb_g13_benchmark().calibration_case
    assert case.calibrated_relative_residual < case.uncalibrated_relative_residual
    assert case.calibrated_relative_residual <= 5e-4


def test_g13_single_tile_fault_preserves_reachability():
    case = run_nsb_g13_benchmark().fault_case
    assert case.effective_rank == 3
    assert case.relative_residual <= 5e-3
    assert case.max_abs_actuator_command <= 3.0 + 1e-12


def test_g13_saturation_is_flagged_unreachable():
    case = run_nsb_g13_benchmark().saturation_case
    assert case.saturated_actuators > 0
    assert case.relative_residual > 0.05
    assert case.correctly_flagged_unreachable


def test_g13_forward_mapped_loop_retains_control_effect():
    case = run_nsb_g13_benchmark().closed_loop_case
    assert case.target_modal_energy_reduction_fraction >= 0.15
    assert case.forward_map_vs_ideal_relative_gap <= 0.01
    assert case.enstrophy_reduction_fraction > 0.0
    assert case.max_modal_tracking_residual <= 5e-4


def test_g13_zero_target_returns_zero_actuation():
    matrix = build_transfer_matrix(tile_count=8)
    currents, realized, residual, saturated = allocate_modal_command((0.0, 0.0, 0.0), matrix=matrix)
    assert currents == (0.0,) * 8
    assert realized == (0.0, 0.0, 0.0)
    assert residual == 0.0
    assert saturated == 0


def test_g13_rejects_invalid_gain_profile():
    with pytest.raises(ValueError):
        build_transfer_matrix(tile_count=8, gain_profile=(1.0, 1.0))


def test_g13_digest_detects_tampering():
    report = run_nsb_g13_benchmark()
    tampered = report.model_copy(
        update={
            "nominal_case": report.nominal_case.model_copy(
                update={"relative_residual": report.nominal_case.relative_residual + 0.01}
            )
        }
    )
    assert not verify_nsb_g13_report(tampered)


def test_g13_fail_closed_physical_mapping_claim():
    report = run_nsb_g13_benchmark()
    payload = report.model_dump(mode="json")
    payload["physical_actuator_mapping_validated"] = True
    with pytest.raises(ValueError):
        NSBG13Report.model_validate(payload)


def test_g13_fail_closed_lab_claim():
    report = run_nsb_g13_benchmark()
    payload = report.model_dump(mode="json")
    payload["laboratory_validation_performed"] = True
    with pytest.raises(ValueError):
        NSBG13Report.model_validate(payload)
