from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from math import log, exp
from typing import Iterable

class EvidencePolarity(str, Enum):
    SUPPORTS = "SUPPORTS"
    AGAINST = "AGAINST"
    NONDETECTION = "NONDETECTION"
    INCONCLUSIVE = "INCONCLUSIVE"

@dataclass(frozen=True)
class ConsciousnessObservable:
    name: str
    polarity: EvidencePolarity
    log_likelihood_ratio: float
    sensitivity: float | None = None
    specificity: float | None = None
    motor_dependent: bool = False
    sensory_dependent: bool = False
    theory_dependent: bool = False
    evidence_ref: str | None = None

    def validate(self) -> None:
        for value in (self.sensitivity, self.specificity):
            if value is not None and not 0 <= value <= 1:
                raise ValueError("sensitivity/specificity must be in [0,1]")

def posterior_probability(
    prior: float,
    observations: Iterable[ConsciousnessObservable],
) -> float:
    if not 0 < prior < 1:
        raise ValueError("prior must be in (0,1)")
    odds_log = log(prior / (1 - prior))
    for obs in observations:
        obs.validate()
        if obs.polarity == EvidencePolarity.INCONCLUSIVE:
            continue
        if obs.polarity == EvidencePolarity.NONDETECTION:
            # A non-detection must not be treated as strong negative evidence
            # unless the measurement's sensitivity is explicitly known.
            if obs.sensitivity is None:
                continue
            scale = max(0.0, min(1.0, obs.sensitivity))
            odds_log += obs.log_likelihood_ratio * scale
        else:
            odds_log += obs.log_likelihood_ratio
    odds = exp(odds_log)
    return odds / (1 + odds)

def negative_behavior_is_not_absence(
    behavioral_response: bool,
    covert_command_following: bool | None,
) -> str:
    if behavioral_response:
        return "OVERT_RESPONSE_PRESENT"
    if covert_command_following is True:
        return "COGNITIVE_MOTOR_DISSOCIATION_COMPATIBLE"
    if covert_command_following is False:
        return "NO_COVERT_RESPONSE_DETECTED_NOT_PROOF_OF_ABSENCE"
    return "BEHAVIORAL_NONRESPONSE_REQUIRES_ADDITIONAL_EVIDENCE"

def theory_claim_ceiling(
    preregistered_critical_predictions_passed: int,
    preregistered_critical_predictions_failed: int,
) -> str:
    if preregistered_critical_predictions_failed > 0:
        return "THEORY_REQUIRES_REVISION_OR_NARROWING"
    if preregistered_critical_predictions_passed > 0:
        return "SUPPORTED_ON_TESTED_PREDICTIONS_NOT_ESTABLISHED"
    return "INSUFFICIENT_DISCRIMINATING_EVIDENCE"
