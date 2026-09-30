from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .graph_metrics import GraphScore, score_graph
from .legacy_file_ingest import LoadedLegacyArtifact, load_file_backed_corpus
from .mbse_extract import CandidateRelation, extract_candidate_relations
from .neutral_model import evidence_graph_to_neutral_model
from .qualification import (
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    canonical_digest,
)


FILE_CONVERSION_SCHEMA = "WS-MBSE-FILE-CONVERSION-V1"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _source_evidence(item: LoadedLegacyArtifact) -> dict[str, Any]:
    return {
        "artifact_id": item.artifact_id,
        "kind": item.kind,
        "path": item.relative_path,
        "sha256": item.sha256,
        "size_bytes": item.size_bytes,
    }


def _source_index(loaded: tuple[LoadedLegacyArtifact, ...]) -> dict[str, dict[str, Any]]:
    return {
        f"artifact:{item.artifact_id}": _source_evidence(item)
        for item in loaded
    }


def _candidate_entity_metadata(
    loaded: tuple[LoadedLegacyArtifact, ...],
    relations: tuple[CandidateRelation, ...],
) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}

    def ensure(name: str) -> dict[str, Any]:
        return metadata.setdefault(
            name,
            {
                "entity_type": "legacy_entity",
                "source_refs": set(),
                "attributes": {},
                "confidence": 0.90,
            },
        )

    for item in loaded:
        source_ref = f"artifact:{item.artifact_id}"
        if item.kind != "hardware_bom":
            continue
        for row in item.artifact.get("rows", []):
            name = str(row.get("item", "")).strip()
            if not name:
                continue
            entry = ensure(name)
            entry["source_refs"].add(source_ref)
            explicit_type = str(row.get("entity_type", "")).strip()
            if explicit_type:
                entry["entity_type"] = explicit_type
                entry["confidence"] = 0.99
            part = str(row.get("part", "")).strip()
            if part:
                entry["attributes"]["part"] = part

    for relation in relations:
        for name in (relation.source_name, relation.target_name):
            entry = ensure(name)
            entry["source_refs"].add(relation.source_ref)
            entry["confidence"] = max(float(entry["confidence"]), relation.confidence)

    return metadata


def build_file_backed_candidate_graph(
    *,
    graph_id: str,
    loaded: tuple[LoadedLegacyArtifact, ...],
) -> EvidenceGraph:
    artifacts = [item.artifact for item in loaded]
    relations = extract_candidate_relations(artifacts)
    source_index = _source_index(loaded)
    entity_metadata = _candidate_entity_metadata(loaded, relations)

    nodes: list[EvidenceGraphNode] = []
    for name in sorted(entity_metadata):
        entry = entity_metadata[name]
        source_refs = sorted(entry["source_refs"])
        node_sources = [source_index[ref] for ref in source_refs if ref in source_index]
        nodes.append(
            EvidenceGraphNode(
                node_id=f"entity:{_slug(name)}",
                node_type=str(entry["entity_type"]),
                label=name,
                source_ref=source_refs[0] if source_refs else None,
                confidence=float(entry["confidence"]),
                attributes={
                    **dict(entry["attributes"]),
                    "source_refs": source_refs,
                    "source_evidence": node_sources,
                },
            )
        )

    edges: list[EvidenceGraphEdge] = []
    for index, relation in enumerate(relations, start=1):
        source_evidence = source_index.get(relation.source_ref)
        edges.append(
            EvidenceGraphEdge(
                edge_id=f"rel:{index:04d}",
                source_node_id=f"entity:{_slug(relation.source_name)}",
                target_node_id=f"entity:{_slug(relation.target_name)}",
                relation=relation.relation,
                source_ref=relation.source_ref,
                confidence=relation.confidence,
                attributes={
                    "source_evidence": source_evidence or {},
                },
            )
        )

    return EvidenceGraph(graph_id=graph_id, nodes=nodes, edges=edges)


def _expected_entities(manifest: dict[str, Any]) -> set[str]:
    return {str(node["name"]) for node in manifest["ground_truth"]["nodes"]}


def _expected_relations(manifest: dict[str, Any]) -> set[str]:
    names = {
        str(node["id"]): str(node["name"])
        for node in manifest["ground_truth"]["nodes"]
    }
    return {
        f"{names[str(edge['source'])]}->{names[str(edge['target'])]}:{edge['relation']}"
        for edge in manifest["ground_truth"]["edges"]
    }


def score_file_backed_candidate(
    manifest: dict[str, Any], graph: EvidenceGraph
) -> GraphScore:
    predicted_entities = {node.label for node in graph.nodes}
    node_names = {node.node_id: node.label for node in graph.nodes}
    predicted_relations = {
        f"{node_names[edge.source_node_id]}->{node_names[edge.target_node_id]}:{edge.relation}"
        for edge in graph.edges
    }
    return score_graph(
        expected_entities=_expected_entities(manifest),
        predicted_entities=predicted_entities,
        expected_relationships=_expected_relations(manifest),
        predicted_relationships=predicted_relations,
    )


def run_file_backed_conversion(manifest_path: str | Path) -> dict[str, Any]:
    manifest, loaded = load_file_backed_corpus(manifest_path)
    fixture_id = str(manifest["fixture_id"])
    graph = build_file_backed_candidate_graph(
        graph_id=f"{fixture_id}-candidate",
        loaded=loaded,
    )
    score = score_file_backed_candidate(manifest, graph)
    neutral_model = evidence_graph_to_neutral_model(graph)

    result: dict[str, Any] = {
        "schema": FILE_CONVERSION_SCHEMA,
        "fixture_id": fixture_id,
        "classification": str(manifest.get("classification", "UNCLASSIFIED_SYNTHETIC_FIXTURE")),
        "source_artifacts": [_source_evidence(item) for item in loaded],
        "candidate_graph": graph.model_dump(mode="json"),
        "neutral_model": neutral_model,
        "metrics": {
            "entity_precision": score.entity_precision,
            "entity_recall": score.entity_recall,
            "relationship_precision": score.relationship_precision,
            "relationship_recall": score.relationship_recall,
        },
        "negative_evidence": {
            "unsupported_entities": list(score.unsupported_entities),
            "unsupported_relationships": list(score.unsupported_relationships),
            "missed_entities": list(score.missed_entities),
            "missed_relationships": list(score.missed_relationships),
        },
        "claims_boundary": [
            "File-backed synthetic conversion for supported UTF-8 TXT/MD, CSV, and JSON sources only.",
            "Rule-based extraction against a frozen synthetic corpus; general document understanding is not established.",
            "PDF/image/diagram extraction is not implemented by this pipeline.",
            "Neutral internal model only; no SysML/XMI/Cameo/MagicDraw interoperability claim.",
            "No Navy/Aegis/classified-system reconstruction or government validation claim.",
        ],
    }
    result["output_digest"] = canonical_digest(result)
    return result
