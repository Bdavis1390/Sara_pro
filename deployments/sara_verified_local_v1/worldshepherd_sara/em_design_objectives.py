"""Multi-objective design utilities for Worldshepherd electromagnetic R&D.

The module deliberately avoids collapsing electromagnetic design quality into one
weighted scalar.  Candidates are compared by Pareto dominance so improvements in
one objective cannot silently compensate for regressions in another.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EMDesignMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    te_angle_observability: float = Field(ge=0.0)
    tm_phase_span_deg: float = Field(ge=0.0, le=360.0)
    polarization_isolation_dB: float = Field(ge=0.0)
    minimum_reflection_magnitude: float = Field(ge=0.0, le=1.0)
    te_state_crosstalk: float = Field(ge=0.0)
    tm_refinement_uncertainty: float = Field(ge=0.0)
    loss_proxy: float = Field(ge=0.0)


class EMDesignCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=128)
    design_version: str = Field(min_length=1, max_length=128)
    metrics: EMDesignMetrics
    evidence_refs: list[str] = Field(default_factory=list, max_length=64)
    validated: bool = False


_MAXIMIZE = (
    "te_angle_observability",
    "tm_phase_span_deg",
    "polarization_isolation_dB",
    "minimum_reflection_magnitude",
)

_MINIMIZE = (
    "te_state_crosstalk",
    "tm_refinement_uncertainty",
    "loss_proxy",
)


def dominates(a: EMDesignCandidate, b: EMDesignCandidate) -> bool:
    """Return True when *a* Pareto-dominates *b* across all registered objectives."""

    ma = a.metrics
    mb = b.metrics

    no_worse = all(getattr(ma, name) >= getattr(mb, name) for name in _MAXIMIZE)
    no_worse = no_worse and all(
        getattr(ma, name) <= getattr(mb, name) for name in _MINIMIZE
    )

    strictly_better = any(getattr(ma, name) > getattr(mb, name) for name in _MAXIMIZE)
    strictly_better = strictly_better or any(
        getattr(ma, name) < getattr(mb, name) for name in _MINIMIZE
    )

    return no_worse and strictly_better


def pareto_front(candidates: list[EMDesignCandidate]) -> list[EMDesignCandidate]:
    """Return the deterministic non-dominated candidate set.

    Input ordering is not used as a hidden preference; output is sorted by
    candidate_id for reproducibility.
    """

    front = [
        candidate
        for candidate in candidates
        if not any(
            other.candidate_id != candidate.candidate_id and dominates(other, candidate)
            for other in candidates
        )
    ]
    return sorted(front, key=lambda item: item.candidate_id)


def design_objective_contract() -> dict[str, object]:
    return {
        "selection_method": "PARETO_NON_DOMINANCE",
        "scalar_weighted_score": False,
        "maximize": list(_MAXIMIZE),
        "minimize": list(_MINIMIZE),
        "claims_boundary": [
            "OBJECTIVES_ARE_R_AND_D_DIRECTIONAL_PREFERENCES",
            "NO_NEW_UC06_ACCEPTANCE_THRESHOLD",
            "NO_CANDIDATE_VALIDATED_BY_PARETO_STATUS",
            "PALACE_OR_LATER_PHYSICAL_VALIDATION_REQUIRED",
        ],
    }
