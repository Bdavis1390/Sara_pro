"""Bounded dose-volume histogram utilities for BAROS research verification.

NON-CLINICAL. These functions operate on numerical dose arrays and masks only.
They do not establish contour correctness, dose-engine accuracy, clinical
constraint validity, or patient-care suitability.

Metric semantics follow the AAPM TG-263 convention used by BAROS:
- Vx: volume receiving dose >= x
- Dx%: minimum dose received by the hottest x percent of structure volume

For discrete equally weighted voxels, Dx% is evaluated as an empirical weighted
quantile using a conservative nearest-rank convention documented below.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class DVHSummary:
    voxel_count: int
    total_volume_cc: float | None
    dmin_gy: float
    dmean_gy: float
    dmedian_gy: float
    dmax_gy: float


def _dose_values(dose_gy: np.ndarray | Sequence[float], mask: np.ndarray | None = None) -> np.ndarray:
    dose = np.asarray(dose_gy, dtype=np.float64)
    if dose.size == 0:
        raise ValueError("dose array must be non-empty")
    if not np.all(np.isfinite(dose)):
        raise ValueError("dose array must contain only finite values")
    if np.any(dose < 0.0):
        raise ValueError("dose array must be non-negative")

    if mask is None:
        values = dose.reshape(-1)
    else:
        m = np.asarray(mask)
        if m.shape != dose.shape:
            raise ValueError("mask shape must match dose shape")
        if m.dtype != np.bool_:
            if not np.all(np.isin(m, [0, 1])):
                raise ValueError("mask must be boolean or contain only 0/1")
            m = m.astype(bool)
        values = dose[m]

    if values.size == 0:
        raise ValueError("selected structure contains no voxels")
    return values.astype(np.float64, copy=False)


def _voxel_volume(voxel_volume_cc: float | None) -> float | None:
    if voxel_volume_cc is None:
        return None
    value = float(voxel_volume_cc)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("voxel_volume_cc must be finite and positive")
    return value


def summarize_dose(
    dose_gy: np.ndarray | Sequence[float],
    *,
    mask: np.ndarray | None = None,
    voxel_volume_cc: float | None = None,
) -> DVHSummary:
    """Return exact numerical summary over selected voxels."""
    values = _dose_values(dose_gy, mask)
    voxel_cc = _voxel_volume(voxel_volume_cc)
    return DVHSummary(
        voxel_count=int(values.size),
        total_volume_cc=None if voxel_cc is None else float(values.size * voxel_cc),
        dmin_gy=float(np.min(values)),
        dmean_gy=float(np.mean(values)),
        dmedian_gy=float(np.median(values)),
        dmax_gy=float(np.max(values)),
    )


def volume_at_least(
    dose_gy: np.ndarray | Sequence[float],
    threshold_gy: float,
    *,
    mask: np.ndarray | None = None,
    voxel_volume_cc: float | None = None,
    output: str = "percent",
) -> float:
    """Compute TG-263-style Vx: volume receiving >= threshold dose.

    `output='percent'` returns percentage of selected volume.
    `output='cc'` requires a positive voxel_volume_cc and returns absolute volume.
    """
    values = _dose_values(dose_gy, mask)
    threshold = float(threshold_gy)
    if not math.isfinite(threshold) or threshold < 0.0:
        raise ValueError("threshold_gy must be finite and non-negative")
    count = int(np.count_nonzero(values >= threshold))

    if output == "percent":
        return 100.0 * count / values.size
    if output == "cc":
        voxel_cc = _voxel_volume(voxel_volume_cc)
        if voxel_cc is None:
            raise ValueError("voxel_volume_cc is required for cc output")
        return float(count * voxel_cc)
    raise ValueError("output must be 'percent' or 'cc'")


def dose_to_hottest_percent(
    dose_gy: np.ndarray | Sequence[float],
    hottest_percent: float,
    *,
    mask: np.ndarray | None = None,
) -> float:
    """Compute Dx% using a conservative discrete nearest-rank convention.

    Dx% is the minimum dose received by the hottest x% of selected voxels.
    For N equal-volume voxels, k=ceil(x/100*N) voxels are included in the
    hottest subvolume and the returned value is the k-th largest dose.

    This avoids interpolation creating a dose not represented by any voxel and
    makes small synthetic fixtures exactly reproducible. Clinical comparison
    against a TPS must account for that TPS's DVH sampling/interpolation rules.
    """
    values = _dose_values(dose_gy, mask)
    pct = float(hottest_percent)
    if not math.isfinite(pct) or not (0.0 < pct <= 100.0):
        raise ValueError("hottest_percent must be within (0, 100]")
    k = max(1, int(math.ceil((pct / 100.0) * values.size)))
    ordered = np.sort(values)[::-1]
    return float(ordered[k - 1])


def cumulative_dvh(
    dose_gy: np.ndarray | Sequence[float],
    *,
    mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return an exact empirical cumulative DVH as dose points and volume %.

    Each dose point is a unique observed voxel dose. The corresponding volume
    percentage is the selected voxel fraction receiving that dose or more.
    """
    values = _dose_values(dose_gy, mask)
    dose_points = np.unique(np.sort(values))
    volume_percent = np.array(
        [100.0 * np.count_nonzero(values >= threshold) / values.size for threshold in dose_points],
        dtype=np.float64,
    )
    return dose_points, volume_percent
