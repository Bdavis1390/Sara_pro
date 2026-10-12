"""BAROS wrapper around an independent gamma-index implementation.

NON-CLINICAL. Gamma analysis is a numerical comparison tool. A passing result
from this module is not a substitute for commissioned measurement-based QA,
clinical medical-physics review, or patient-specific treatment verification.

The implementation delegates gamma calculation to pinned PyMedPhys rather than
maintaining an unreviewed BAROS-specific gamma algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class GammaSummary:
    valid_points: int
    passing_points: int
    pass_rate_percent: float
    max_finite_gamma: float
    gamma: np.ndarray


def _validate_axes(axes: Sequence[Sequence[float]], shape: tuple[int, ...], label: str) -> tuple[np.ndarray, ...]:
    if len(axes) != len(shape):
        raise ValueError(f"{label} axes count must match dose dimensionality")
    validated: list[np.ndarray] = []
    for index, (axis, expected_length) in enumerate(zip(axes, shape)):
        arr = np.asarray(axis, dtype=np.float64)
        if arr.ndim != 1 or arr.size != expected_length:
            raise ValueError(f"{label} axis {index} length must match dose dimension")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{label} axis {index} must be finite")
        if arr.size > 1 and not np.all(np.diff(arr) > 0.0):
            raise ValueError(f"{label} axis {index} must be strictly increasing")
        validated.append(arr)
    return tuple(validated)


def _validate_dose(dose: np.ndarray | Sequence[float], label: str) -> np.ndarray:
    arr = np.asarray(dose, dtype=np.float64)
    if arr.ndim not in (1, 2, 3) or arr.size == 0:
        raise ValueError(f"{label} dose must be a non-empty 1D, 2D, or 3D array")
    if not np.all(np.isfinite(arr)) or np.any(arr < 0.0):
        raise ValueError(f"{label} dose must be finite and non-negative")
    return arr


def gamma_compare(
    *,
    axes_reference_mm: Sequence[Sequence[float]],
    dose_reference: np.ndarray | Sequence[float],
    axes_evaluation_mm: Sequence[Sequence[float]],
    dose_evaluation: np.ndarray | Sequence[float],
    dose_percent_threshold: float = 3.0,
    distance_mm_threshold: float = 2.0,
    lower_percent_dose_cutoff: float = 10.0,
    local_gamma: bool = False,
    global_normalisation: float | None = None,
    max_gamma: float = 2.0,
    interp_fraction: int = 10,
) -> GammaSummary:
    """Compare reference/evaluation dose grids via PyMedPhys gamma.

    Defaults are parameter values commonly associated with TG-218-style global
    gamma reporting, but no clinical acceptance decision is made by this
    function. Thresholds and acceptance limits must be governed by the relevant
    commissioned QA protocol and qualified medical physicists.
    """
    reference = _validate_dose(dose_reference, "reference")
    evaluation = _validate_dose(dose_evaluation, "evaluation")
    ref_axes = _validate_axes(axes_reference_mm, reference.shape, "reference")
    eval_axes = _validate_axes(axes_evaluation_mm, evaluation.shape, "evaluation")

    for name, value in (
        ("dose_percent_threshold", dose_percent_threshold),
        ("distance_mm_threshold", distance_mm_threshold),
        ("max_gamma", max_gamma),
    ):
        value = float(value)
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be finite and positive")
    cutoff = float(lower_percent_dose_cutoff)
    if not math.isfinite(cutoff) or not (0.0 <= cutoff < 100.0):
        raise ValueError("lower_percent_dose_cutoff must be within [0, 100)")
    if not isinstance(interp_fraction, int) or interp_fraction <= 0:
        raise ValueError("interp_fraction must be a positive integer")
    if global_normalisation is not None:
        norm = float(global_normalisation)
        if not math.isfinite(norm) or norm <= 0.0:
            raise ValueError("global_normalisation must be finite and positive")
    elif float(np.max(reference)) <= 0.0:
        raise ValueError("reference dose maximum must be positive when using automatic global normalisation")

    try:
        import pymedphys
    except ImportError as exc:  # pragma: no cover - explicit runtime boundary
        raise RuntimeError("PyMedPhys is required for BAROS gamma verification") from exc

    gamma = np.asarray(
        pymedphys.gamma(
            ref_axes,
            reference,
            eval_axes,
            evaluation,
            dose_percent_threshold=float(dose_percent_threshold),
            distance_mm_threshold=float(distance_mm_threshold),
            lower_percent_dose_cutoff=cutoff,
            interp_fraction=interp_fraction,
            max_gamma=float(max_gamma),
            local_gamma=bool(local_gamma),
            global_normalisation=global_normalisation,
            quiet=True,
        ),
        dtype=np.float64,
    )

    finite = np.isfinite(gamma)
    valid_points = int(np.count_nonzero(finite))
    if valid_points == 0:
        raise ValueError("gamma comparison produced no finite points above the configured cutoff")
    passing_points = int(np.count_nonzero(finite & (gamma <= 1.0)))
    finite_values = gamma[finite]
    return GammaSummary(
        valid_points=valid_points,
        passing_points=passing_points,
        pass_rate_percent=100.0 * passing_points / valid_points,
        max_finite_gamma=float(np.max(finite_values)),
        gamma=gamma,
    )
