import pytest

from baros.reliability import (
    DEFAULT_CASE_COUNT,
    DEFAULT_CONFIDENCE,
    DEFAULT_TARGET_PROBABILITY,
    minimum_zero_failure_trials,
    run_reliability_gate,
    zero_failure_lower_bound,
)


def test_exact_zero_failure_sample_size_for_987_at_999_confidence():
    required = minimum_zero_failure_trials(
        target_probability=0.987,
        confidence=0.999,
    )
    assert required == 528
    assert zero_failure_lower_bound(trials=required, confidence=0.999) >= 0.987
    assert zero_failure_lower_bound(trials=required - 1, confidence=0.999) < 0.987


def test_default_population_has_statistical_margin_over_987():
    lower = zero_failure_lower_bound(
        trials=DEFAULT_CASE_COUNT,
        confidence=DEFAULT_CONFIDENCE,
    )
    assert DEFAULT_CASE_COUNT == 1000
    assert DEFAULT_CONFIDENCE == pytest.approx(0.999)
    assert DEFAULT_TARGET_PROBABILITY == pytest.approx(0.987)
    assert lower > DEFAULT_TARGET_PROBABILITY
    assert lower > 0.993


def test_full_predeclared_1000_case_reliability_gate():
    report = run_reliability_gate(commit_sha="TEST-RELIABILITY")
    assert report.cases == 1000
    assert report.successes == 1000
    assert report.failures == 0
    assert report.gate_passed is True
    assert report.lower_confidence_bound > 0.993
    assert report.lower_confidence_bound >= report.target_probability
    assert report.failed_case_indices == ()
    assert len(report.case_results_sha256) == 64


def test_underpowered_reliability_claim_fails_closed():
    with pytest.raises(ValueError, match="insufficient"):
        run_reliability_gate(
            cases=527,
            confidence=0.999,
            target_probability=0.987,
        )
