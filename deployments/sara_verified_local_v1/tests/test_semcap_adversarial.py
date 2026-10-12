from worldshepherd_sara.semcap import SemcapMeasurements, evaluate_thresholds


def evaluate(m):
    return evaluate_thresholds(m, min_reduction=.90, min_utility_retention=.95,
        max_latency_ms=500, max_power_w=5, min_reconstruction_fidelity=.90,
        min_provenance_completeness=.99)


def base(**changes):
    d = dict(baseline_bits=1_000_000, semantic_bits=80_000,
        baseline_mission_utility=1.0, semantic_mission_utility=.98,
        latency_ms=100, power_w=2, missed_critical_events=0,
        false_semantic_selections=0, reconstruction_fidelity=.97,
        provenance_completeness=1.0)
    d.update(changes)
    return SemcapMeasurements(**d)


def test_bandwidth_win_with_critical_miss_is_failure():
    r = evaluate(base(semantic_bits=1_000, missed_critical_events=1))
    assert r["Q_C_reduction"] is True
    assert r["Q_critical_events"] is False


def test_good_semantics_with_incomplete_provenance_is_not_fully_qualified():
    r = evaluate(base(provenance_completeness=.5))
    assert r["Q_X_utility"] is True
    assert r["Q_E_provenance"] is False


def test_reconstruction_failure_is_independent_of_reduction():
    r = evaluate(base(reconstruction_fidelity=.2))
    assert r["Q_C_reduction"] is True
    assert r["Q_X_reconstruction"] is False
