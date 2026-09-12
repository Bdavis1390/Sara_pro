"""Provenance-gated adapter for externally supplied state estimates.

This adapter deliberately does not implement a magnetic/equilibrium estimator.
It accepts a state estimate produced by an independent external method, validates
its identity/provenance/quality envelope, and converts it into the common
PlasmaStateEstimate contract for the consensus gate.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple

from worldshepherd_sara.fusion_control import PlasmaStateEstimate


@dataclass(frozen=True)
class ExternalObserverRecord:
    timestamp: float
    shot_id: str
    vertical_displacement_m: float
    confidence: float
    estimator_id: str
    method: str
    source_diagnostics: Tuple[str, ...]
    provenance: str
    quality: str
    validated_by_source: bool

    def validate(self) -> Tuple[bool, str]:
        if not math.isfinite(self.timestamp):
            return False, "timestamp_not_finite"
        if not self.shot_id.strip():
            return False, "shot_id_missing"
        if not math.isfinite(self.vertical_displacement_m):
            return False, "state_not_finite"
        if not (0.0 <= self.confidence <= 1.0):
            return False, "confidence_out_of_range"
        if not self.estimator_id.strip():
            return False, "estimator_id_missing"
        if not self.method.strip():
            return False, "method_missing"
        if not self.source_diagnostics or any(not item.strip() for item in self.source_diagnostics):
            return False, "source_diagnostics_missing"
        if not self.provenance.strip():
            return False, "provenance_missing"
        if not self.quality.strip():
            return False, "quality_missing"
        if not self.validated_by_source:
            return False, "external_estimate_not_source_validated"
        return True, "ok"


class ExternalObserverAdapter:
    """Fail-closed conversion into the shared state-estimate contract."""

    def __init__(self, *, minimum_confidence: float = 0.80) -> None:
        self.minimum_confidence = float(minimum_confidence)
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence_out_of_range")

    def adapt(self, record: ExternalObserverRecord) -> PlasmaStateEstimate:
        ok, reason = record.validate()
        if not ok:
            raise ValueError(reason)
        if record.confidence < self.minimum_confidence:
            raise ValueError("external_estimate_confidence_below_policy")

        estimate = PlasmaStateEstimate(
            timestamp=record.timestamp,
            shot_id=record.shot_id,
            vertical_displacement_m=record.vertical_displacement_m,
            confidence=record.confidence,
            estimator_id=record.estimator_id,
            source_diagnostics=record.source_diagnostics,
        )
        estimate_ok, estimate_reason = estimate.validate()
        if not estimate_ok:
            raise ValueError(f"adapted_state_invalid:{estimate_reason}")
        return estimate
