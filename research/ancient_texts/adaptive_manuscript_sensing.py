from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class SensingAction(str, Enum):
    HANDHELD_XRF = "HANDHELD_XRF"
    XRF_MAPPING = "XRF_MAPPING"
    LAB_CT = "LAB_CT"
    SYNCHROTRON_CT = "SYNCHROTRON_CT"
    MULTISPECTRAL = "MULTISPECTRAL"
    DNA_NONDESTRUCTIVE = "DNA_NONDESTRUCTIVE"
    PROTEOMICS_NONDESTRUCTIVE = "PROTEOMICS_NONDESTRUCTIVE"
    HUMAN_REVIEW = "HUMAN_REVIEW"

@dataclass(frozen=True)
class ArtifactState:
    artifact_id: str
    carbonized: bool = False
    lead_detected: bool | None = None
    parchment: bool = False
    fragment_join_disputed: bool = False
    hidden_text: bool = False
    damage_risk: float = 0.0

def recommend_next_sensing(state: ArtifactState) -> list[SensingAction]:
    if not 0 <= state.damage_risk <= 1:
        raise ValueError("damage_risk must be in [0,1]")

    out: list[SensingAction] = []

    if state.carbonized and state.hidden_text and state.lead_detected is None:
        out.append(SensingAction.HANDHELD_XRF)

    if state.carbonized and state.hidden_text and state.lead_detected is True:
        out.extend([SensingAction.LAB_CT, SensingAction.XRF_MAPPING])

    if state.parchment and state.fragment_join_disputed:
        out.append(SensingAction.DNA_NONDESTRUCTIVE)

    if state.damage_risk > 0.5:
        out.append(SensingAction.HUMAN_REVIEW)

    return out

@dataclass(frozen=True)
class SyntheticPhantom:
    phantom_id: str
    hidden_text: str
    ink_composition: str
    carbonization_protocol: str
    scan_ref: str

    def ground_truth_available(self) -> bool:
        return bool(self.hidden_text and self.scan_ref)

def algorithm_validation_state(
    phantom: SyntheticPhantom,
    recovered_text: str,
) -> dict:
    if not phantom.ground_truth_available():
        return {"state":"NO_GROUND_TRUTH","exact":False}
    exact = recovered_text == phantom.hidden_text
    return {
        "state":"GROUND_TRUTH_COMPARISON",
        "exact":exact,
        "reference_length":len(phantom.hidden_text),
        "recovered_length":len(recovered_text),
    }
