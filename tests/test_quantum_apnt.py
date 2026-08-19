from worldshepherd_sara.quantum_apnt import evaluate_sensor_series, run_synthetic_apnt_benchmark


def test_apnt_truth_referenced_metrics_are_reproducible():
    result = evaluate_sensor_series(
        [10.0, 10.1, None, 10.2, 10.2],
        [10.0, 10.0, 10.0, 10.0, 10.0],
        tolerance=0.25,
    )
    assert result.sample_count == 4
    assert result.availability == 0.8
    assert result.bias > 0
    assert result.rmse > 0
    assert result.within_tolerance_fraction == 1.0
    assert result.evidence_digest.startswith("sha256:")
    assert result.mission_use_decision.startswith("NO_GO_BELOW_97")


def test_apnt_synthetic_benchmark_closes_only_internal_surrogate_precondition():
    benchmark = run_synthetic_apnt_benchmark()

    assert benchmark.benchmark_id == "WS-APNT-SYN-001"
    assert benchmark.evidence_level == "synthetic_surrogate"
    assert benchmark.sample_count_total == 128
    assert benchmark.metrics.sample_count < benchmark.sample_count_total
    assert benchmark.metrics.availability >= benchmark.acceptance_criteria["minimum_availability"]
    assert benchmark.metrics.rmse <= benchmark.acceptance_criteria["maximum_rmse"]
    assert abs(benchmark.metrics.bias) <= benchmark.acceptance_criteria["maximum_abs_bias"]
    assert benchmark.metrics.within_tolerance_fraction >= benchmark.acceptance_criteria["minimum_within_tolerance_fraction"]
    assert abs(benchmark.metrics.drift_per_sample) <= benchmark.acceptance_criteria["maximum_abs_drift_per_sample"]
    assert benchmark.accepted is True
    assert benchmark.precondition_id == "WS-APNT-P0-SIMULATED-SENSOR-BENCHMARK"
    assert benchmark.truth_digest.startswith("sha256:")
    assert benchmark.measured_digest.startswith("sha256:")
    assert "not calibrated sensor evidence" in benchmark.claim_control


def test_apnt_synthetic_benchmark_refuses_too_small_series():
    try:
        run_synthetic_apnt_benchmark(sample_count=32)
    except ValueError as exc:
        assert "at least 64" in str(exc)
    else:
        raise AssertionError("benchmark accepted a series below the frozen minimum")
