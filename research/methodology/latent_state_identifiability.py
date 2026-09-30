from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

class IdentificationState(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    PARTIALLY_IDENTIFIED = "PARTIALLY_IDENTIFIED"
    EQUIVALENCE_CLASS_ONLY = "EQUIVALENCE_CLASS_ONLY"
    NONIDENTIFIABLE_WITH_CURRENT_OBSERVATIONS = "NONIDENTIFIABLE_WITH_CURRENT_OBSERVATIONS"
    UNKNOWN = "UNKNOWN"

class EvidenceAction(str, Enum):
    OBSERVE_NEW_MODALITY = "OBSERVE_NEW_MODALITY"
    INTERVENE = "INTERVENE"
    PERTURB = "PERTURB"
    WAIT_FOR_TEMPORAL_EVIDENCE = "WAIT_FOR_TEMPORAL_EVIDENCE"
    SEEK_NEW_WITNESS = "SEEK_NEW_WITNESS"
    NATURAL_EXPERIMENT = "NATURAL_EXPERIMENT"
    RETURN_TO_SOURCE = "RETURN_TO_SOURCE"
    REPORT_EQUIVALENCE_CLASS = "REPORT_EQUIVALENCE_CLASS"

@dataclass(frozen=True)
class LatentHypothesis:
    hypothesis_id: str
    predicted_observables: dict[str, str]
    predicted_interventions: dict[str, str] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()

@dataclass
class IdentificationProblem:
    target: str
    hypotheses: list[LatentHypothesis]
    observed: dict[str, str]
    interventions_available: list[str] = field(default_factory=list)

    def observational_equivalence_classes(self) -> list[set[str]]:
        groups: dict[tuple[tuple[str, str], ...], set[str]] = {}
        for h in self.hypotheses:
            signature = tuple(
                sorted(
                    (k, v)
                    for k, v in h.predicted_observables.items()
                    if k in self.observed
                )
            )
            groups.setdefault(signature, set()).add(h.hypothesis_id)
        return list(groups.values())

    def identification_state(self) -> IdentificationState:
        classes = self.observational_equivalence_classes()
        compatible = []
        for cls in classes:
            member = next(h for h in self.hypotheses if h.hypothesis_id in cls)
            if all(
                member.predicted_observables.get(k) == v
                for k, v in self.observed.items()
                if k in member.predicted_observables
            ):
                compatible.append(cls)

        if len(compatible) == 1 and len(compatible[0]) == 1:
            return IdentificationState.IDENTIFIED
        if len(compatible) == 1 and len(compatible[0]) > 1:
            return IdentificationState.EQUIVALENCE_CLASS_ONLY
        if len(compatible) > 1:
            return IdentificationState.NONIDENTIFIABLE_WITH_CURRENT_OBSERVATIONS
        return IdentificationState.UNKNOWN

    def discriminating_interventions(self) -> list[str]:
        candidates = []
        for intervention in self.interventions_available:
            predictions = {
                h.predicted_interventions.get(intervention)
                for h in self.hypotheses
                if intervention in h.predicted_interventions
            }
            if len(predictions) > 1:
                candidates.append(intervention)
        return candidates

def negative_observation_claim(
    detected: bool,
    sensitivity: float | None,
) -> str:
    if detected:
        return "TARGET_DETECTED"
    if sensitivity is None:
        return "NONDETECTION_ONLY"
    if not 0 <= sensitivity <= 1:
        raise ValueError("sensitivity must be in [0,1]")
    if sensitivity < 0.8:
        return "NONDETECTION_LOW_SENSITIVITY"
    return "NEGATIVE_EVIDENCE_WITH_KNOWN_SENSITIVITY"

def default_action_for_state(state: IdentificationState) -> EvidenceAction:
    if state == IdentificationState.IDENTIFIED:
        return EvidenceAction.REPORT_EQUIVALENCE_CLASS
    if state in {
        IdentificationState.EQUIVALENCE_CLASS_ONLY,
        IdentificationState.NONIDENTIFIABLE_WITH_CURRENT_OBSERVATIONS,
    }:
        return EvidenceAction.INTERVENE
    return EvidenceAction.OBSERVE_NEW_MODALITY
