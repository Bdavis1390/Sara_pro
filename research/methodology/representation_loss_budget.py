from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class Preservation(str, Enum):
    PRESERVED = "PRESERVED"
    APPROXIMATED = "APPROXIMATED"
    DISCARDED = "DISCARDED"
    ADDED_EXTERNAL = "ADDED_EXTERNAL"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class LayerDisposition:
    layer: str
    status: Preservation
    note: str | None = None

@dataclass
class RepresentationTransform:
    transform_id: str
    source_type: str
    representation_type: str
    reversible: bool
    dispositions: list[LayerDisposition] = field(default_factory=list)
    external_evidence_refs: list[str] = field(default_factory=list)

    def lost_layers(self) -> set[str]:
        return {
            d.layer for d in self.dispositions
            if d.status == Preservation.DISCARDED
        }

    def approximated_layers(self) -> set[str]:
        return {
            d.layer for d in self.dispositions
            if d.status == Preservation.APPROXIMATED
        }

    def added_layers(self) -> set[str]:
        return {
            d.layer for d in self.dispositions
            if d.status == Preservation.ADDED_EXTERNAL
        }

    def validate(self) -> None:
        if self.added_layers() and not self.external_evidence_refs:
            raise ValueError(
                "ADDED_EXTERNAL layers require provenance-bearing external evidence refs"
            )

    def claim_gate(self, required_layers: set[str]) -> dict:
        self.validate()
        lost = self.lost_layers() & required_layers
        approximate = self.approximated_layers() & required_layers
        if lost:
            return {
                "allowed": False,
                "state": "RETURN_TO_SOURCE_OR_CAP_CLAIM",
                "blocking_layers": sorted(lost),
                "approximate_layers": sorted(approximate),
            }
        if approximate:
            return {
                "allowed": True,
                "state": "ALLOW_WITH_UNCERTAINTY",
                "blocking_layers": [],
                "approximate_layers": sorted(approximate),
            }
        return {
            "allowed": True,
            "state": "REPRESENTATION_SUFFICIENT_FOR_DECLARED_LAYERS",
            "blocking_layers": [],
            "approximate_layers": [],
        }

def compose(a: RepresentationTransform, b: RepresentationTransform) -> RepresentationTransform:
    if a.representation_type != b.source_type:
        raise ValueError("transform types do not compose")
    status_order = {
        Preservation.PRESERVED: 0,
        Preservation.APPROXIMATED: 1,
        Preservation.DISCARDED: 2,
        Preservation.UNKNOWN: 3,
    }
    by_layer: dict[str, LayerDisposition] = {}
    for d in a.dispositions:
        by_layer[d.layer] = d
    for d in b.dispositions:
        prior = by_layer.get(d.layer)
        if d.status == Preservation.ADDED_EXTERNAL:
            by_layer[d.layer] = d
            continue
        if prior is None:
            by_layer[d.layer] = d
            continue
        if prior.status == Preservation.ADDED_EXTERNAL:
            if d.status == Preservation.DISCARDED:
                by_layer[d.layer] = d
            continue
        if status_order.get(d.status, 99) > status_order.get(prior.status, 99):
            by_layer[d.layer] = d
    return RepresentationTransform(
        transform_id=f"{a.transform_id}->{b.transform_id}",
        source_type=a.source_type,
        representation_type=b.representation_type,
        reversible=a.reversible and b.reversible,
        dispositions=list(by_layer.values()),
        external_evidence_refs=a.external_evidence_refs + b.external_evidence_refs,
    )
