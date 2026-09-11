from worldshepherd_sara.nsb_g14_geometry_em_forward_map import run_nsb_g14_benchmark, verify_nsb_g14_report


def test_g14_default_report_passes_and_verifies():
    report = run_nsb_g14_benchmark()
    assert report.acceptance.acceptance_pass
    assert verify_nsb_g14_report(report)


def test_g14_geometry_and_control_metrics_are_bounded():
    report = run_nsb_g14_benchmark()
    assert report.nominal_case.effective_rank == 3
    assert report.nominal_case.relative_modal_residual <= report.acceptance.nominal_residual_limit
    assert report.nominal_case.max_abs_coil_current_a <= report.geometry.coil_current_limit_a + 1e-12
    assert report.closed_loop_case.target_modal_energy_reduction_fraction >= report.acceptance.target_reduction_floor
    assert report.closed_loop_case.geometry_map_vs_ideal_relative_gap <= report.acceptance.ideal_gap_limit


def test_g14_recalibration_and_fault_paths_pass():
    report = run_nsb_g14_benchmark()
    assert report.geometry_mismatch_case.recalibrated_relative_modal_residual < report.geometry_mismatch_case.uncalibrated_relative_modal_residual
    assert report.fault_case.all_single_coil_faults_rank_three
    assert report.fault_case.worst_relative_modal_residual <= report.acceptance.single_fault_residual_limit
    assert report.saturation_case.correctly_flagged_unreachable
