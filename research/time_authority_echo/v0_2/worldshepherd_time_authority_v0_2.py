from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Dict, List, Optional, Tuple
import statistics


@dataclass(frozen=True)
class ClockSample:
    source_id: str
    sequence: int
    source_time: float
    receive_monotonic: float
    provenance_ok: bool = True


@dataclass(frozen=True)
class ExternalCalibrationSample:
    provider_id: str
    sequence: int
    offset_s: float
    uncertainty_s: float
    provenance_ok: bool = True

    @property
    def low_s(self) -> float:
        return self.offset_s - self.uncertainty_s

    @property
    def high_s(self) -> float:
        return self.offset_s + self.uncertainty_s


@dataclass(frozen=True)
class ExternalCalibrationDecision:
    state: str  # CONSISTENT / DEGRADED / UNAVAILABLE
    offset_s: Optional[float]
    uncertainty_s: Optional[float]
    provider_count: int
    agreeing_providers: Tuple[str, ...]
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class CalibrationAnchorResult:
    accepted: bool
    absolute_time: Optional[float]
    anchor_uncertainty_s: Optional[float]
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class TimeDecision:
    state: str  # TRUSTED / DEGRADED / UNAVAILABLE
    consensus_time: Optional[float]
    source_count: int
    agreeing_sources: Tuple[str, ...]
    dispersion_s: Optional[float]
    holdover_error_s: Optional[float]
    holdover_bound_s: Optional[float]
    reasons: Tuple[str, ...]
    anchor_source: Optional[str] = None
    anchor_uncertainty_s: Optional[float] = None


