from __future__ import annotations
from dataclasses import dataclass
from math import log2
from typing import Mapping, Sequence

@dataclass(frozen=True)
class HypothesisDistribution:
    probabilities: Mapping[str, float]

    def validate(self) -> None:
        if not self.probabilities:
            raise ValueError("hypotheses required")
        if any(p < 0 for p in self.probabilities.values()):
            raise ValueError("negative probability")
        if abs(sum(self.probabilities.values()) - 1.0) > 1e-9:
            raise ValueError("probabilities must sum to one")

    def entropy_bits(self) -> float:
        self.validate()
        return -sum(
            p * log2(p)
            for p in self.probabilities.values()
            if p > 0
        )

@dataclass(frozen=True)
class OutcomePosterior:
    probability: float
    posterior: HypothesisDistribution

@dataclass(frozen=True)
class CandidateAction:
    name: str
    outcomes: tuple[OutcomePosterior, ...]
    risk: float
    cost: float
    irreversibility: float
    authorized: bool = True

    def validate(self) -> None:
        if any(x < 0 for x in (self.risk, self.cost, self.irreversibility)):
            raise ValueError("risk/cost/irreversibility must be nonnegative")
        if abs(sum(o.probability for o in self.outcomes) - 1.0) > 1e-9:
            raise ValueError("outcome probabilities must sum to one")
        for outcome in self.outcomes:
            outcome.posterior.validate()

def expected_information_gain_bits(
    prior: HypothesisDistribution,
    action: CandidateAction,
) -> float:
    prior.validate()
    action.validate()
    expected_posterior_entropy = sum(
        o.probability * o.posterior.entropy_bits()
        for o in action.outcomes
    )
    return prior.entropy_bits() - expected_posterior_entropy

def bounded_epistemic_utility(
    prior: HypothesisDistribution,
    action: CandidateAction,
    risk_weight: float = 1.0,
    cost_weight: float = 1.0,
    irreversibility_weight: float = 1.0,
) -> float:
    if not action.authorized:
        return float("-inf")
    eig = expected_information_gain_bits(prior, action)
    return (
        eig
        - risk_weight * action.risk
        - cost_weight * action.cost
        - irreversibility_weight * action.irreversibility
    )

def choose_action(
    prior: HypothesisDistribution,
    actions: Sequence[CandidateAction],
) -> tuple[str, float]:
    if not actions:
        raise ValueError("candidate actions required")
    scored = [
        (a.name, bounded_epistemic_utility(prior, a))
        for a in actions
    ]
    return max(scored, key=lambda x: x[1])
