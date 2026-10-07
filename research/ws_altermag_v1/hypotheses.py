from __future__ import annotations

import math

from .decompiler import fit_relaxation_only
from .schema import InferenceResult, Measurement


def _aic(n: int, k: int, sse: float) -> float:
    floor = 1.0e-30
    return n * math.log(max(sse, floor) / n) + 2.0 * k


def compare_am_vs_relaxation(
    measurements: list[Measurement],
    full: InferenceResult,
) -> dict[str, float | str | bool]:
    null = fit_relaxation_only(measurements)
    n = len(measurements)
    aic_full = _aic(n, 2, full.sse)
    aic_null = _aic(n, 1, null["sse"])
    delta_aic = aic_null - aic_full
    ratio = null["sse"] / max(full.sse, 1.0e-30)
    preferred = "H1_AM_PLUS_RELAXATION" if delta_aic >= 10.0 else "UNRESOLVED"
    return {
        "h0_sse": float(null["sse"]),
        "h1_sse": float(full.sse),
        "sse_ratio_h0_over_h1": float(ratio),
        "delta_aic_h0_minus_h1": float(delta_aic),
        "preferred": preferred,
        "decisive": bool(delta_aic >= 10.0),
    }
