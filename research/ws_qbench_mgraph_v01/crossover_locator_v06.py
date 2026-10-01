"""WS-QBENCH-MGRAPH v0.6 crossover-location utilities.

This module analyzes already-computed paired topology × scale interaction
curves. It does not infer missing source-paper parameters and does not promote
an exact Figure 4 reproduction claim.

A crossover is only reported when adjacent sampled target ratios bracket zero.
The estimate is a local linear interpolation, not a fitted critical exponent or
phase-transition claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class CrossoverEstimate:
    lower_ratio: float
    upper_ratio: float
    lower_interaction: float
    upper_interaction: float
    estimated_ratio: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def bracket_zero_crossing(
    points: Iterable[tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Return the first adjacent sign-changing pair in ascending-ratio order."""
    ordered = sorted((float(x), float(y)) for x, y in points)
    if len(ordered) < 2:
        return None
    for left, right in zip(ordered, ordered[1:]):
        x0, y0 = left
        x1, y1 = right
        if x1 <= x0:
            raise ValueError("target ratios must be strictly increasing after sorting")
        if y0 == 0.0:
            return left, left
        if y1 == 0.0:
            return right, right
        if y0 * y1 < 0.0:
            return left, right
    return None


def estimate_crossover(
    points: Iterable[tuple[float, float]],
) -> CrossoverEstimate | None:
    """Estimate a zero crossing by linear interpolation inside a valid bracket."""
    bracket = bracket_zero_crossing(points)
    if bracket is None:
        return None
    (x0, y0), (x1, y1) = bracket
    if x0 == x1:
        root = x0
    else:
        denominator = y1 - y0
        if denominator == 0.0:
            return None
        root = x0 + (-y0) * (x1 - x0) / denominator
    return CrossoverEstimate(
        lower_ratio=x0,
        upper_ratio=x1,
        lower_interaction=y0,
        upper_interaction=y1,
        estimated_ratio=float(root),
    )


def cutoff_consensus(estimates: Iterable[float]) -> dict[str, float | int]:
    """Summarize crossover estimates across finite Fock cutoffs.

    This is descriptive only. The spread is retained as convergence evidence;
    it is not converted into a statistical confidence interval.
    """
    values = [float(value) for value in estimates]
    if not values:
        raise ValueError("at least one estimate is required")
    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "spread": max(values) - min(values),
    }
