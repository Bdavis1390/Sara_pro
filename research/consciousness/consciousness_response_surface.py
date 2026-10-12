from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

class EvidenceClass(str, Enum):
    PREPRINT_SINGLE_ARM = "PREPRINT_SINGLE_ARM"
    PILOT_SINGLE_ARM = "PILOT_SINGLE_ARM"
    OBSERVATIONAL_LONGITUDINAL = "OBSERVATIONAL_LONGITUDINAL"
    RANDOMIZED_PILOT = "RANDOMIZED_PILOT"
    RANDOMIZED_CONFIRMATORY = "RANDOMIZED_CONFIRMATORY"

@dataclass(frozen=True)
class BrainState:
    state_id: str
    consciousness_score: float | None = None
    eeg_features: Mapping[str, float] | None = None
    metabolic_features: Mapping[str, float] | None = None
    network_features: Mapping[str, float] | None = None
    anatomy_ref: str | None = None

@dataclass(frozen=True)
class Perturbation:
    modality: str
    target: str
    carrier_hz: float | None = None
    envelope_hz: float | None = None
    amplitude: float | None = None
    duration_s: float | None = None
    field_geometry_ref: str | None = None
    sessions: int | None = None

@dataclass(frozen=True)
class TransitionObservation:
    before: BrainState
    perturbation: Perturbation
    after: BrainState
    evidence_class: EvidenceClass
    source_ref: str

    def consciousness_delta(self) -> float | None:
        if (
            self.before.consciousness_score is None
            or self.after.consciousness_score is None
        ):
            return None
        return self.after.consciousness_score - self.before.consciousness_score

def monotonic_activation_assumption_violated(
    consciousness_delta: float,
    metabolic_delta: float | None,
) -> bool:
    return (
        metabolic_delta is not None
        and consciousness_delta > 0
        and metabolic_delta < 0
    )

def fixed_frequency_is_underidentified(
    perturbation: Perturbation,
    baseline_state_known: bool,
) -> bool:
    return (
        perturbation.carrier_hz is not None
        and (
            not baseline_state_known
            or perturbation.target == ""
            or perturbation.field_geometry_ref is None
        )
    )

def eligible_for_adaptive_control(
    state_confidence: float,
    clinician_authorized: bool,
    safety_envelope_valid: bool,
    response_monitoring_available: bool,
) -> str:
    if not clinician_authorized:
        return "BLOCK_UNAUTHORIZED"
    if not safety_envelope_valid:
        return "BLOCK_OUTSIDE_SAFETY_ENVELOPE"
    if state_confidence < 0.8:
        return "MEASURE_STATE_FIRST"
    if not response_monitoring_available:
        return "OPEN_LOOP_ONLY_UNDER_PROTOCOL"
    return "ELIGIBLE_FOR_RESEARCH_CLOSED_LOOP_EVALUATION"
