"""Identifiability and information-gain tools for BAROS translational research.

NON-CLINICAL. These utilities support experimental design and model scrutiny.
They do not establish that a biological model is clinically valid.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class IdentifiabilityAssessment:
    parameter_names: tuple[str, ...]
    observation_count: int
    parameter_count: int
    rank: int
    nullity: int
    singular_values: tuple[float, ...]
    condition_number: float
    locally_identifiable: bool
    weak_parameter_directions: tuple[tuple[float, ...], ...]


def assess_local_identifiability(
    jacobian: Sequence[Sequence[float]],
    *,
    parameter_names: Sequence[str],
    relative_rank_tolerance: float = 1e-10,
    condition_limit: float = 1e8,
) -> IdentifiabilityAssessment:
    """Assess local structural/practical identifiability from a sensitivity matrix.

    Rows represent observations and columns represent model parameters.
    Full column rank is necessary for local identifiability. A very large
    condition number is treated as weak practical identifiability.
    """
    j = np.asarray(jacobian, dtype=np.float64)
    names = tuple(str(name).strip() for name in parameter_names)
    if j.ndim != 2 or j.size == 0:
        raise ValueError("jacobian must be a non-empty 2D matrix")
    if j.shape[1] != len(names) or not names or any(not name for name in names):
        raise ValueError("parameter_names must match jacobian columns and be non-empty")
    if not np.all(np.isfinite(j)):
        raise ValueError("jacobian must contain only finite values")
    if not math.isfinite(relative_rank_tolerance) or relative_rank_tolerance <= 0.0:
        raise ValueError("relative_rank_tolerance must be finite and positive")
    if not math.isfinite(condition_limit) or condition_limit <= 1.0:
        raise ValueError("condition_limit must be finite and > 1")

    u, singular, vh = np.linalg.svd(j, full_matrices=True)
    del u
    max_s = float(np.max(singular)) if singular.size else 0.0
    threshold = relative_rank_tolerance * max(1.0, max_s)
    rank = int(np.count_nonzero(singular > threshold))
    parameter_count = j.shape[1]
    nullity = parameter_count - rank

    if rank == 0:
        condition = math.inf
    elif rank < parameter_count:
        condition = math.inf
    else:
        min_s = float(np.min(singular))
        condition = math.inf if min_s <= 0.0 else max_s / min_s

    weak: list[tuple[float, ...]] = []
    if nullity > 0:
        weak.extend(tuple(float(v) for v in row) for row in vh[rank:, :])
    elif condition > condition_limit and vh.size:
        weak.append(tuple(float(v) for v in vh[-1, :]))

    return IdentifiabilityAssessment(
        parameter_names=names,
        observation_count=j.shape[0],
        parameter_count=parameter_count,
        rank=rank,
        nullity=nullity,
        singular_values=tuple(float(v) for v in singular),
        condition_number=float(condition),
        locally_identifiable=(rank == parameter_count and condition <= condition_limit),
        weak_parameter_directions=tuple(weak),
    )


@dataclass(frozen=True)
class ExperimentCandidate:
    name: str
    sensitivity_rows: tuple[tuple[float, ...], ...]
    cost: float
    risk: float
    irreversibility: float = 0.0
    authorized: bool = True


@dataclass(frozen=True)
class ExperimentScore:
    name: str
    information_gain: float
    penalty: float
    utility: float
    authorized: bool


def _validate_covariance(covariance: np.ndarray) -> np.ndarray:
    cov = np.asarray(covariance, dtype=np.float64)
    if cov.ndim != 2 or cov.shape[0] != cov.shape[1] or cov.shape[0] == 0:
        raise ValueError("prior_covariance must be a non-empty square matrix")
    if not np.all(np.isfinite(cov)):
        raise ValueError("prior_covariance must be finite")
    if not np.allclose(cov, cov.T, atol=1e-12, rtol=0.0):
        raise ValueError("prior_covariance must be symmetric")
    eig = np.linalg.eigvalsh(cov)
    if np.min(eig) <= 0.0:
        raise ValueError("prior_covariance must be positive definite")
    return cov


def expected_information_gain(
    prior_covariance: Sequence[Sequence[float]],
    sensitivity_rows: Sequence[Sequence[float]],
    *,
    noise_variance: float,
) -> float:
    """Gaussian linearized EIG proxy: 0.5 log det(I + P H^T R^-1 H)."""
    prior = _validate_covariance(np.asarray(prior_covariance, dtype=np.float64))
    h = np.asarray(sensitivity_rows, dtype=np.float64)
    if h.ndim != 2 or h.shape[1] != prior.shape[0] or h.shape[0] == 0:
        raise ValueError("sensitivity_rows must be non-empty and match covariance dimension")
    if not np.all(np.isfinite(h)):
        raise ValueError("sensitivity_rows must be finite")
    noise = float(noise_variance)
    if not math.isfinite(noise) or noise <= 0.0:
        raise ValueError("noise_variance must be finite and positive")

    matrix = np.eye(prior.shape[0]) + prior @ (h.T @ h) / noise
    sign, logdet = np.linalg.slogdet(matrix)
    if sign <= 0 or not math.isfinite(float(logdet)):
        raise ValueError("information-gain matrix is not positive definite")
    return 0.5 * float(logdet)


def rank_validation_experiments(
    prior_covariance: Sequence[Sequence[float]],
    candidates: Sequence[ExperimentCandidate],
    *,
    noise_variance: float,
    cost_weight: float = 1.0,
    risk_weight: float = 1.0,
    irreversibility_weight: float = 1.0,
) -> tuple[ExperimentScore, ...]:
    """Rank authorized evidence-acquisition actions by EIG minus explicit penalties.

    Unauthorized candidates are retained in the output but receive -inf utility
    so an optimizer cannot silently choose them.
    """
    prior = _validate_covariance(np.asarray(prior_covariance, dtype=np.float64))
    if not candidates:
        raise ValueError("at least one experiment candidate is required")
    weights = (cost_weight, risk_weight, irreversibility_weight)
    if any((not math.isfinite(float(w))) or float(w) < 0.0 for w in weights):
        raise ValueError("penalty weights must be finite and non-negative")

    scored: list[ExperimentScore] = []
    for candidate in candidates:
        for name, value in (
            ("cost", candidate.cost),
            ("risk", candidate.risk),
            ("irreversibility", candidate.irreversibility),
        ):
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(f"{candidate.name} {name} must be finite and non-negative")
        gain = expected_information_gain(
            prior,
            candidate.sensitivity_rows,
            noise_variance=noise_variance,
        )
        penalty = (
            float(cost_weight) * float(candidate.cost)
            + float(risk_weight) * float(candidate.risk)
            + float(irreversibility_weight) * float(candidate.irreversibility)
        )
        utility = gain - penalty if candidate.authorized else -math.inf
        scored.append(
            ExperimentScore(
                name=candidate.name,
                information_gain=gain,
                penalty=penalty,
                utility=utility,
                authorized=bool(candidate.authorized),
            )
        )
    return tuple(sorted(scored, key=lambda item: item.utility, reverse=True))


@dataclass(frozen=True)
class ObservabilityControllabilityAssessment:
    observability_rank: int
    controllability_rank: int
    state_dimension: int
    observability_fraction: float
    controllability_fraction: float
    low_observability_high_control_hazard: bool


def assess_observability_controllability(
    observability_matrix: Sequence[Sequence[float]],
    controllability_matrix: Sequence[Sequence[float]],
    *,
    relative_rank_tolerance: float = 1e-10,
    low_observability_threshold: float = 0.5,
    high_controllability_threshold: float = 0.8,
) -> ObservabilityControllabilityAssessment:
    """Flag high-actuation / low-observability research configurations."""
    o = np.asarray(observability_matrix, dtype=np.float64)
    c = np.asarray(controllability_matrix, dtype=np.float64)
    if o.ndim != 2 or c.ndim != 2 or o.size == 0 or c.size == 0:
        raise ValueError("observability and controllability matrices must be non-empty 2D matrices")
    if o.shape[1] != c.shape[0]:
        raise ValueError("state dimension mismatch between observability and controllability matrices")
    if not np.all(np.isfinite(o)) or not np.all(np.isfinite(c)):
        raise ValueError("matrices must be finite")
    n = o.shape[1]
    o_rank = int(np.linalg.matrix_rank(o, tol=relative_rank_tolerance))
    c_rank = int(np.linalg.matrix_rank(c, tol=relative_rank_tolerance))
    o_fraction = o_rank / n
    c_fraction = c_rank / n
    hazard = o_fraction < low_observability_threshold and c_fraction >= high_controllability_threshold
    return ObservabilityControllabilityAssessment(
        observability_rank=o_rank,
        controllability_rank=c_rank,
        state_dimension=n,
        observability_fraction=o_fraction,
        controllability_fraction=c_fraction,
        low_observability_high_control_hazard=hazard,
    )
