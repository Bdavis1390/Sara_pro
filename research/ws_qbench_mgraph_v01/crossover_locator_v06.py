"""WS-QBENCH-MGRAPH v0.6 zero-crossing utilities.

This module analyzes already-computed topology × scale curves. It applies to
both the reference-relative interaction I(r; r0) and the direct topology effect
E(r). It does not infer missing source-paper parameters and does not promote an
exact Figure 4 reproduction claim.

A zero is only reported when sampled adjacent target ratios bracket zero (or a
sample lands exactly on zero). Estimates use local linear interpolation; they
are not fitted critical exponents or phase-transition claims.
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


def _ordered_points(points: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    ordered = sorted((float(x), float(y)) for x, y in points)
    for (x0, _), (x1, _) in zip(ordered, ordered[1:]):
        if x1 <= x0:
            raise ValueError("target ratios must be unique")
    return ordered


def _interpolate(
    left: tuple[float, float],
    right: tuple[float, float],
) -> CrossoverEstimate | None:
    x0, y0 = left
    x1, y1 = right
    if x0 == x1:
        if y0 != 0.0:
            return None
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


def estimate_all_crossovers(
    points: Iterable[tuple[float, float]],
) -> list[CrossoverEstimate]:
    """Return every sampled/interpolated zero crossing in ascending-ratio order.

    Multiple results are intentionally preserved so re-entrant finite-model
    behavior cannot be collapsed into a single boundary.
    """
    ordered = _ordered_points(points)
    if not ordered:
        return []

    out: list[CrossoverEstimate] = []
    seen_exact: set[float] = set()
    for left, right in zip(ordered, ordered[1:]):
        x0, y0 = left
        _x1, y1 = right
        if y0 == 0.0 and x0 not in seen_exact:
            row = _interpolate(left, left)
            if row is not None:
                out.append(row)
            seen_exact.add(x0)
        if y0 * y1 < 0.0:
            row = _interpolate(left, right)
            if row is not None:
                out.append(row)

    x_last, y_last = ordered[-1]
    if y_last == 0.0 and x_last not in seen_exact:
        row = _interpolate(ordered[-1], ordered[-1])
        if row is not None:
            out.append(row)
    return out


def bracket_zero_crossing(
    points: Iterable[tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Return the first adjacent sign-changing or exact-zero bracket."""
    ordered = _ordered_points(points)
    for left, right in zip(ordered, ordered[1:]):
        if left[1] == 0.0:
            return left, left
        if right[1] == 0.0:
            return right, right
        if left[1] * right[1] < 0.0:
            return left, right
    if ordered and ordered[-1][1] == 0.0:
        return ordered[-1], ordered[-1]
    return None


def estimate_crossover(
    points: Iterable[tuple[float, float]],
) -> CrossoverEstimate | None:
    """Return the first zero crossing for backward-compatible single-root use."""
    rows = estimate_all_crossovers(points)
    return rows[0] if rows else None


def cutoff_consensus(estimates: Iterable[float]) -> dict[str, float | int]:
    """Summarize zero estimates across finite Fock cutoffs.

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
