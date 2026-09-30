import pytest
from worldshepherd_sara.semcap import SemcapMeasurements, evaluate_thresholds


def _m(**overrides):
    values = dict(
        baseline_bits=1_000_000,
        semantic_bits=80_000,
        baseline_mission_utility=1.0,
        semantic_mission_utility=0.98,
        latency_ms=100.0,
        power_w=2.0,
        missed_critical_events=0,
        false_semantic_selections=1,
        reconstruction_fidelity=0.97,
        provenance_completeness=1.0,
    )
    values.update(overrides)
    return SemcapMeasurements(**values)


def test_reduction_and_utility_are_separate():
    m = _m()
    assert m.reduction == pytest.approx(0.92)
    assert m.utility_retention == pytest.approx(0.98)


def test_high_reduction_cannot_hide_bad_utility():
    m = _m(semantic_bits=10_000, semantic_mission_utility=0.20)
    result = evaluate_thresholds(m, min_reduction=.90, min_utility_retention=.95,
        max_latency_ms=500, max_power_w=5, min_reconstruction_fidelity=.90,
        min_provenance_completeness=.99)
    assert result["Q_C_reduction"] is True
    assert result["Q_X_utility"] is False
    assert all(result.values()) is False


def test_missed_critical_event_fails_dimension():
    m = _m(missed_critical_events=1)
    result = evaluate_thresholds(m, min_reduction=.90, min_utility_retention=.95,
        max_latency_ms=500, max_power_w=5, min_reconstruction_fidelity=.90,
        min_provenance_completeness=.99)
    assert result["Q_critical_events"] is False


def test_invalid_baseline_is_rejected():
    with pytest.raises(ValueError):
        _m(baseline_bits=0).validate()
