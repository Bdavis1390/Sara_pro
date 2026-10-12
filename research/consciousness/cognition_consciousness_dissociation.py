from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

class CapabilityAxis(str, Enum):
    PROCESSING = "PROCESSING"
    SEMANTICS = "SEMANTICS"
    LEARNING = "LEARNING"
    PREDICTION = "PREDICTION"
    AGENCY = "AGENCY"
    GLOBAL_INTEGRATION = "GLOBAL_INTEGRATION"
    CONSCIOUSNESS_EVIDENCE = "CONSCIOUSNESS_EVIDENCE"

@dataclass(frozen=True)
class CognitiveProfile:
    scores: Mapping[CapabilityAxis, float]

    def validate(self) -> None:
        for score in self.scores.values():
            if not 0 <= score <= 1:
                raise ValueError("scores must be in [0,1]")

    def score(self, axis: CapabilityAxis) -> float:
        self.validate()
        return self.scores.get(axis, 0.0)

def consciousness_inference_gate(profile: CognitiveProfile) -> str:
    profile.validate()

    capability_axes = [
        CapabilityAxis.PROCESSING,
        CapabilityAxis.SEMANTICS,
        CapabilityAxis.LEARNING,
        CapabilityAxis.PREDICTION,
        CapabilityAxis.AGENCY,
    ]
    capability = max(profile.score(axis) for axis in capability_axes)
    consciousness_evidence = profile.score(
        CapabilityAxis.CONSCIOUSNESS_EVIDENCE
    )

    if capability >= 0.8 and consciousness_evidence < 0.5:
        return "HIGH_CAPABILITY_DOES_NOT_ESTABLISH_CONSCIOUSNESS"

    if consciousness_evidence >= 0.8:
        return "CONSCIOUSNESS_HYPOTHESIS_REQUIRES_THEORY_SPECIFIC_VALIDATION"

    return "INSUFFICIENT_FOR_CONSCIOUSNESS_INFERENCE"

def local_semantics_global_access_dissociation(
    semantic_score: float,
    global_integration_score: float,
) -> str:
    for value in (semantic_score, global_integration_score):
        if not 0 <= value <= 1:
            raise ValueError("scores must be in [0,1]")

    if semantic_score >= 0.7 and global_integration_score < 0.4:
        return "LOCAL_SEMANTIC_PROCESSING_WITH_LOW_GLOBAL_INTEGRATION"

    if semantic_score >= 0.7 and global_integration_score >= 0.7:
        return "SEMANTICS_AND_GLOBAL_INTEGRATION_BOTH_HIGH"

    return "NO_STRONG_DISSOCIATION_DETECTED"
