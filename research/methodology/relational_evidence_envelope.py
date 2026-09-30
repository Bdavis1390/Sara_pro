from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class Layer(str, Enum):
    CONTENT = "CONTENT"
    STRUCTURE = "STRUCTURE"
    RELATIONS = "RELATIONS"
    SEQUENCE = "SEQUENCE"
    STATE = "STATE"
    PROVENANCE = "PROVENANCE"
    TRANSFORMATIONS = "TRANSFORMATIONS"
    CONTEXT = "CONTEXT"
    INTERFACES = "INTERFACES"
    SCALE = "SCALE"
    MEASUREMENTS = "MEASUREMENTS"
    UNCERTAINTY = "UNCERTAINTY"
    DEPENDENCIES = "DEPENDENCIES"
    ALTERNATIVES = "ALTERNATIVES"
    FALSIFIERS = "FALSIFIERS"

@dataclass
class RelationalEvidenceEnvelope:
    object_id: str
    modality: str
    layers: dict[Layer, Any] = field(default_factory=dict)
    representation_loss: list[str] = field(default_factory=list)
    claim_state: list[str] = field(default_factory=list)

    def missing_layers(self) -> set[Layer]:
        return set(Layer) - set(self.layers)

    def layer_coverage(self) -> float:
        return len(self.layers) / len(Layer)

    def record_loss(self, note: str) -> None:
        if note.strip():
            self.representation_loss.append(note.strip())

    def consequential_ready(self) -> bool:
        required = {
            Layer.CONTENT,
            Layer.RELATIONS,
            Layer.PROVENANCE,
            Layer.UNCERTAINTY,
            Layer.DEPENDENCIES,
            Layer.ALTERNATIVES,
            Layer.FALSIFIERS,
        }
        return required.issubset(self.layers)

    def claim_ceiling(self) -> str:
        if not self.consequential_ready():
            return "OBSERVATION_OR_HYPOTHESIS_ONLY"
        if self.representation_loss:
            return "VALIDATION_REQUIRED_REPRESENTATION_LOSS"
        if Layer.MEASUREMENTS not in self.layers:
            return "STRUCTURED_INTERPRETATION_NO_QUANTITATIVE_VALIDATION"
        return "ELIGIBLE_FOR_DOMAIN_VALIDATION"

def compare_ablations(full: RelationalEvidenceEnvelope) -> list[dict[str, Any]]:
    ordered = [
        Layer.CONTENT,
        Layer.STRUCTURE,
        Layer.RELATIONS,
        Layer.SEQUENCE,
        Layer.PROVENANCE,
        Layer.CONTEXT,
        Layer.DEPENDENCIES,
    ]
    out = []
    present = set()
    for layer in ordered:
        if layer in full.layers:
            present.add(layer)
            out.append({
                "added_layer": layer.value,
                "active_layers": sorted(x.value for x in present),
                "coverage": len(present) / len(Layer),
            })
    return out

def nonflattening_violation(
    source_layers: set[Layer],
    derived_layers: set[Layer],
    disclosed_losses: set[Layer],
) -> set[Layer]:
    lost = source_layers - derived_layers
    return lost - disclosed_losses
