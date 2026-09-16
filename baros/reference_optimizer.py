"""Deterministic synthetic BAROS optimizer for G1/G2 research verification.

This implementation intentionally optimizes a small synthetic surrogate only.
It does not generate clinically deliverable plans and must not be used for patient care.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from .dose import dose_from_influence, hard_max_constraints
from .models import lq_survival


@dataclass(frozen=True)
class OptimizationResult:
    weights: tuple[float, ...]
    dose_gy: tuple[float, ...]
    objective: float
    iterations: int
    converged: bool


def tumor_survival_objective(
    dose_gy: Sequence[float],
    tumor_voxels: Sequence[int],
    alpha_per_gy: Sequence[float],
    beta_per_gy2: Sequence[float],
) -> float:
    if not tumor_voxels or not (len(tumor_voxels) == len(alpha_per_gy) == len(beta_per_gy2)):
        raise ValueError("tumor voxel/model arrays must have the same non-zero length")
    total = 0.0
    for idx, a, b in zip(tumor_voxels, alpha_per_gy, beta_per_gy2):
        if idx < 0 or idx >= len(dose_gy):
            raise ValueError(f"tumor voxel index out of range: {idx}")
        total += lq_survival(dose_gy[idx], a, b)
    return total / len(tumor_voxels)


def _gradient(
    weights: Sequence[float],
    influence: Sequence[Sequence[float]],
    tumor_voxels: Sequence[int],
    alpha_per_gy: Sequence[float],
    beta_per_gy2: Sequence[float],
) -> list[float]:
    dose = dose_from_influence(weights, influence)
    grad = [0.0] * len(weights)
    denom = float(len(tumor_voxels))
    for idx, a, b in zip(tumor_voxels, alpha_per_gy, beta_per_gy2):
        d = dose[idx]
        s = lq_survival(d, a, b)
        d_obj_d_dose = -(a + 2.0 * b * d) * s / denom
        for i, row in enumerate(influence):
            grad[i] += d_obj_d_dose * row[idx]
    return grad


def optimize_synthetic(
    *,
    influence: Sequence[Sequence[float]],
    tumor_voxels: Sequence[int],
    alpha_per_gy: Sequence[float],
    beta_per_gy2: Sequence[float],
    oar_max_gy: dict[int, float],
    initial_weights: Sequence[float],
    weight_max: float = 20.0,
    step_size: float = 2.0,
    max_iterations: int = 200,
    tolerance: float = 1e-10,
) -> OptimizationResult:
    if not math.isfinite(weight_max) or weight_max <= 0:
        raise ValueError("weight_max must be finite and positive")
    if not math.isfinite(step_size) or step_size <= 0:
        raise ValueError("step_size must be finite and positive")
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive")

    weights = [min(weight_max, max(0.0, float(w))) for w in initial_weights]
    if len(weights) != len(influence):
        raise ValueError("initial_weights must match influence rows")

    dose = dose_from_influence(weights, influence)
    feasible, failures = hard_max_constraints(dose, oar_max_gy)
    if not feasible:
        raise ValueError("initial plan violates hard constraints: " + "; ".join(failures))
    objective = tumor_survival_objective(dose, tumor_voxels, alpha_per_gy, beta_per_gy2)

    for iteration in range(1, max_iterations + 1):
        grad = _gradient(weights, influence, tumor_voxels, alpha_per_gy, beta_per_gy2)
        local_step = step_size
        accepted = False
        candidate_weights = weights
        candidate_dose = dose
        candidate_obj = objective

        for _ in range(30):
            proposal = [min(weight_max, max(0.0, w - local_step * g)) for w, g in zip(weights, grad)]
            proposal_dose = dose_from_influence(proposal, influence)
            feasible, _ = hard_max_constraints(proposal_dose, oar_max_gy)
            if feasible:
                proposal_obj = tumor_survival_objective(
                    proposal_dose, tumor_voxels, alpha_per_gy, beta_per_gy2
                )
                if proposal_obj <= objective + 1e-15:
                    candidate_weights = proposal
                    candidate_dose = proposal_dose
                    candidate_obj = proposal_obj
                    accepted = True
                    break
            local_step *= 0.5

        if not accepted:
            return OptimizationResult(tuple(weights), tuple(dose), objective, iteration - 1, True)

        improvement = objective - candidate_obj
        weights, dose, objective = candidate_weights, candidate_dose, candidate_obj
        if improvement <= tolerance:
            return OptimizationResult(tuple(weights), tuple(dose), objective, iteration, True)

    return OptimizationResult(tuple(weights), tuple(dose), objective, max_iterations, False)
