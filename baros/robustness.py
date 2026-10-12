"""Deterministic finite-scenario robustness evaluation for BAROS research.

NON-CLINICAL. Scenarios are explicit numerical perturbations supplied by the
caller. This module does not assert that any scenario distribution represents
clinical uncertainty unless separately justified and validated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .dose import dose_from_influence, hard_max_constraints
from .reference_optimizer import tumor_survival_objective


@dataclass(frozen=True)
class RobustScenarioResult:
    name: str
    dose_gy: tuple[float, ...]
    tumor_survival_objective: float
    hard_constraints_satisfied: bool
    constraint_failures: tuple[str, ...]


@dataclass(frozen=True)
class RobustnessSummary:
    scenarios: tuple[RobustScenarioResult, ...]
    worst_objective_scenario: str
    worst_tumor_survival_objective: float
    all_hard_constraints_satisfied: bool


def scale_influence(
    influence: Sequence[Sequence[float]],
    scale: float,
) -> tuple[tuple[float, ...], ...]:
    """Create an explicitly declared multiplicative synthetic dose scenario."""
    factor = float(scale)
    if factor <= 0.0:
        raise ValueError("scale must be positive")
    return tuple(tuple(float(value) * factor for value in row) for row in influence)


def evaluate_robustness(
    *,
    weights: Sequence[float],
    influence_scenarios: Mapping[str, Sequence[Sequence[float]]],
    tumor_voxels: Sequence[int],
    alpha_per_gy: Sequence[float],
    beta_per_gy2: Sequence[float],
    hard_max_gy: dict[int, float],
) -> RobustnessSummary:
    """Evaluate one fixed solution across explicit finite uncertainty scenarios.

    The robust gate passes only when every supplied scenario satisfies all hard
    maximum-dose constraints. The biological objective is reported worst-case
    as the largest mean surviving-fraction objective because BAROS minimizes it.
    """
    if not influence_scenarios:
        raise ValueError("at least one influence scenario is required")

    results: list[RobustScenarioResult] = []
    for name, influence in sorted(influence_scenarios.items()):
        if not str(name).strip():
            raise ValueError("scenario names must be non-empty")
        dose = dose_from_influence(weights, influence)
        objective = tumor_survival_objective(
            dose,
            tumor_voxels,
            alpha_per_gy,
            beta_per_gy2,
        )
        feasible, failures = hard_max_constraints(dose, hard_max_gy)
        results.append(
            RobustScenarioResult(
                name=str(name),
                dose_gy=tuple(dose),
                tumor_survival_objective=objective,
                hard_constraints_satisfied=feasible,
                constraint_failures=tuple(failures),
            )
        )

    worst = max(results, key=lambda item: item.tumor_survival_objective)
    return RobustnessSummary(
        scenarios=tuple(results),
        worst_objective_scenario=worst.name,
        worst_tumor_survival_objective=worst.tumor_survival_objective,
        all_hard_constraints_satisfied=all(item.hard_constraints_satisfied for item in results),
    )
