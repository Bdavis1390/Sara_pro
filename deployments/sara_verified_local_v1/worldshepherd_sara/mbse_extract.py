from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .qualification import EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _clean_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" .;,:")
    return re.sub(r"^(?:the)\s+", "", cleaned, flags=re.I)


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


def _append_relation(
    relations: list[CandidateRelation],
    *,
    source: str,
    target: str,
    relation: str,
    source_ref: str,
    confidence: float,
) -> None:
    relations.append(
        CandidateRelation(
            source_name=_clean_name(source),
            target_name=_clean_name(target),
            relation=relation,
            source_ref=source_ref,
            confidence=confidence,
        )
    )


def extract_candidate_relations(artifacts: list[dict[str, Any]]) -> tuple[CandidateRelation, ...]:
    """Conservative rule-based extractor for the frozen synthetic fixture family.

    It extracts only relationships explicitly encoded in supported text/row patterns.
    Two bounded prose forms are supported for the synthetic power and Ethernet cases so
    the benchmark can test a held-out paraphrase without claiming general NLP.

    This is not a general document-understanding or SysML reconstruction engine.
    """
    relations: list[CandidateRelation] = []

    for artifact in artifacts:
        artifact_id = str(artifact["artifact_id"])
        source_ref = f"artifact:{artifact_id}"
        kind = str(artifact["kind"])

        if kind == "technical_manual_excerpt":
            text = str(artifact.get("content", ""))

            receives_power = re.search(
                r"(?P<target>.+?) receives 28 VDC from the (?P<source>.+?) subsystem",
                text,
            )
            if receives_power:
                _append_relation(
                    relations,
                    source=receives_power.group("source"),
                    target=receives_power.group("target"),
                    relation="powers",
                    source_ref=source_ref,
                    confidence=0.95,
                )
            else:
                supplies_power = re.search(
                    r"(?P<source>(?:The )?[A-Z][A-Za-z0-9 _/-]+?) subsystem supplies 28 VDC to "
                    r"(?:the )?(?P<target>[A-Z][A-Za-z0-9 _/-]+?)(?:[.;]|$)",
                    text,
                )
                if supplies_power:
                    _append_relation(
                        relations,
                        source=supplies_power.group("source"),
                        target=supplies_power.group("target"),
                        relation="powers",
                        source_ref=source_ref,
                        confidence=0.90,
                    )

            forwards_ethernet = re.search(
                r"(?P<source>Sensor A).+?forwards observation messages to the "
                r"(?P<target>Mission Processor) over Ethernet",
                text,
            )
            if forwards_ethernet:
                _append_relation(
                    relations,
                    source=forwards_ethernet.group("source"),
                    target=forwards_ethernet.group("target"),
                    relation="ethernet_data",
                    source_ref=source_ref,
                    confidence=0.95,
                )
            else:
                sends_ethernet = re.search(
                    r"(?P<source>[A-Z][A-Za-z0-9 _/-]+?) "
                    r"(?:sends|transmits) observation messages over Ethernet to "
                    r"(?:the )?(?P<target>[A-Z][A-Za-z0-9 _/-]+?)(?:[.;]|$)",
                    text,
                )
                if sends_ethernet:
                    _append_relation(
                        relations,
                        source=sends_ethernet.group("source"),
                        target=sends_ethernet.group("target"),
                        relation="ethernet_data",
                        source_ref=source_ref,
                        confidence=0.90,
                    )

        elif kind == "network_configuration":
            for row in artifact.get("rows", []):
                if row.get("host") and row.get("service"):
                    _append_relation(
                        relations,
                        source=str(row["host"]),
                        target=str(row["service"]),
                        relation="hosts",
                        source_ref=source_ref,
                        confidence=0.99,
                    )
                if row.get("consumer") and row.get("service"):
                    _append_relation(
                        relations,
                        source=str(row["service"]),
                        target=str(row["consumer"]),
                        relation="publishes_track_data",
                        source_ref=source_ref,
                        confidence=0.99,
                    )

        elif kind == "cable_record":
            for row in artifact.get("rows", []):
                if row.get("from") and row.get("to") and "28 VDC" in str(row.get("purpose", "")):
                    _append_relation(
                        relations,
                        source=str(row["from"]),
                        target=str(row["to"]),
                        relation="powers",
                        source_ref=source_ref,
                        confidence=0.99,
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
