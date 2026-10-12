from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

class EvidenceLevel(str, Enum):
    SIMULATION_ONLY = "SIMULATION_ONLY"
    RETRODICTION = "RETRODICTION"
    ORTHOGONAL_VALIDATION = "ORTHOGONAL_VALIDATION"
    PILOT_RANDOMIZED = "PILOT_RANDOMIZED"
    MULTICENTER_RANDOMIZED = "MULTICENTER_RANDOMIZED"
    CLINICAL_STANDARD = "CLINICAL_STANDARD"

class ValidationModality(str, Enum):
    EEG = "EEG"
    DTI = "DTI"
    RNA_SEQ = "RNA_SEQ"
    ELECTROPHYSIOLOGY = "ELECTROPHYSIOLOGY"
    BEHAVIOR = "BEHAVIOR"
    ANIMAL_MODEL = "ANIMAL_MODEL"
    PET = "PET"
    FMRI = "FMRI"

@dataclass(frozen=True)
class MechanismPrediction:
    prediction_id: str
    statement: str
    model_ref: str
    validations: tuple[ValidationModality, ...] = ()
    evidence_level: EvidenceLevel = EvidenceLevel.SIMULATION_ONLY

    def independent_validation_count(self) -> int:
        return len(set(self.validations))

    def claim_ceiling(self) -> str:
        if self.evidence_level == EvidenceLevel.SIMULATION_ONLY:
            return "HYPOTHESIS"
        if self.evidence_level == EvidenceLevel.RETRODICTION:
            return "MODEL_SUPPORTED_HYPOTHESIS"
        if self.independent_validation_count() >= 2:
            return "MULTIMODAL_MECHANISM_SUPPORT"
        if self.independent_validation_count() == 1:
            return "ORTHOGONALLY_SUPPORTED_HYPOTHESIS"
        return "HYPOTHESIS"

@dataclass(frozen=True)
class StimulationPattern:
    intervention_id: str
    carrier_hz: float | None = None
    intraburst_hz: float | None = None
    envelope_hz: float | None = None
    amplitude: float | None = None
    amplitude_unit: str | None = None
    target: str | None = None
    duration_s: float | None = None
    sessions: int | None = None
    field_geometry_ref: str | None = None
    evidence_level: EvidenceLevel = EvidenceLevel.SIMULATION_ONLY

    def is_frequency_only(self) -> bool:
        specified = [
            self.carrier_hz is not None,
            self.intraburst_hz is not None,
            self.envelope_hz is not None,
        ]
        contextual = [
            self.target,
            self.duration_s,
            self.field_geometry_ref,
            self.amplitude,
        ]
        return any(specified) and not any(x is not None for x in contextual)

    def claim_ceiling(self) -> str:
        if self.is_frequency_only():
            return "INSUFFICIENT_INTERVENTION_SPECIFICATION"
        if self.evidence_level == EvidenceLevel.PILOT_RANDOMIZED:
            return "PRELIMINARY_CAUSAL_CLINICAL_EVIDENCE"
        if self.evidence_level == EvidenceLevel.MULTICENTER_RANDOMIZED:
            return "RANDOMIZED_CLINICAL_EVIDENCE"
        return "MECHANISTIC_OR_PRECLINICAL_EVIDENCE"

def closed_loop_candidate(
    current_state_confidence: float,
    safety_envelope_valid: bool,
    evidence_current: bool,
    authorized: bool,
) -> str:
    if not authorized:
        return "BLOCK_UNAUTHORIZED"
    if not safety_envelope_valid:
        return "BLOCK_OUTSIDE_SAFETY_ENVELOPE"
    if not evidence_current:
        return "BLOCK_STALE_EVIDENCE"
    if current_state_confidence < 0.8:
        return "MEASURE_MORE_BEFORE_PERTURBING"
    return "ELIGIBLE_FOR_CLINICAL_PROTOCOL_EVALUATION"
