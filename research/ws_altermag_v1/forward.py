from __future__ import annotations

import math
import numpy as np

from .schema import Measurement


def g_wave(theta_rad: float, phi_rad: float) -> float:
    """Dimensionless B1g-like synthetic basis: sin^3(theta) cos(theta) sin(3 phi)."""
    return (
        math.sin(theta_rad) ** 3
        * math.cos(theta_rad)
        * math.sin(3.0 * phi_rad)
    )


def coefficients(ef: float, theta_rad: float, phi_rad: float) -> tuple[float, float, float]:
    s = g_wave(theta_rad, phi_rad)
    baseline = 1.0 + 0.035 * ef + 0.012 * ef * ef
    c_am = (0.52 + 0.17 * ef) * s + 0.09 * s * s
    c_relax = 0.31 - 0.075 * ef + 0.04 * math.cos(theta_rad)
    return baseline, c_am, c_relax


def synthesize(
    *,
    amplitude: float,
    tau: float,
    grid: list[tuple[float, float, float]],
    sigma: float = 0.0025,
    seed: int = 9675,
) -> list[Measurement]:
    """Generate deterministic synthetic observables.

    amplitude and tau are hidden synthetic parameters. They are not physical CrSb values.
    """
    if tau <= 0:
        raise ValueError("tau must be positive")
    rng = np.random.default_rng(seed)
    out: list[Measurement] = []
    inv_tau = 1.0 / tau
    for ef, theta, phi in grid:
        baseline, c_am, c_relax = coefficients(ef, theta, phi)
        value = baseline + c_am * amplitude + c_relax * inv_tau
        value += float(rng.normal(0.0, sigma))
        out.append(Measurement(ef, theta, phi, value, sigma))
    return out
