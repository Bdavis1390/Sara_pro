"""Estimator-consensus gate for WS-FUSION-CTRL-001.

The gate does not estimate plasma state and does not command actuators.  It is a
policy boundary between independently produced state estimates and downstream
control proposals.  A proposal path can require multiple distinct estimators
to agree within explicitly configured limits before their state is considered
consensus-eligible.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence, Tuple

from worldshepherd_sara.fusion_control import PlasmaStateEstimate


@dataclass(frozen=True)
class StateConsensusPolicy:
    minimum_estimators: int = 2
    minimum_confidence: float = 0.80
    maximum_time_skew_s: float = 0.001
    maximum_abs_disagreement_m: float = 0.01

    def validate(self) -> None:
        if self.minimum_estimators < 2:
            raise ValueError("minimum_estimators_must_be_at_least_two")
        if not (0.0 <= self.minimum_confidence <= 1.0):
            raise ValueError("minimum_confidence_out_of_range")
        if not math.isfinite(self.maximum_time_skew_s) or self.maximum_time_skew_s < 0:
            raise ValueError("maximum_time_skew_invalid")
        if not math.isfinite(self.maximum_abs_disagreement_m) or self.maximum_abs_disagreement_m < 0:
            raise ValueError("maximum_abs_disagreement_invalid")


@dataclass(frozen=True)
class StateConsensusResult:
    accepted: bool
    reason: str
    shot_id: str
    timestamp: float
    vertical_displacement_m: float | None
    confidence: float
    estimator_ids: Tuple[str, ...]
    disagreement_span_m: float | None


class StateConsensusGate:
    def __init__(self, policy: StateConsensusPolicy | None = None) -> None:
        self.policy = policy or StateConsensusPolicy()
        self.policy.validate()

    def evaluate(self, estimates: Sequence[PlasmaStateEstimate]) -> StateConsensusResult:
        if len(estimates) < self.policy.minimum_estimators:
            return self._reject("insufficient_estimators", estimates)

        estimator_ids = tuple(estimate.estimator_id.strip() for estimate in estimates)
        if any(not estimator_id for estimator_id in estimator_ids):
            return self._reject("estimator_id_missing", estimates)
        if len(set(estimator_ids)) != len(estimator_ids):
            return self._reject("estimators_not_independent_by_identity", estimates)

        shot_ids = {estimate.shot_id for estimate in estimates}
        if len(shot_ids) != 1 or "" in shot_ids:
            return self._reject("shot_id_mismatch", estimates)

        timestamps = [float(estimate.timestamp) for estimate in estimates]
        displacements = [float(estimate.vertical_displacement_m) for estimate in estimates]
        confidences = [float(estimate.confidence) for estimate in estimates]
        if any(not math.isfinite(value) for value in timestamps + displacements + confidences):
            return self._reject("nonfinite_estimator_output", estimates)
        if any(confidence < self.policy.minimum_confidence or confidence > 1.0 for confidence in confidences):
            return self._reject("estimator_confidence_below_policy", estimates)

        time_skew = max(timestamps) - min(timestamps)
        if time_skew > self.policy.maximum_time_skew_s:
            return self._reject("estimator_time_skew_exceeded", estimates)

        disagreement = max(displacements) - min(displacements)
        if disagreement > self.policy.maximum_abs_disagreement_m:
            return self._reject("estimator_disagreement_exceeded", estimates, disagreement)

        total_weight = sum(confidences)
        if total_weight <= 0:
            return self._reject("invalid_consensus_weight", estimates, disagreement)
        fused = sum(value * confidence for value, confidence in zip(displacements, confidences)) / total_weight

        return StateConsensusResult(
            accepted=True,
            reason="consensus_accepted",
            shot_id=next(iter(shot_ids)),
            timestamp=max(timestamps),
            vertical_displacement_m=fused,
            confidence=min(confidences),
            estimator_ids=estimator_ids,
            disagreement_span_m=disagreement,
        )

    def _reject(
        self,
        reason: str,
        estimates: Sequence[PlasmaStateEstimate],
        disagreement: float | None = None,
    ) -> StateConsensusResult:
        estimator_ids = tuple(estimate.estimator_id for estimate in estimates)
        shot_id = estimates[0].shot_id if estimates else ""
        finite_times = [float(e.timestamp) for e in estimates if math.isfinite(float(e.timestamp))]
        finite_confidences = [float(e.confidence) for e in estimates if math.isfinite(float(e.confidence))]
        return StateConsensusResult(
            accepted=False,
            reason=reason,
            shot_id=shot_id,
            timestamp=max(finite_times) if finite_times else 0.0,
            vertical_displacement_m=None,
            confidence=min(finite_confidences) if finite_confidences else 0.0,
            estimator_ids=estimator_ids,
            disagreement_span_m=disagreement,
        )
