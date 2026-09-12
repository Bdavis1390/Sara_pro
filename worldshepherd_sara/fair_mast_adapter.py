"""Read-only FAIR-MAST adapter for WS-FUSION-CTRL-001.

This module converts public FAIR-MAST metadata/series references into the
simulator-only SensorSample contract.  It deliberately contains no actuator,
EPICS, CODAC, RTF, coil, gas, or heating command path.

FAIR-MAST publishes shot metadata through a JSON API and diagnostic arrays as
Zarr objects in a public S3 bucket.  The adapter keeps those source identities
in every generated provenance string so downstream replay can identify the
exact archive level, shot, diagnostic group, signal, and sample index.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from worldshepherd_sara.fusion_control import SensorSample


FAIR_MAST_API_BASE = "https://mastapp.site/json"
FAIR_MAST_S3_ENDPOINT = "https://s3.echo.stfc.ac.uk"
FAIR_MAST_BUCKET = "mast"
_ALLOWED_API_HOSTS = {"mastapp.site"}
_ALLOWED_LEVELS = {"level1", "level2"}


@dataclass(frozen=True)
class FairMastSource:
    shot_id: int
    diagnostic_group: str
    signal: str
    level: str = "level1"

    def validate(self) -> Tuple[bool, str]:
        if int(self.shot_id) <= 0:
            return False, "shot_id_invalid"
        if self.level not in _ALLOWED_LEVELS:
            return False, "data_level_not_allowlisted"
        if not self.diagnostic_group.strip():
            return False, "diagnostic_group_missing"
        if not self.signal.strip():
            return False, "signal_missing"
        if "/" in self.diagnostic_group.strip("/"):
            return False, "diagnostic_group_must_be_single_path_component"
        if "/" in self.signal.strip("/"):
            return False, "signal_must_be_single_path_component"
        return True, "ok"

    @property
    def zarr_uri(self) -> str:
        ok, reason = self.validate()
        if not ok:
            raise ValueError(reason)
        return (
            f"s3://{FAIR_MAST_BUCKET}/{self.level}/shots/{int(self.shot_id)}.zarr/"
            f"{self.diagnostic_group}"
        )

    @property
    def diagnostic_name(self) -> str:
        return f"{self.diagnostic_group}/{self.signal}"

    def provenance_for_index(self, index: int) -> str:
        return (
            f"fair-mast|endpoint={FAIR_MAST_S3_ENDPOINT}|uri={self.zarr_uri}"
            f"|signal={self.signal}|index={int(index)}|level={self.level}"
        )


class FairMastQualityPolicy:
    """Conservative source-quality rules for replay/analysis preparation.

    A published FAIR-MAST issue reports severe quantization in at least one
    Level-2 magnetics dataset and recommends Level-1 raw data for analyses that
    depend on derivatives.  Until the scope is resolved, derivative-sensitive
    Level-2 magnetic signals are blocked by default instead of silently treated
    as equivalent to Level-1 data.
    """

    @staticmethod
    def evaluate(source: FairMastSource, *, derivative_sensitive: bool = False) -> Tuple[bool, str]:
        ok, reason = source.validate()
        if not ok:
            return False, reason

        name = source.diagnostic_name.lower()
        looks_magnetic = (
            "magnet" in name
            or "mirnov" in name
            or "saddle" in name
            or "b_field" in name
        )
        if derivative_sensitive and source.level == "level2" and looks_magnetic:
            return False, "level2_magnetics_derivative_quality_risk"
        return True, "ok"


class FairMastReadOnlyMetadataClient:
    """Strict GET-only client for FAIR-MAST shot metadata.

    Network access is not used by unit tests.  The client is intentionally
    host-allowlisted and exposes no arbitrary-URL fetch method.
    """

    def __init__(self, base_url: str = FAIR_MAST_API_BASE, timeout_s: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = float(timeout_s)
        self._validate_base_url()

    def _validate_base_url(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https":
            raise ValueError("FAIR-MAST API must use https")
        if parsed.hostname not in _ALLOWED_API_HOSTS:
            raise ValueError("FAIR-MAST API host not allowlisted")
        if not parsed.path.startswith("/json"):
            raise ValueError("FAIR-MAST API base path must start with /json")
        if not math.isfinite(self.timeout_s) or self.timeout_s <= 0 or self.timeout_s > 60:
            raise ValueError("timeout_s must be in (0, 60]")

    def shot_url(self, shot_id: int) -> str:
        shot = int(shot_id)
        if shot <= 0:
            raise ValueError("shot_id_invalid")
        return f"{self.base_url}/shots/{shot}"

    def fetch_shot_metadata(self, shot_id: int) -> Dict[str, Any]:
        request = Request(
            self.shot_url(shot_id),
            method="GET",
            headers={"Accept": "application/json", "User-Agent": "Worldshepherd-FAIR-MAST-readonly/0.1"},
        )
        with urlopen(request, timeout=self.timeout_s) as response:  # nosec B310: URL host is allowlisted above
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"FAIR-MAST metadata request returned HTTP {status}")
            payload = response.read()
        decoded = json.loads(payload.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("FAIR-MAST metadata payload must be a JSON object")
        return decoded


def _expand_uncertainty(uncertainty: float | Sequence[float], count: int) -> List[float]:
    if isinstance(uncertainty, (int, float)):
        values = [float(uncertainty)] * count
    else:
        values = [float(value) for value in uncertainty]
        if len(values) != count:
            raise ValueError("uncertainty_length_mismatch")
    if any((not math.isfinite(value) or value < 0) for value in values):
        raise ValueError("uncertainty_invalid")
    return values


def series_to_sensor_samples(
    source: FairMastSource,
    timestamps: Sequence[float],
    values: Sequence[float],
    *,
    unit: str,
    uncertainty: float | Sequence[float],
    valid: Optional[Sequence[bool]] = None,
    quality: str = "archive",
    derivative_sensitive: bool = False,
) -> List[SensorSample]:
    """Convert an already-read FAIR-MAST series into Worldshepherd samples.

    Reading Zarr arrays is intentionally kept outside this core adapter so
    archive access cannot be confused with control authority.  Callers provide
    arrays/series, and this function performs source-policy checks, shape
    checks, and provenance attachment.
    """

    policy_ok, policy_reason = FairMastQualityPolicy.evaluate(
        source,
        derivative_sensitive=derivative_sensitive,
    )
    if not policy_ok:
        raise ValueError(policy_reason)

    if not unit.strip():
        raise ValueError("unit_missing")
    if not quality.strip():
        raise ValueError("quality_missing")
    if len(timestamps) != len(values):
        raise ValueError("timestamp_value_length_mismatch")
    count = len(values)
    if count == 0:
        return []

    uncertainties = _expand_uncertainty(uncertainty, count)
    validity = [True] * count if valid is None else [bool(value) for value in valid]
    if len(validity) != count:
        raise ValueError("validity_length_mismatch")

    samples: List[SensorSample] = []
    previous_ts: Optional[float] = None
    for index, (timestamp, value, sample_uncertainty, is_valid) in enumerate(
        zip(timestamps, values, uncertainties, validity)
    ):
        ts = float(timestamp)
        sample_value = float(value)
        if not math.isfinite(ts):
            raise ValueError(f"timestamp_not_finite:{index}")
        if previous_ts is not None and ts < previous_ts:
            raise ValueError(f"timestamp_not_monotonic:{index}")
        previous_ts = ts

        sample = SensorSample(
            timestamp=ts,
            shot_id=str(int(source.shot_id)),
            diagnostic=source.diagnostic_name,
            value=sample_value,
            unit=unit,
            uncertainty=sample_uncertainty,
            valid=is_valid and math.isfinite(sample_value),
            quality=f"{quality};fair-mast-{source.level}",
            provenance=source.provenance_for_index(index),
        )
        ok, reason = sample.validate()
        if not ok and reason != "sensor_invalid":
            raise ValueError(f"sample_invalid:{index}:{reason}")
        samples.append(sample)

    return samples
