"""Bounded adaptive/cumulative dose helpers for BAROS research.

NON-CLINICAL. Dose accumulation is permitted here only for grids declared and
verified to share the same frame, shape, origin, spacing, and orientation.
No deformable registration is performed or implied. Mismatched geometry fails
closed and requires an externally validated registration/resampling workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class DoseGridGeometry:
    frame_of_reference_uid: str
    shape: tuple[int, ...]
    origin_mm: tuple[float, ...]
    spacing_mm: tuple[float, ...]
    direction: tuple[float, ...]

    def validate(self) -> None:
        if not self.frame_of_reference_uid.strip():
            raise ValueError("frame_of_reference_uid must be non-empty")
        if not self.shape or any((not isinstance(v, int)) or v <= 0 for v in self.shape):
            raise ValueError("shape must contain positive integers")
        if len(self.origin_mm) != len(self.shape) or len(self.spacing_mm) != len(self.shape):
            raise ValueError("origin_mm and spacing_mm dimensionality must match shape")
        if len(self.direction) != len(self.shape) * len(self.shape):
            raise ValueError("direction must contain a square direction-cosine matrix")
        if any(not math.isfinite(float(v)) for v in self.origin_mm):
            raise ValueError("origin_mm must be finite")
        if any((not math.isfinite(float(v))) or float(v) <= 0.0 for v in self.spacing_mm):
            raise ValueError("spacing_mm must be finite and positive")
        if any(not math.isfinite(float(v)) for v in self.direction):
            raise ValueError("direction must be finite")


def _same_geometry(a: DoseGridGeometry, b: DoseGridGeometry, *, atol: float) -> bool:
    a.validate()
    b.validate()
    return (
        a.frame_of_reference_uid == b.frame_of_reference_uid
        and a.shape == b.shape
        and np.allclose(a.origin_mm, b.origin_mm, rtol=0.0, atol=atol)
        and np.allclose(a.spacing_mm, b.spacing_mm, rtol=0.0, atol=atol)
        and np.allclose(a.direction, b.direction, rtol=0.0, atol=atol)
    )


def accumulate_aligned_dose(
    dose_grids_gy: Sequence[np.ndarray],
    geometries: Sequence[DoseGridGeometry],
    *,
    geometry_tolerance_mm: float = 1e-6,
) -> np.ndarray:
    """Sum already aligned physical-dose grids after strict geometry checks.

    This function intentionally has no resampling/registration fallback. A
    mismatch raises ValueError so an external, independently validated spatial
    registration process must resolve it before BAROS can accumulate the dose.
    """
    if not dose_grids_gy or len(dose_grids_gy) != len(geometries):
        raise ValueError("dose_grids_gy and geometries must have the same non-zero length")
    tol = float(geometry_tolerance_mm)
    if not math.isfinite(tol) or tol < 0.0:
        raise ValueError("geometry_tolerance_mm must be finite and non-negative")

    reference_geometry = geometries[0]
    reference_geometry.validate()
    accumulated = np.zeros(reference_geometry.shape, dtype=np.float64)

    for index, (grid, geometry) in enumerate(zip(dose_grids_gy, geometries)):
        geometry.validate()
        if not _same_geometry(reference_geometry, geometry, atol=tol):
            raise ValueError(f"dose grid {index} geometry is not aligned with reference geometry")
        arr = np.asarray(grid, dtype=np.float64)
        if arr.shape != reference_geometry.shape:
            raise ValueError(f"dose grid {index} array shape does not match declared geometry")
        if not np.all(np.isfinite(arr)) or np.any(arr < 0.0):
            raise ValueError(f"dose grid {index} must be finite and non-negative")
        accumulated += arr

    if not np.all(np.isfinite(accumulated)):
        raise ValueError("accumulated dose contains non-finite values")
    return accumulated
