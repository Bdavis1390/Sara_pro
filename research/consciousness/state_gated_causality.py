from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence

@dataclass(frozen=True)
class PreState:
    state_id: str
    metrics: Mapping[str, float]
    confidence: float

    def validate(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be in [0,1]")

@dataclass(frozen=True)
class Intervention:
    intervention_id: str
    target: str
    stimulus_signature: str
    timing_ms: float | None = None
    phase_rad: float | None = None
    intensity: float | None = None

@dataclass(frozen=True)
class Trial:
    pre_state: PreState
    intervention: Intervention
    response: float

def variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / (len(values) - 1)

def variability_reduction(
    ungated_responses: Sequence[float],
    gated_responses: Sequence[float],
) -> float:
    base = variance(ungated_responses)
    gated = variance(gated_responses)
    if base == 0:
        return 0.0
    return (base - gated) / base

def classify_uncertainty(
    predictive_gain_from_state: float,
    prospective_variance_reduction: float,
    minimum_gain: float = 0.05,
) -> str:
    if predictive_gain_from_state >= minimum_gain and prospective_variance_reduction > 0:
        return "PARTLY_EPISTEMIC_HIDDEN_STATE"
    if predictive_gain_from_state >= minimum_gain:
        return "STATE_PREDICTIVE_NOT_YET_CAUSALLY_GATED"
    return "IRREDUCIBLE_OR_UNRESOLVED"

def stimulation_gate(
    state: PreState,
    required_state_confidence: float,
    authorized: bool,
    safety_ok: bool,
) -> str:
    state.validate()
    if not authorized:
        return "BLOCK_UNAUTHORIZED"
    if not safety_ok:
        return "BLOCK_SAFETY"
    if state.confidence < required_state_confidence:
        return "WAIT_FOR_BETTER_STATE_ESTIMATE"
    return "ELIGIBLE_FOR_SUPERVISED_STATE_GATED_PROTOCOL"
