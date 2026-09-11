from worldshepherd_sara.nsb_g15_finite_geometry_em import run_nsb_g15_benchmark, verify_nsb_g15_report


def test_g15_default_report_passes_and_verifies():
    report = run_nsb_g15_benchmark()
    assert report.acceptance.acceptance_pass
    assert verify_nsb_g15_report(report)


def test_g15_loop_and_conduction_verification_pass():
    report = run_nsb_g15_benchmark()
    assert report.acceptance.loop_verification_pass
    assert report.loop_verification_case.finest_relative_error <= report.acceptance.loop_error_limit
    assert report.loop_verification_case.convergence_ratio_48_to_96 > 3.5
    assert report.acceptance.conduction_solve_pass
    assert report.conduction_case.mean_jy_relative_error <= report.acceptance.conduction_relative_error_limit
    assert report.conduction_case.jy_relative_std <= report.acceptance.conduction_uniformity_limit


def test_g15_reachability_fault_and_closed_loop_pass():
    report = run_nsb_g15_benchmark()
    assert report.nominal_case.effective_rank == 3
    assert report.acceptance.nominal_reachability_pass
    assert report.fault_case.all_single_coil_faults_rank_three
    assert report.acceptance.single_fault_pass
    assert report.closed_loop_case.target_modal_energy_reduction_fraction >= report.acceptance.target_reduction_floor
    assert report.closed_loop_case.finite_geometry_vs_ideal_relative_gap <= report.acceptance.ideal_gap_limit
    assert report.acceptance.closed_loop_pass
