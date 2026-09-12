from worldshepherd_sara.fusion_control import SensorSample
from worldshepherd_sara.fusion_faults import (
    FAULT_DROP_LOWER,
    FAULT_INVALID_FLAG,
    FAULT_MISSING_PROVENANCE,
    FAULT_NONFINITE_VALUE,
    FAULT_PAIR_TIME_SKEW,
    FAULT_SHOT_MISMATCH,
    run_fault_case,
    run_standard_fault_campaign,
)
from worldshepherd_sara.fusion_replay import FusionReplayRunner


def sample(ts: float, name: str, value: float) -> SensorSample:
    return SensorSample(
        timestamp=ts,
        shot_id="fault-shot",
        diagnostic=name,
        value=value,
        unit="arb",
        uncertainty=0.5,
        valid=True,
        quality="fault-fixture",
        provenance=f"fixture:{name}:{ts}",
    )


def paired_series():
    upper = [sample(1.0, "upper", 110.0), sample(2.0, "upper", 108.0)]
    lower = [sample(1.0, "lower", 90.0), sample(2.0, "lower", 92.0)]
    return upper, lower


def test_baseline_fixture_replays_before_fault_injection():
    upper, lower = paired_series()
    report = FusionReplayRunner().replay(upper, lower)
    assert report.ledger_ok is True
    assert report.cycle_count == 2


def test_standard_fault_campaign_fails_safe_for_all_cases():
    upper, lower = paired_series()
    results = run_standard_fault_campaign(FusionReplayRunner(), upper, lower)
    assert len(results) == 6
    assert all(result.safe_failure for result in results)


def test_drop_lower_sample_stops_replay():
    upper, lower = paired_series()
    result = run_fault_case(FusionReplayRunner(), upper, lower, FAULT_DROP_LOWER)
    assert result.safe_failure is True
    assert "paired_series_length_mismatch" in result.observed_reason


def test_pair_time_skew_stops_replay():
    upper, lower = paired_series()
    result = run_fault_case(FusionReplayRunner(), upper, lower, FAULT_PAIR_TIME_SKEW)
    assert result.safe_failure is True
    assert "paired_timestamp_skew_exceeded" in result.observed_reason


def test_shot_mismatch_stops_replay():
    upper, lower = paired_series()
    result = run_fault_case(FusionReplayRunner(), upper, lower, FAULT_SHOT_MISMATCH)
    assert result.safe_failure is True
    assert "shot_id_mismatch" in result.observed_reason


def test_corrupted_sample_integrity_faults_stop_before_valid_control():
    upper, lower = paired_series()
    for fault, expected in (
        (FAULT_MISSING_PROVENANCE, "provenance_missing"),
        (FAULT_NONFINITE_VALUE, "value_not_finite"),
        (FAULT_INVALID_FLAG, "sensor_invalid"),
    ):
        result = run_fault_case(FusionReplayRunner(), upper, lower, fault)
        assert result.safe_failure is True
        assert expected in result.observed_reason
