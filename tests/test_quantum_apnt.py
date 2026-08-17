from worldshepherd_sara.quantum_apnt import evaluate_sensor_series


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