class TimeAuthority:
    """Bounded time authority with optional externally calibrated holdover.

    Evidence layers are deliberately separate:
      * source provenance / anti-replay
      * source consensus
      * external UTC-offset interval calibration
      * local monotonic holdover
      * authority state

    This primitive does not discipline a physical clock and does not claim NTP/PTP,
    GNSS, oscillator, or certified timing performance.
    """

    def __init__(
        self,
        *,
        min_sources: int = 2,
        consensus_dispersion_s: float = 0.008,
        holdover_base_uncertainty_s: float = 0.007,
        holdover_drift_ppm: float = 15.0,
        clean_required: int = 4,
        min_external_providers: int = 2,
        external_max_uncertainty_s: float = 0.025,
        require_external_anchor: bool = False,
    ):
        self.min_sources = min_sources
        self.consensus_dispersion_s = consensus_dispersion_s
        self.holdover_base_uncertainty_s = holdover_base_uncertainty_s
        self.holdover_drift_ppm = holdover_drift_ppm
        self.clean_required = clean_required
        self.min_external_providers = min_external_providers
        self.external_max_uncertainty_s = external_max_uncertainty_s
        self.require_external_anchor = require_external_anchor

        self._last_seq: Dict[str, int] = {}
        self._last_external_seq: Dict[str, int] = {}
        self._anchor_offset: Optional[float] = None  # absolute time - local monotonic
        self._anchor_mono: Optional[float] = None
        self._anchor_uncertainty_s: Optional[float] = None
        self._anchor_source: Optional[str] = None
        self._clean = 0

    def _largest_consistent_cluster(self, samples: List[ClockSample]) -> List[ClockSample]:
        if not samples:
            return []
        ss = sorted(samples, key=lambda s: s.source_time)
        best: List[ClockSample] = []
        for i in range(len(ss)):
            j = i
            while j + 1 < len(ss) and ss[j + 1].source_time - ss[i].source_time <= self.consensus_dispersion_s:
                j += 1
            cluster = ss[i:j + 1]
            if len(cluster) > len(best):
                best = cluster
        return best

    @staticmethod
    def _largest_interval_cluster(samples: List[ExternalCalibrationSample]) -> List[ExternalCalibrationSample]:
        """Return the largest subset with a non-empty common interval intersection."""
        if not samples:
            return []
        candidates: List[float] = []
        for s in samples:
            candidates.extend((s.low_s, s.offset_s, s.high_s))
        best: List[ExternalCalibrationSample] = []
        best_width: Optional[float] = None
        for point in candidates:
            cluster = [s for s in samples if s.low_s <= point <= s.high_s]
            if not cluster:
                continue
            low = max(s.low_s for s in cluster)
            high = min(s.high_s for s in cluster)
            if low > high:
                continue
            width = high - low
            if len(cluster) > len(best) or (len(cluster) == len(best) and (best_width is None or width < best_width)):
                best = cluster
                best_width = width
        return best

    def evaluate_external_calibration(
        self, samples: Iterable[ExternalCalibrationSample]
    ) -> ExternalCalibrationDecision:
        reasons: List[str] = []
        usable: List[ExternalCalibrationSample] = []

        for s in samples:
            if not s.provenance_ok:
                reasons.append(f"EXTERNAL_PROVENANCE_REJECT:{s.provider_id}")
                continue
            if s.uncertainty_s < 0:
                reasons.append(f"EXTERNAL_INVALID_UNCERTAINTY:{s.provider_id}")
                continue
            prev = self._last_external_seq.get(s.provider_id)
            if prev is not None and s.sequence <= prev:
                reasons.append(f"EXTERNAL_REPLAY_REJECT:{s.provider_id}")
                continue
            usable.append(s)

        for s in usable:
            self._last_external_seq[s.provider_id] = s.sequence

        if len(usable) < self.min_external_providers:
            return ExternalCalibrationDecision(
                "UNAVAILABLE", None, None, len(usable), tuple(),
                tuple(reasons + ["INSUFFICIENT_EXTERNAL_PROVIDERS"]),
            )

        cluster = self._largest_interval_cluster(usable)
        if len(cluster) < self.min_external_providers:
            return ExternalCalibrationDecision(
                "DEGRADED", None, None, len(usable), tuple(),
                tuple(reasons + ["NO_EXTERNAL_INTERVAL_CONSENSUS"]),
            )

        low = max(s.low_s for s in cluster)
        high = min(s.high_s for s in cluster)
        offset = (low + high) / 2
        uncertainty = (high - low) / 2
        agreeing = tuple(sorted(s.provider_id for s in cluster))
        if len(cluster) < len(usable):
            reasons.append("EXTERNAL_PROVIDER_OUTLIER_EXCLUDED")

        if uncertainty > self.external_max_uncertainty_s:
            reasons.append("EXTERNAL_CALIBRATION_UNCERTAINTY_TOO_WIDE")
            state = "DEGRADED"
        else:
            state = "CONSISTENT"

        return ExternalCalibrationDecision(
            state, offset, uncertainty, len(usable), agreeing, tuple(reasons)
        )

    def seed_external_anchor(
        self,
        decision: ExternalCalibrationDecision,
        *,
        local_wall_time: float,
        local_monotonic: float,
    ) -> CalibrationAnchorResult:
        if decision.state != "CONSISTENT" or decision.offset_s is None or decision.uncertainty_s is None:
            return CalibrationAnchorResult(
                False, None, None, ("EXTERNAL_CALIBRATION_NOT_CONSISTENT",)
            )
        if decision.uncertainty_s > self.external_max_uncertainty_s:
            return CalibrationAnchorResult(
                False, None, None, ("EXTERNAL_CALIBRATION_UNCERTAINTY_TOO_WIDE",)
            )

        absolute_time = local_wall_time + decision.offset_s
        self._anchor_offset = absolute_time - local_monotonic
        self._anchor_mono = local_monotonic
        self._anchor_uncertainty_s = max(
            self.holdover_base_uncertainty_s, decision.uncertainty_s
        )
        self._anchor_source = "EXTERNAL_INTERVAL_CALIBRATION"
        self._clean = 0
        return CalibrationAnchorResult(
            True, absolute_time, self._anchor_uncertainty_s, tuple()
        )

    def evaluate(self, samples: Iterable[ClockSample], local_monotonic: float) -> TimeDecision:
        reasons: List[str] = []
        usable: List[ClockSample] = []

        for s in samples:
            if not s.provenance_ok:
                reasons.append(f"PROVENANCE_REJECT:{s.source_id}")
                continue
            prev = self._last_seq.get(s.source_id)
            if prev is not None and s.sequence <= prev:
                reasons.append(f"REPLAY_REJECT:{s.source_id}")
                continue
            usable.append(s)

        for s in usable:
            self._last_seq[s.source_id] = s.sequence

        if len(usable) < self.min_sources:
            self._clean = 0
            return TimeDecision(
                "UNAVAILABLE", None, len(usable), tuple(), None, None, None,
                tuple(reasons + ["INSUFFICIENT_SOURCES"]),
                self._anchor_source, self._anchor_uncertainty_s,
            )

        cluster = self._largest_consistent_cluster(usable)
        if len(cluster) < self.min_sources:
            self._clean = 0
            vals = [s.source_time for s in usable]
            disp = max(vals) - min(vals) if len(vals) > 1 else None
            return TimeDecision(
                "DEGRADED", None, len(usable), tuple(), disp, None, None,
                tuple(reasons + ["NO_SOURCE_CONSENSUS"]),
                self._anchor_source, self._anchor_uncertainty_s,
            )

        times = [s.source_time for s in cluster]
        consensus = statistics.median(times)
        dispersion = max(times) - min(times) if len(times) > 1 else 0.0
        agree = tuple(sorted(s.source_id for s in cluster))
        if len(cluster) < len(usable):
            reasons.append("SOURCE_OUTLIER_EXCLUDED")

        if self._anchor_offset is None:
            if self.require_external_anchor:
                self._clean = 0
                reasons.append("EXTERNAL_ANCHOR_REQUIRED")
                return TimeDecision(
                    "DEGRADED", consensus, len(usable), agree, dispersion,
                    None, None, tuple(reasons), None, None,
                )
            # Backward-compatible internal bootstrap for non-strict deployments.
            self._anchor_offset = consensus - local_monotonic
            self._anchor_mono = local_monotonic
            self._anchor_uncertainty_s = self.holdover_base_uncertainty_s
            self._anchor_source = "INTERNAL_SOURCE_CLUSTER"

        anchor_mono = self._anchor_mono if self._anchor_mono is not None else local_monotonic
        elapsed = max(0.0, local_monotonic - anchor_mono)
        anchor_offset = self._anchor_offset if self._anchor_offset is not None else 0.0
        expected = local_monotonic + anchor_offset
        base_uncertainty = max(
            self.holdover_base_uncertainty_s,
            self._anchor_uncertainty_s or 0.0,
        )
        bound = base_uncertainty + elapsed * self.holdover_drift_ppm * 1e-6
        herr = abs(consensus - expected)
        abs_ok = herr <= bound
        if not abs_ok:
            reasons.append("HOLDOVER_PLAUSIBILITY_FAIL")

        consensus_ok = dispersion <= self.consensus_dispersion_s
        if consensus_ok and abs_ok:
            self._clean += 1
        else:
            self._clean = 0
        state = "TRUSTED" if self._clean >= self.clean_required else "DEGRADED"
        if state == "DEGRADED" and self._clean > 0:
            reasons.append("RECOVERY_HYSTERESIS")

        return TimeDecision(
            state, consensus, len(usable), agree, dispersion, herr, bound,
            tuple(reasons), self._anchor_source, self._anchor_uncertainty_s,
        )
