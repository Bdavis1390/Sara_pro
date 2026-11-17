"""BAROS Phase I comparator scoring for predeclared synthetic research scenarios.

RESEARCH ONLY. The labels are supplied by a fixture author, not inferred from
patients, a commissioned treatment-planning system, or observed clinical harm.
These scores measure agreement with a synthetic decision policy ONLY.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Literal, Sequence

from baros.closed_loop import (
    AdaptationThresholds,
    BiologicalState,
    decide_adaptation,
)

Truth = Literal["qualified_trigger", "disqualified_trigger", "no_trigger"]


@dataclass(frozen=True)
class PredeclaredCase:
    case_id: str
    truth: Truth
    previous: BiologicalState
    current: BiologicalState


@dataclass(frozen=True)
class Rate:
    numerator: int
    denominator: int
    wilson_low: float
    wilson_high: float

    @property
    def value(self) -> float:
        return self.numerator / self.denominator


@dataclass(frozen=True)
class ComparatorScores:
    strategy: str
    critical_false_proceed: Rate
    eligible_proposal_recall: Rate
    spurious_proposals_without_trigger: Rate


@dataclass(frozen=True)
class BenchmarkReport:
    cases: int
    eligible_cases: int
    disqualified_cases: int
    no_trigger_cases: int
    results: tuple[ComparatorScores, ...]
    treatment_authority_ever_granted: bool


def _rate(numerator: int, denominator: int) -> Rate:
    """A descriptive 95% Wilson interval, NOT a clinical confidence bound."""
    if denominator <= 0:
        raise ValueError("all three reference-label strata must be non-empty")
    if not 0 <= numerator <= denominator:
        raise ValueError("invalid numerator")
    z = 1.959963984540054
    p = numerator / denominator
    z2 = z * z
    denom = 1 + z2 / denominator
    center = (p + z2 / (2 * denominator)) / denom
    half = z * sqrt((p * (1 - p) / denominator) + z2 / (4 * denominator**2)) / denom
    return Rate(numerator, denominator, max(0.0, center - half), min(1.0, center + half))


def evaluate_cases(
    cases: Sequence[PredeclaredCase],
    thresholds: AdaptationThresholds,
) -> BenchmarkReport:
    """Score the exact same frozen synthetic cases under three policies.

    Comparators:
      gated: current BAROS decision contract.
      trigger_only: allow any triggered proposal, ignoring data qualification.
      quality_only: synthetic quality / uncertainty / OOD gate; NO geometry or
          identifiability check. This is a deliberately limited heuristic,
          NOT a published/vendor implementation.
      abstain_all: never allow a proposal (trivially safe but not useful).
    """
    cases = tuple(cases)
    if not cases or any(not c.case_id.strip() for c in cases):
        raise ValueError("require non-empty, named cases")
    if len({c.case_id for c in cases}) != len(cases):
        raise ValueError("case IDs must be unique")
    expected = {"qualified_trigger", "disqualified_trigger", "no_trigger"}
    if {c.truth for c in cases} != expected:
        raise ValueError("require non-empty qualified, disqualified, and no-trigger strata")

    decisions = []
    for c in cases:
        decision = decide_adaptation(
            previous=c.previous,
            current=c.current,
            thresholds=thresholds,
            last_valid_plan_identity="FROZEN-LAST-VALID",
            standard_plan_identity="FROZEN-STANDARD",
        )
        decisions.append(decision)
    is_triggered = tuple(d.triggered for d in decisions)
    quality_only = tuple(
        d.triggered
        and not c.current.out_of_distribution
        and c.current.measurement_quality >= thresholds.min_measurement_quality
        and max(c.current.uncertainty) <= thresholds.max_uncertainty
        for c, d in zip(cases, decisions)
    )
    proposals = (
        ("gated", tuple(d.proposal_allowed for d in decisions)),
        ("trigger_only", is_triggered),
        ("quality_only", quality_only),
        ("abstain_all", (False,) * len(decisions)),
    )
    results = []
    for name, predictions in proposals:
        unsafe = [(c, p) for c, p in zip(cases, predictions) if c.truth == "disqualified_trigger"]
        eligible = [(c, p) for c, p in zip(cases, predictions) if c.truth == "qualified_trigger"]
        no_trigger = [(c, p) for c, p in zip(cases, predictions) if c.truth == "no_trigger"]
        results.append(
            ComparatorScores(
                strategy=name,
                critical_false_proceed=_rate(sum(p for _, p in unsafe), len(unsafe)),
                eligible_proposal_recall=_rate(sum(p for _, p in eligible), len(eligible)),
                spurious_proposals_without_trigger=_rate(sum(p for _, p in no_trigger), len(no_trigger)),
            )
        )
    return BenchmarkReport(
        cases=len(cases),
        eligible_cases=sum(c.truth == "qualified_trigger" for c in cases),
        disqualified_cases=sum(c.truth == "disqualified_trigger" for c in cases),
        no_trigger_cases=sum(c.truth == "no_trigger" for c in cases),
        results=tuple(results),
        treatment_authority_ever_granted=any(d.treatment_authority for d in decisions),
    )
