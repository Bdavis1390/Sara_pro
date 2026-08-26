from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .qualification import EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


@dataclass(frozen=True)
class CandidateRelation:
    source_name: str
    target_name: str
    relation: str
    source_ref: str
    confidence: float

    @property
    def canonical(self) -> str:
        return f"{self.source_name}->{self.target_name}:{self.relation}"


def extract_candidate_relations(artifacts: list[dict[str, Any]]) -> tuple[CandidateRelation, ...]:
    """Conservative rule-based extractor for the frozen synthetic fixture family.

    It only extracts relationships explicitly encoded in supported text/row patterns.
    It is not a general document-understanding or SysML reconstruction engine.
    """
    relations: list[CandidateRelation] = []

    for artifact in artifacts:
        artifact_id = str(artifact["artifact_id"])
        source_ref = f"artifact:{artifact_id}"
        kind = str(artifact["kind"])

        if kind == "technical_manual_excerpt":
            text = str(artifact.get("content", ""))
            power_match = re.search(
                r"(?P<target>.+?) receives 28 VDC from the (?P<source>.+?) subsystem",
                text,
            )
            if power_match:
                relations.append(
                    CandidateRelation(
                        source_name=power_match.group("source").strip(),
                        target_name=power_match.group("target").strip(),
                        relation="powers",
                        source_ref=source_ref,
                        confidence=0.95,
                    )
                )
            ethernet_match = re.search(
                r"(?P<source>Sensor A).+?forwards observation messages to the (?P<target>Mission Processor) over Ethernet",
                text,
            )
            if ethernet_match:
                relations.append(
                    CandidateRelation(
                        source_name=ethernet_match.group("source").strip(),
                        target_name=ethernet_match.group("target").strip(),
                        relation="ethernet_data",
                        source_ref=source_ref,
                        confidence=0.95,
                    )
                )

        elif kind == "network_configuration":
            for row in artifact.get("rows", []):
                if row.get("host") and row.get("service"):
                    relations.append(
                        CandidateRelation(
                            source_name=str(row["host"]),
                            target_name=str(row["service"]),
                            relation="hosts",
                            source_ref=source_ref,
                            confidence=0.99,
                        )
                    )
                if row.get("consumer") and row.get("service"):
                    relations.append(
                        CandidateRelation(
                            source_name=str(row["service"]),
                            target_name=str(row["consumer"]),
                            relation="publishes_track_data",
                            source_ref=source_ref,
                            confidence=0.99,
                        )
                    )

        elif kind == "cable_record":
            for row in artifact.get("rows", []):
                if row.get("from") and row.get("to") and "28 VDC" in str(row.get("purpose", "")):
                    relations.append(
                        CandidateRelation(
                            source_name=str(row["from"]),
                            target_name=str(row["to"]),
                            relation="powers",
                            source_ref=source_ref,
                            confidence=0.99,
                        )
                    )

    unique: dict[str, CandidateRelation] = {}
    for relation in relations:
        unique[relation.canonical] = relation
    return tuple(unique[key] for key in sorted(unique))


def candidate_graph(graph_id: str, relations: tuple[CandidateRelation, ...]) -> EvidenceGraph:
    names = sorted({r.source_name for r in relations} | {r.target_name for r in relations})
    nodes = [
        EvidenceGraphNode(
            node_id=f"entity:{_slug(name)}",
            node_type="synthetic_legacy_entity",
            label=name,
        )
        for name in names
    ]
    edges = [
        EvidenceGraphEdge(
            edge_id=f"rel:{index:04d}",
            source_node_id=f"entity:{_slug(relation.source_name)}",
            target_node_id=f"entity:{_slug(relation.target_name)}",
            relation=relation.relation,
            source_ref=relation.source_ref,
            confidence=relation.confidence,
        )
        for index, relation in enumerate(relations, start=1)
    ]
    return EvidenceGraph(graph_id=graph_id, nodes=nodes, edges=edges)
