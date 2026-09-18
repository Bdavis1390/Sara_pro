"""Synthetic dose-influence operations for BAROS G1 verification.

NON-CLINICAL: This is not a treatment planning or dose calculation engine.
"""

from __future__ import annotations

import math
from typing import Sequence


def dose_from_influence(weights: Sequence[float], influence: Sequence[Sequence[float]]) -> list[float]:
    """Return voxel dose for a beamlet-by-voxel synthetic influence matrix."""
    if not weights or not influence or len(weights) != len(influence):
        raise ValueError("weights must match the number of influence rows")
    width = len(influence[0])
    if width == 0 or any(len(row) != width for row in influence):
        raise ValueError("influence must be a non-empty rectangular matrix")
    result = [0.0] * width
    for w, row in zip(weights, influence):
        w = float(w)
        if not math.isfinite(w) or w < 0.0:
            raise ValueError("weights must be finite and non-negative")
        for j, coeff in enumerate(row):
            coeff = float(coeff)
            if not math.isfinite(coeff) or coeff < 0.0:
                raise ValueError("influence coefficients must be finite and non-negative")
            result[j] += w * coeff
    return result


def hard_max_constraints(dose_gy: Sequence[float], limits_gy: dict[int, float]) -> tuple[bool, list[str]]:
    """Fail-closed maximum-dose constraints for selected synthetic voxels."""
    failures: list[str] = []
    for idx, limit in sorted(limits_gy.items()):
        if idx < 0 or idx >= len(dose_gy):
            failures.append(f"constraint voxel index out of range: {idx}")
            continue
        d = float(dose_gy[idx])
        lim = float(limit)
        if not math.isfinite(d) or not math.isfinite(lim) or lim < 0.0:
            failures.append(f"invalid constraint value at voxel {idx}")
            continue
        if d > lim + 1e-12:
            failures.append(f"voxel {idx} dose {d:.12g} exceeds max {lim:.12g}")
    return (not failures, failures)
