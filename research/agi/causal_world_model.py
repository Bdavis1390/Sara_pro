from __future__ import annotations
from dataclasses import dataclass, field
from math import log2, log
from typing import Mapping

def _effect_signature(effects: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(effects.items()))

@dataclass(frozen=True)
class CausalHypothesis:
    hypothesis_id: str
    action_effects: Mapping[str, Mapping[str, str]]
    evidence_refs: tuple[str, ...] = ()

    def predict(self, action_id: str) -> dict[str, str] | None:
        value = self.action_effects.get(action_id)
        return None if value is None else dict(value)

@dataclass
class CausalHypothesisSet:
    hypotheses: dict[str, CausalHypothesis]
    probabilities: dict[str, float]
    update_history: list[dict] = field(default_factory=list)

    def validate(self) -> None:
        if not self.hypotheses:
            raise ValueError("at least one causal hypothesis required")
        if set(self.hypotheses) != set(self.probabilities):
            raise ValueError("hypothesis/probability keys must match")
        if any(p < 0 for p in self.probabilities.values()):
            raise ValueError("probabilities must be nonnegative")
        total = sum(self.probabilities.values())
        if total <= 0:
            raise ValueError("probabilities must have positive mass")
        for key in list(self.probabilities):
            self.probabilities[key] /= total

    def entropy_bits(self) -> float:
        self.validate()
        return -sum(
            p * log2(p)
            for p in self.probabilities.values()
            if p > 0
        )

    def predictive_distribution(
        self,
        action_id: str,
    ) -> dict[tuple[tuple[str, str], ...], float]:
        self.validate()
        out: dict[tuple[tuple[str, str], ...], float] = {}
        for hid, hypothesis in self.hypotheses.items():
            prediction = hypothesis.predict(action_id)
            signature = _effect_signature(prediction or {"__unknown__":"1"})
            out[signature] = out.get(signature, 0.0) + self.probabilities[hid]
        return out

    def expected_information_gain_bits(self, action_id: str) -> float:
        self.validate()
        prior_entropy = self.entropy_bits()
        groups: dict[tuple[tuple[str, str], ...], list[str]] = {}
        for hid, hypothesis in self.hypotheses.items():
            signature = _effect_signature(
                hypothesis.predict(action_id) or {"__unknown__":"1"}
            )
            groups.setdefault(signature, []).append(hid)

        expected_posterior_entropy = 0.0
        for members in groups.values():
            mass = sum(self.probabilities[h] for h in members)
            if mass <= 0:
                continue
            posterior = [
                self.probabilities[h] / mass
                for h in members
                if self.probabilities[h] > 0
            ]
            entropy = -sum(p * log2(p) for p in posterior)
            expected_posterior_entropy += mass * entropy
        return prior_entropy - expected_posterior_entropy

    def update(
        self,
        action_id: str,
        observed_effects: Mapping[str, str],
        match_likelihood: float = 0.95,
        mismatch_likelihood: float = 0.05,
    ) -> None:
        if not 0 < mismatch_likelihood < match_likelihood < 1:
            raise ValueError("likelihoods must satisfy 0 < mismatch < match < 1")
        self.validate()
        observed_signature = _effect_signature(observed_effects)
        weights: dict[str, float] = {}
        for hid, hypothesis in self.hypotheses.items():
            predicted = hypothesis.predict(action_id)
            predicted_signature = _effect_signature(
                predicted or {"__unknown__":"1"}
            )
            likelihood = (
                match_likelihood
                if predicted_signature == observed_signature
                else mismatch_likelihood
            )
            weights[hid] = self.probabilities[hid] * likelihood

        z = sum(weights.values())
        if z <= 0:
            raise ValueError("posterior normalization failed")
        self.probabilities = {hid:w/z for hid,w in weights.items()}
        self.update_history.append({
            "action_id": action_id,
            "observed_effects": dict(observed_effects),
            "posterior": dict(self.probabilities),
        })

    def predictive_probability(
        self,
        action_id: str,
        observed_effects: Mapping[str, str],
    ) -> float:
        signature = _effect_signature(observed_effects)
        return self.predictive_distribution(action_id).get(signature, 0.0)

    def surprise_nats(
        self,
        action_id: str,
        observed_effects: Mapping[str, str],
        floor: float = 1e-12,
    ) -> float:
        p = max(floor, self.predictive_probability(action_id, observed_effects))
        return -log(p)

    def best_hypothesis(self) -> tuple[str, float]:
        self.validate()
        return max(self.probabilities.items(), key=lambda kv: kv[1])
