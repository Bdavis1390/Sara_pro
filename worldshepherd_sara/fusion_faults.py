"""Deterministic diagnostic fault injection for WS-FUSION-CTRL-001.

The campaign mutates offline SensorSample fixtures only.  It has no network or
hardware side effects.  Its purpose is to demonstrate that malformed or
inconsistent diagnostic streams stop before a virtual command can be treated
as valid.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Sequence, Tuple

from worldshepherd_sara.fusion_control import SensorSample
from worldshepherd_sara.fusion_replay import FusionReplayRunner


FAULT_DROP_LOWER = "drop_lower_sample"
FAULT_PAIR_TIME_SKEW = "pair_time_skew"
FAULT_SHOT_MISMATCH = "shot_mismatch"
FAULT_MISSING_PROVENANCE = "missing_provenance"
FAULT_NONFINITE_VALUE = "nonfinite_value"
FAULT_INVALID_FLAG = "invalid_sensor_flag"
FAULT_DUPLICATE_PAIR = "duplicate_pair"
FAULT_DELAYED_LOWER = "delayed_lower_stream"
FAULT_REORDERED_PAIR = "reordered_pair"
FAULT_DIAGNOSTIC_COLLISION = "diagnostic_identity_collision"
FAULT_MISSING_UNIT = "missing_unit_metadata"
FAULT_MISSING_QUALITY = "missing_quality_metadata"

_SUPPORTED_FAULTS = {
    FAULT_DROP_LOWER,
    FAULT_PAIR_TIME_SKEW,
    FAULT_SHOT_MISMATCH,
    FAULT_MISSING_PROVENANCE,
    FAULT_NONFINITE_VALUE,
    FAULT_INVALID_FLAG,
    FAULT_DUPLICATE_PAIR,
    FAULT_DELAYED_LOWER,
    FAULT_REORDERED_PAIR,
    FAULT_DIAGNOSTIC_COLLISION,
    FAULT_MISSING_UNIT,
    FAULT_MISSING_QUALITY,
}

_EXPECTED_REASON_FRAGMENT: Dict[str, str] = {
    FAULT_DROP_LOWER: "paired_series_length_mismatch",
    FAULT_PAIR_TIME_SKEW: "paired_timestamp_skew_exceeded",
    FAULT_SHOT_MISMATCH: "shot_id_mismatch",
    FAULT_MISSING_PROVENANCE: "provenance_missing",
    FAULT_NONFINITE_VALUE: "value_not_finite",
    FAULT_INVALID_FLAG: "sensor_invalid",
    FAULT_DUPLICATE_PAIR: "replay_time_not_strictly_increasing",
    FAULT_DELAYED_LOWER: "paired_timestamp_skew_exceeded",
    FAULT_REORDERED_PAIR: "replay_time_not_strictly_increasing",
    FAULT_DIAGNOSTIC_COLLISION: "optical diagnostic identity collision",
    FAULT_MISSING_UNIT: "unit_missing",
    FAULT_MISSING_QUALITY: "quality_missing",
}


@dataclass(frozen=True)
class FaultCampaignResult:
    fault: str
    safe_failure: bool
    observed_reason: str
    expected_reason_fragment: str


def inject_fault(
    upper_samples: Sequence[SensorSample],
    lower_samples: Sequence[SensorSample],
    fault: str,
    *,
    skew_s: float = 0.01,
) -> Tuple[Tuple[SensorSample, ...], Tuple[SensorSample, ...]]:
    if fault not in _SUPPORTED_FAULTS:
        raise ValueError(f"unsupported_fault:{fault}")
    if not upper_samples or not lower_samples:
        raise ValueError("fault_campaign_requires_nonempty_paired_input")

    upper = list(upper_samples)
    lower = list(lower_samples)

    if fault == FAULT_DROP_LOWER:
        lower = lower[:-1]
    elif fault == FAULT_PAIR_TIME_SKEW:
        lower[0] = replace(lower[0], timestamp=lower[0].timestamp + float(skew_s))
    elif fault == FAULT_SHOT_MISMATCH:
        lower[0] = replace(lower[0], shot_id=f"{lower[0].shot_id}-MISMATCH")
    elif fault == FAULT_MISSING_PROVENANCE:
        upper[0] = replace(upper[0], provenance="")
    elif fault == FAULT_NONFINITE_VALUE:
        upper[0] = replace(upper[0], value=float("nan"))
    elif fault == FAULT_INVALID_FLAG:
        upper[0] = replace(upper[0], valid=False)
    elif fault == FAULT_DUPLICATE_PAIR:
        upper.insert(1, upper[0])
        lower.insert(1, lower[0])
    elif fault == FAULT_DELAYED_LOWER:
        index = 1 if len(lower) > 1 else 0
        lower[index] = replace(lower[index], timestamp=lower[index].timestamp + float(skew_s))
    elif fault == FAULT_REORDERED_PAIR:
        if len(upper) < 2 or len(lower) < 2:
            raise ValueError("reordered_pair_requires_at_least_two_pairs")
        upper[0], upper[1] = upper[1], upper[0]
        lower[0], lower[1] = lower[1], lower[0]
    elif fault == FAULT_DIAGNOSTIC_COLLISION:
        lower[0] = replace(lower[0], diagnostic=upper[0].diagnostic)
    elif fault == FAULT_MISSING_UNIT:
        upper[0] = replace(upper[0], unit="")
    elif fault == FAULT_MISSING_QUALITY:
        upper[0] = replace(upper[0], quality="")

    return tuple(upper), tuple(lower)


def run_fault_case(
    runner: FusionReplayRunner,
    upper_samples: Sequence[SensorSample],
    lower_samples: Sequence[SensorSample],
    fault: str,
    *,
    skew_s: float = 0.01,
) -> FaultCampaignResult:
    expected = _EXPECTED_REASON_FRAGMENT.get(fault)
    if expected is None:
        raise ValueError(f"unsupported_fault:{fault}")

    upper, lower = inject_fault(
        upper_samples,
        lower_samples,
        fault,
        skew_s=skew_s,
    )
    try:
        runner.replay(upper, lower)
    except ValueError as exc:
        reason = str(exc)
        return FaultCampaignResult(
            fault=fault,
            safe_failure=expected in reason,
            observed_reason=reason,
            expected_reason_fragment=expected,
        )

    return FaultCampaignResult(
        fault=fault,
        safe_failure=False,
        observed_reason="fault_was_not_rejected",
        expected_reason_fragment=expected,
    )


def run_standard_fault_campaign(
    runner: FusionReplayRunner,
    upper_samples: Sequence[SensorSample],
    lower_samples: Sequence[SensorSample],
) -> Tuple[FaultCampaignResult, ...]:
    return tuple(
        run_fault_case(runner, upper_samples, lower_samples, fault)
        for fault in (
            FAULT_DROP_LOWER,
            FAULT_PAIR_TIME_SKEW,
            FAULT_SHOT_MISMATCH,
            FAULT_MISSING_PROVENANCE,
            FAULT_NONFINITE_VALUE,
            FAULT_INVALID_FLAG,
            FAULT_DUPLICATE_PAIR,
            FAULT_DELAYED_LOWER,
            FAULT_REORDERED_PAIR,
            FAULT_DIAGNOSTIC_COLLISION,
            FAULT_MISSING_UNIT,
            FAULT_MISSING_QUALITY,
        )
    )
