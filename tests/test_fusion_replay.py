from worldshepherd_sara.fusion_control import SensorSample
from worldshepherd_sara.fusion_replay import FusionReplayRunner


def sample(ts: float, name: str, value: float, uncertainty: float = 0.5) -> SensorSample:
    return SensorSample(
        timestamp=ts,
        shot_id="replay-shot",
        diagnostic=name,
        value=value,
        unit="arb",
        uncertainty=uncertainty,
        valid=True,
        quality="test",
        provenance=f"fixture:{name}:{ts}",
    )


def series():
    upper = [
        sample(1.0, "upper", 112.0),
        sample(2.0, "upper", 108.0),
        sample(3.0, "upper", 104.0),
    ]
    lower = [
        sample(1.0, "lower", 88.0),
        sample(2.0, "lower", 92.0),
        sample(3.0, "lower", 96.0),
    ]
    return upper, lower


def test_identical_input_produces_identical_replay_fingerprint():
    upper, lower = series()
    runner = FusionReplayRunner()
    first = runner.replay(upper, lower)
    second = runner.replay(upper, lower)

    assert first.ledger_ok is True
    assert second.ledger_ok is True
    assert first.fingerprint_sha256 == second.fingerprint_sha256
    assert first.cycles == second.cycles
    assert first.cycle_count == 3


def test_changed_input_changes_replay_fingerprint():
    upper, lower = series()
    runner = FusionReplayRunner()
    baseline = runner.replay(upper, lower)

    altered = list(upper)
    altered[1] = sample(2.0, "upper", 107.0)
    changed = runner.replay(altered, lower)

    assert baseline.fingerprint_sha256 != changed.fingerprint_sha256


def test_replay_rejects_pair_time_skew():
    upper, lower = series()
    lower[1] = sample(2.01, "lower", 92.0)
    runner = FusionReplayRunner(maximum_pair_time_skew_s=1e-4)

    try:
        runner.replay(upper, lower)
    except ValueError as exc:
        assert "paired_timestamp_skew_exceeded" in str(exc)
    else:
        raise AssertionError("time-skewed diagnostic pair was not rejected")


def test_replay_rejects_non_increasing_time():
    upper, lower = series()
    upper[2] = sample(2.0, "upper", 104.0)
    lower[2] = sample(2.0, "lower", 96.0)
    runner = FusionReplayRunner()

    try:
        runner.replay(upper, lower)
    except ValueError as exc:
        assert "replay_time_not_strictly_increasing" in str(exc)
    else:
        raise AssertionError("non-increasing replay time was not rejected")
