from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

NODE_TYPES = {
    "Artifact", "Witness", "Glyph", "Motif", "Token", "Phrase", "TableCell",
    "SpatialRegion", "Translation", "Gloss", "Measurement", "Person",
    "Organization", "Place", "DateRange", "Hypothesis", "Experiment",
    "ClaimState", "Text", "Manuscript", "Inscription",
}

EDGE_TYPES = {
    "CONTAINS", "ADJACENT_TO", "ABOVE", "BELOW", "CROSSES",
    "WINDS_AROUND", "REPEATS", "VARIANT_OF", "COPIED_FROM",
    "TRANSLATED_AS", "GLOSSED_AS", "ASSOCIATED_WITH", "DOCUMENTED_BY",
    "RESEMBLES", "MEASURED_AS", "PREDICTS", "FALSIFIED_BY",
    "SUPPORTED_BY", "CONTRADICTED_BY", "PRECEDES", "POSSIBLE_TRANSMISSION",
}

@dataclass
class Node:
    id: str
    type: str
    attrs: dict[str, Any] = field(default_factory=dict)

@dataclass
class Edge:
    source: str
    target: str
    type: str
    evidence_refs: list[str] = field(default_factory=list)
    attrs: dict[str, Any] = field(default_factory=dict)

class EvidenceGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []

    def add_node(self, node: Node) -> None:
        if node.type not in NODE_TYPES:
            raise ValueError(f"invalid node type: {node.type}")
        if node.id in self.nodes:
            raise ValueError(f"duplicate node id: {node.id}")
        if node.type == "Measurement":
            for required in ("value", "unit", "uncertainty"):
                if required not in node.attrs:
                    raise ValueError(f"Measurement requires {required}")
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.type not in EDGE_TYPES:
            raise ValueError(f"invalid edge type: {edge.type}")
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError("edge endpoints must exist")
        if edge.type in {
            "TRANSLATED_AS", "GLOSSED_AS", "COPIED_FROM",
            "POSSIBLE_TRANSMISSION", "SUPPORTED_BY"
        } and not edge.evidence_refs:
            raise ValueError(f"{edge.type} requires explicit evidence_refs")
        if edge.type == "MEASURED_AS" and self.nodes[edge.target].type != "Measurement":
            raise ValueError("MEASURED_AS must target a Measurement node")
        self.edges.append(edge)

    def outgoing(self, node_id: str, edge_type: str | None = None) -> list[Edge]:
        return [
            e for e in self.edges
            if e.source == node_id and (edge_type is None or e.type == edge_type)
        ]

    def evidence_types(self, node_id: str) -> set[str]:
        return {e.type for e in self.outgoing(node_id)}

    def claim_ceiling(self, node_id: str) -> str:
        types = self.evidence_types(node_id)
        structural = {
            "RESEMBLES", "ADJACENT_TO", "ABOVE", "BELOW",
            "CROSSES", "WINDS_AROUND", "REPEATS"
        }
        if not types or types <= structural:
            return "HYPOTHESIS_OR_STRUCTURAL_CORRESPONDENCE"
        if "POSSIBLE_TRANSMISSION" in types and "DOCUMENTED_BY" not in types:
            return "POSSIBLE_HISTORICAL_LINK"
        if "TRANSLATED_AS" in types:
            return "TRANSLATION_REQUIRES_SCRIPT_LANGUAGE_VALIDATION"
        if "MEASURED_AS" in types:
            return "MEASURED_RELATION_ONLY"
        return "EVIDENCE_DEPENDENT"

    def validate_no_resemblance_promotion(self) -> list[str]:
        errors = []
        for node_id in self.nodes:
            outgoing = self.outgoing(node_id)
            if not any(e.type == "RESEMBLES" for e in outgoing):
                continue
            for edge in outgoing:
                if edge.type in {
                    "COPIED_FROM", "TRANSLATED_AS",
                    "SUPPORTED_BY", "POSSIBLE_TRANSMISSION"
                } and not edge.evidence_refs:
                    errors.append(
                        f"{node_id}: {edge.type} lacks independent evidence beyond resemblance"
                    )
        return errors
