from worldshepherd_sara.quantum_metasurface_uc06 import UC06PrecalibrationSummary, evaluate_uc06_precalibration, retained_uc06_status


def test_retained_uc06_status_is_progress_but_not_calibration():
    decision = retained_uc06_status()
    assert decision.accepted_as_precalibration_status is True
    assert decision.calibration_gate_satisfied is False
    assert decision.status == "PRECALIBRATION_EVIDENCE_PRESENT_GATE_NOT_SATISFIED"
    assert "frozen convergence gate failed" in decision.blockers
    assert "semantic equivalence not established" in decision.blockers
    assert "numerical equivalence not established" in decision.blockers
    assert "VNA correlation not executed" in decision.blockers
    assert "full campaign not authorized" in decision.blockers
    assert "raw solver artifacts are not yet in QRF custody" in decision.blockers
    assert decision.summary_digest.startswith("sha256:")


def test_tuning_or_posthoc_thresholds_keep_bridge_fail_closed():
    summary = UC06PrecalibrationSummary(
        campaign_id="UC06-TEST",
        solver="Palace",
        source_class="controlled-test",
        source_refs=("fixture",),
        six_smoke_runtime_matrix_complete=True,
        historical_points_compared=18,
        historical_points_total=18,
        parameter_tuning_applied=True,
        post_hoc_threshold_applied=True,
        frozen_convergence_gate_passed=True,
        semantic_equivalence_established=True,
        numerical_equivalence_established=True,
        vna_correlation_executed=True,
        full_campaign_authorized=True,
        raw_solver_artifacts_in_qrf_custody=True,
    )
    decision = evaluate_uc06_precalibration(summary)
    assert decision.calibration_gate_satisfied is False
    assert "parameter tuning was applied to the frozen comparison" in decision.blockers
    assert "post-hoc thresholding was applied" in decision.blockers
