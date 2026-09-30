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
        if decision.state != "CONSISTENT" or decision.offset\И\И›Ы™HЬ€XЪ\Ъ[Ы‹ќ[Щ\ќZ[ќWЬИ\И›Ы™N‚€™]\›€Ш[Xњ][Ыђ[ЪЬ”™\Э[
€[ЩK›Ы™K›Ы™K
‘VT“ђSРРSP”ђUSУ—У“ХРУУ”ТTХS•‹
B€
B€Y€XЪ\Ъ[Ы‹ќ[Щ\ќZ[ќWЬИ€Щ[‹™^\›[ЫX^Э[Щ\ќZ[ќWЬО‚€™]\›€Ш[Xњ][Ыђ[ЪЬ”™\Э[
€[ЩK›Ы™K›Ы™K
‘VT“ђSРРSP”ђUSУ—ХSђСT•RS•WХУЧХТQH‹
B€
B‚€XњЫЫ]WЭ[YHHШШ[ЭШ[Э[YH
ИXЪ\Ъ[Ы‹›Щ™њЩ]ЬВ€Щ[‹—Ш[ЪЬ—ЫЩ™њЩ]HXњЫЫ]WЭ[YHHШШ[Ы[Ы›ЭЫљXВ€Щ[‹—Ш[ЪЬ—Ы[Ы›ИHШШ[Ы[Ы›ЭЫљXВ€Щ[‹—Ш[ЪЬ—Э[Щ\ќZ[ќWЬИHX^
€Щ[‹љЫЭ™\—Ш\ЩWЭ[Щ\ќZ[ќWЬЛXЪ\Ъ[Ы‹ќ[Щ\ќZ[ќWЬВ€
B€Щ[‹—Ш[ЪЬ—ЬЫЭ\ЩHH‘VT“ђSТS•T•ђSРРSP”ђUSУ€‚€Щ[‹—ШЫX[€H€™]\›€Ш[Xњ][Ыђ[ЪЬ”™\Э[
€ќYKXњЫЫ]WЭ[YKЩ[‹—Ш[ЪЬ—Э[Щ\ќZ[ќWЬЛ\J
B€
B‚€Y€][X]JЩ[‹Ш[\\О€]\X›VРЫШЪФШ[\WKШШ[Ы[Ы›ЭЫљXО€›Ш]
HO€[YQXЪ\Ъ[ЫЋ‚€™X\ЫЫњО€\ЭЬЭ—HHЧB€\ШX›N€\ЭРЫШЪФШ[\WHHЧB‚€›Ь€И[€Ш[\\О‚€Y€›ЭЛњ›Э™[[ЩWЫЪО‚€™X\ЫЫњЛ\[™
€”“Х‘SђSђСWФ‘R‘PХћЬЛњЫЭ\ЩWЪYHЉB€ЫЫќ[ќYB€™]€HЩ[‹—Ы\ЭЬЩ\K™Щ]
ЛњЫЭ\ЩWЪY
B€Y€™]€\И›Э›Ы™H[™ЛњЩ\]Y[ЩHH™]Ћ‚€™X\ЫЫњЛ\[™
€”‘TVWФ‘R‘PХћЬЛњЫЭ\ЩWЪYHЉB€ЫЫќ[ќYB€\ШX›K\[™
КB‚€›Ь€И[€\ШX›N‚€Щ[‹—Ы\ЭЬЩ\VЬЛњЫЭ\ЩWЪYHHЛњЩ\]Y[ЩB‚€Y€[Љ\ШX›JHЩ[‹›Z[—ЬЫЭ\Щ\О‚€Щ[‹—ШЫX[€H€™]\›€[YQXЪ\Ъ[ЫЉ€•SђUђRSP“H‹›Ы™K[Љ\ШX›JK\J
K›Ы™K›Ы™K›Ы™K€\J™X\ЫЫњИ
ИИ’S”ХQ‘’PТQS•ФУХTђСTИ—JK€Щ[‹—Ш[ЪЬ—ЬЫЭ\ЩKЩ[‹—Ш[ЪЬ—Э[Щ\ќZ[ќWЬЛ€
B‚€Ы\Э\€HЩ[‹—Ы\™Щ\ЭШЫЫњЪ\Э[ќШЫ\Э\Љ\ШX›JB€Y€[ЉЫ\Э\ЉHЩ[‹›Z[—ЬЫЭ\Щ\О‚€Щ[‹—ШЫX[€H€[ИHЬЛњЫЭ\ЩWЭ[YH›Ь€И[€\ШX›WB€\ЬHX^
[КHHZ[Љ[КHY€[Љ[КH€H[ЩH›Ы™B€™]\›€[YQXЪ\Ъ[ЫЉ€‘QФђQQ‹›Ы™K[Љ\ШX›JK\J
K\Ь›Ы™K›Ы™K€\J™X\ЫЫњИ
ИИ““ЧФУХTђСWРУУ”СS”ХTИ—JK€Щ[‹—Ш[ЪЬ—ЬЫЭ\ЩKЩ[‹—Ш[ЪЬ—Э[Щ\ќZ[ќWЬЛ€
B‚€[Y\ИHЬЛњЫЭ\ЩWЭ[YH›Ь€И[€Ы\Э\—B€ЫЫњЩ[њЭ\ИHЭ]\ЭXЬЛ›YYX[Љ[Y\КB€\Ь\њЪ[Ы€HX^
[Y\КHHZ[Љ[Y\КHY€[Љ[Y\КH€H[ЩHЊ€YЬ™YHH\JЫЬќY
ЛњЫЭ\ЩWЪY›Ь€И[€Ы\Э\ЉJB€Y€[ЉЫ\Э\ЉH[Љ\ШX›JN‚€™X\ЫЫњЛ\[™
”УХTђСWУХUQT—СVУQQЉB‚€Y€Щ[‹—Ш[ЪЬ—ЫЩ™њЩ]\И›Ы™N‚€Y€Щ[‹њ™\]Z\™WЩ^\›[Ш[ЪЬЋ‚€Щ[‹—ШЫX[€H€™X\ЫЫњЛ\[™
‘VT“ђSРSђТФ—Ф‘TURT‘QЉB€™]\›€[YQXЪ\Ъ[ЫЉ€‘QФђQQ‹ЫЫњЩ[њЭ\Л[Љ\ШX›JKYЬ™YK\Ь\њЪ[Ы‹€›Ы™K›Ы™K\J™X\ЫЫњКK›Ы™K›Ы™K€
B€ИXЪЭШ\™XЫЫ\]X›H[ќ\›[›ЫЭЭ\›Ь€›Ы‹\ЭљXЭ\Ю[Y[ќЛ‚€Щ[‹—Ш[ЪЬ—ЫЩ™њЩ]HЫЫњЩ[њЭ\ИHШШ[Ы[Ы›ЭЫљXВ€Щ[‹—Ш[ЪЬ—Ы[Ы›ИHШШ[Ы[Ы›ЭЫљXВ€Щ[‹—Ш[ЪЬ—Э[Щ\ќZ[ќWЬИHЩ[‹љЫЭ™\—Ш\ЩWЭ[Щ\ќZ[ќWЬВ€Щ[‹—Ш[ЪЬ—ЬЫЭ\ЩHH’S•T“ђSФУХTђСWРУTХT€‚‚€[ЪЬ—Ы[Ы›ИHЩ[‹—Ш[ЪЬ—Ы[Ы›ИY€Щ[‹—Ш[ЪЬ—Ы[Ы›И\И›Э›Ы™H[ЩHШШ[Ы[Ы›ЭЫљXВ€[\ЩYHX^
ЊШШ[Ы[Ы›ЭЫљXИH[ЪЬ—Ы[Ы›КB€[ЪЬ—ЫЩ™њЩ]HЩ[‹—Ш[ЪЬ—ЫЩ™њЩ]Y€Щ[‹—Ш[ЪЬ—ЫЩ™њЩ]\И›Э›Ы™H[ЩHЊ€^XЭYHШШ[Ы[Ы›ЭЫљXИ
И[ЪЬ—ЫЩ™њЩ]€\ЩWЭ[Щ\ќZ[ќHHX^
€Щ[‹љЫЭ™\—Ш\ЩWЭ[Щ\ќZ[ќWЬЛ€Щ[‹—Ш[ЪЬ—Э[Щ\ќZ[ќWЬИЬ€Њ€
B€›Э[™H\ЩWЭ[Щ\ќZ[ќH
И[\ЩY
€Щ[‹љЫЭ™\—ЩљYќЬH
€YKM‚€\њ€HXњКЫЫњЩ[њЭ\ИH^XЭY
B€XњЧЫЪИH\њ€H›Э[™€Y€›ЭXњЧЫЪО‚€™X\ЫЫњЛ\[™
’УХ‘T—ФUTТP’SUWСђRSЉB‚€ЫЫњЩ[њЭ\ЧЫЪИH\Ь\њЪ[Ы€HЩ[‹ЫЫњЩ[њЭ\ЧЩ\Ь\њЪ[Ы—ЬВ€Y€ЫЫњЩ[њЭ\ЧЫЪИ[™XњЧЫЪО‚€Щ[‹—ШЫX[€
ПHB€[ЩN‚€Щ[‹—ШЫX[€H€Э]HH••TХQ€Y€Щ[‹—ШЫX[€ЏHЩ[‹ЫX[—Ь™\]Z\™Y[ЩH‘QФђQQ‚€Y€Э]HOH‘QФђQQ€[™Щ[‹—ШЫX[€€‚€™X\ЫЫњЛ\[™
”‘PУХ‘T–WТTХT‘TТTИЉB‚€™]\›€[YQXЪ\Ъ[ЫЉ€Э]KЫЫњЩ[њЭ\Л[Љ\ШX›JKYЬ™YK\Ь\њЪ[Ы‹\њ‹›Э[™€\J™X\ЫЫњКKЩ[‹—Ш[ЪЬ—ЬЫЭ\ЩKЩ[‹—Ш[ЪЬ—Э[Щ\ќZ[ќWЬЛ€
B