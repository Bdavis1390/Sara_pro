"""BAROS bounded research reference models.

NON-CLINICAL: This module exists for deterministic verification of mathematical
building blocks only. It must not be used for patient care or treatment planning.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def _finite_nonnegative(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return value


def lq_survival(dose_gy: float, alpha_per_gy: float, beta_per_gy2: float) -> float:
    """Linear-quadratic surviving fraction exp(-alpha D - beta D^2)."""
    d = _finite_nonnegative("dose_gy", dose_gy)
    a = _finite_nonnegative("alpha_per_gy", alpha_per_gy)
    b = _finite_nonnegative("beta_per_gy2", beta_per_gy2)
    return math.exp(-(a * d + b * d * d))


def poisson_tcp(clonogen_counts: Sequence[float], surviving_fractions: Sequence[float]) -> float:
    """Poisson TCP reference: exp(-sum(N_i * S_i))."""
    if len(clonogen_counts) != len(surviving_fractions) or not clonogen_counts:
        raise ValueError("clonogen_counts and surviving_fractions must have the same non-zero length")
    expected_survivors = 0.0
    for n, s in zip(clonogen_counts, surviving_fractions):
        n = _finite_nonnegative("clonogen_count", n)
        s = float(s)
        if not math.isfinite(s) or not (0.0 <= s <= 1.0):
            raise ValueError("surviving_fraction must be finite and within [0, 1]")
        expected_survivors += n * s
    return math.exp(-expected_survivors)


def logistic_ntcp(effective_dose_gy: float, d50_gy: float, slope_per_gy: float) -> float:
    """Bounded sigmoid NTCP reference model used only for numerical checks."""
    d = _finite_nonnegative("effective_dose_gy", effective_dose_gy)
    d50 = _finite_nonnegative("d50_gy", d50_gy)
    k = _finite_nonnegative("slope_per_gy", slope_per_gy)
    z = k * (d - d50)
    if z >= 0:
        e = math.exp(-z)
        return 1.0 / (1.0 + e)
    e = math.exp(z)
    return e / (1.0 + e)


def weighted_mean(values: Iterable[float], weights: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    wts = [float(w) for w in weights]
    if not vals or len(vals) != len(wts):
        raise ValueError("values and weights must have the same non-zero length")
    if any(not math.isfinite(v) for v in vals):
        raise ValueError("values must be finite")
    if any((not math.isfinite(w)) or w < 0.0 for w in wts):
        raise ValueError("weights must be finite and non-negative")
    total = sum(wts)
    if total <= 0.0:
        raise ValueError("sum(weights) must be positive")
    return sum(v * w for v, w in zip(vals, wts)) / total
