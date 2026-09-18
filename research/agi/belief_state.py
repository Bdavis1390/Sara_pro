from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class BeliefState:
    probabilities: Mapping[str, float]

    def validate(self) -> None:
        if not self.probabilities:
            raise ValueError("belief states required")
        if any(p < 0 for p in self.probabilities.values()):
            raise ValueError("negative probability")
        if abs(sum(self.probabilities.values()) - 1.0) > 1e-9:
            raise ValueError("belief probabilities must sum to one")

def bayes_observation_update(
    prior: BeliefState,
    likelihood: Mapping[str, float],
) -> BeliefState:
    prior.validate()
    weighted = {
        state: p * likelihood.get(state, 0.0)
        for state, p in prior.probabilities.items()
    }
    z = sum(weighted.values())
    if z <= 0:
        raise ValueError("observation has zero likelihood under all states")
    posterior = BeliefState({
        state: value / z
        for state, value in weighted.items()
    })
    posterior.validate()
    return posterior

def entropy_bits(belief: BeliefState) -> float:
    from math import log2
    belief.validate()
    return -sum(
        p * log2(p)
        for p in belief.probabilities.values()
        if p > 0
    )
