from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping

class ViabilityDimension(str, Enum):
    EPISTEMIC_INTEGRITY = "EPISTEMIC_INTEGRITY"
    SAFETY = "SAFETY"
    AUTHORIZATION = "AUTHORIZATION"
    RESOURCE_BOUNDS = "RESOURCE_BOUNDS"
    TASK_INTEGRITY = "TASK_INTEGRITY"
    CALIBRATION = "CALIBRATION"

@dataclass(frozen=True)
class ViabilityState:
    values: Mapping[ViabilityDimension, float]

    def score(self, weights: Mapping[ViabilityDimension, float]) -> float:
        total_weight = sum(weights.values())
        if total_weight <= 0:
            raise ValueError("positive viability weights required")
        for value in self.values.values():
            if not 0 <= value <= 1:
                raise ValueError("viability components must be in [0,1]")
        return sum(
            weights.get(k, 0.0) * v
            for k, v in self.values.items()
        ) / total_weight

@dataclass(frozen=True)
class SemanticInterventionResult:
    channel: str
    actual_viability: float
    scrambled_viability: float
    semantic_value: float
    evidence_ref: str

def semantic_value(
    channel: str,
    actual_state: ViabilityState,
    scrambled_state: ViabilityState,
    weights: Mapping[ViabilityDimension, float],
    evidence_ref: str,
) -> SemanticInterventionResult:
    actual = actual_state.score(weights)
    scrambled = scrambled_state.score(weights)
    return SemanticInterventionResult(
        channel=channel,
        actual_viability=actual,
        scrambled_viability=scrambled,
        semantic_value=actual - scrambled,
        evidence_ref=evidence_ref,
    )

def classify_semantic_relevance(
    result: SemanticInterventionResult,
    material_threshold: float = 0.05,
) -> str:
    if result.semantic_value >= material_threshold:
        return "MATERIALLY_VIABILITY_RELEVANT"
    if result.semantic_value <= -material_threshold:
        return "MISLEADING_OR_HARMFUL_INFORMATION"
    return "NO_MATERIAL_VIABILITY_EFFECT_DETECTED"

def governed_action_gate(
    semantic_relevance: str,
    authorized: bool,
    evidence_current: bool,
) -> str:
    if not authorized:
        return "BLOCK_UNAUTHORIZED"
    if not evidence_current:
        return "BLOCK_STALE_EVIDENCE"
    if semantic_relevance == "MISLEADING_OR_HARMFUL_INFORMATION":
        return "BLOCK_OR_REEVALUATE_INFORMATION"
    return "ELIGIBLE_FOR_POLICY_EVALUATION"
