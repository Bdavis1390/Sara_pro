from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class MBSEEntity:
    name: str
    entity_type: str
    source_refs: tuple[str, ...]


@dataclass(frozen=True)
class MBSERelationship:
    source: str
    target: str
    relation: str
    source_ref: str


def _clean_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    value = re.sub(r"\s+subsystem$", "", value, flags=re.IGNORECASE)
    return value.strip(" .,:;")


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _clean_name(value).lower()).strip("_")


def infer_entity_type(name: str) -> str:
    lowered = name.lower()
    if "sensor" in lowered:
        return "sensor"
    if "processor" in lowered or "computer" in lowered or "compute" in lowered:
        return "compute"
    if "display" in lowered or "console" in lowered or "hmi" in lowered:
        return "hmi"
    if "service" in lowered or "daemon" in lowered:
        return "software_service"
    if "distribution" in lowered or "subsystem" in lowered or "power" in lowered:
        return "subsystem"
    return "unknown"


def _add_entity(store: dict[str, MBSEEntity], name: str, source_ref: str) -> None:
    clean = _clean_name(name)
    if not clean:
        return
    key = _key(clean)
    current = store.get(key)
    refs = set(current.source_refs if current else ())
    refs.add(source_ref)
    entity_type = current.entity_type if current and current.entity_type != "unknown" else infer_entity_type(clean)
    store[key] = MBSEEntity(
        name=clean,
        entity_type=entity_type,
        source_refs=tuple(sorted(refs)),
    )


def extract_legacy_model(fixture: dict[str, Any]) -> dict[str, Any]:
    """Extract a small evidence-linked model from the synthetic legacy corpus.

    This is deliberately a deterministic rules baseline, not an AI/ML model and
    not a Cameo/MagicDraw exporter. It exists to create a falsifiable minimum
    benchmark that future AI/ML ingestion must outperform on held-out corpora.
    """

    entities: dict[str, MBSEEntity] = {}
    relationships: list[MBSERelationship] = []

    for artifact in fixture.get("legacy_artifacts", []):
        artifact_id = str(artifact.get("artifact_id", "unknown"))
        kind = artifact.get("kind")

        if kind == "hardware_bom":
            for row in artifact.get("rows", []):
                item = row.get("item")
                if item:
                    _add_entity(entities, str(item), artifact_id)

        elif kind == "network_configuration":
            for row in artifact.get("rows", []):
                host = row.get("host")
                service = row.get("service")
                consumer = row.get("consumer")
                if host:
                    _add_entity(entities, str(host), artifact_id)
                if service:
                    _add_entity(entities, str(service), artifact_id)
                if consumer:
                    _add_entity(entities, str(consumer), artifact_id)
                if host and service:
                    relationships.append(
                        MBSERelationship(str(host), str(service), "hosts", artifact_id)
                    )
                if consumer and service:
                    relationships.append(
                        MBSERelationship(str(service), str(consumer), "publishes_track_data", artifact_id)
                    )

        elif kind == "cable_record":
            for row in artifact.get("rows", []):
                source = row.get("from")
                target = row.get("to")
                purpose = str(row.get("purpose", ""))
                if source:
                    _add_entity(entities, str(source), artifact_id)
                if target:
                    _add_entity(entities, str(target), artifact_id)
                if source and target and ("vdc" in purpose.lower() or "power" in purpose.lower()):
                    relationships.append(
                        MBSERelationship(str(source), str(target), "powers", artifact_id)
                    )

        elif kind == "technical_manual_excerpt":
            text = str(artifact.get("content", ""))
            power_match = re.search(
                r"(?P<target>[A-Z][A-Za-z0-9 ]+?)\s+receives\s+[^.]*?\s+from\s+the\s+(?P<source>[A-Z][A-Za-z0-9 ]+?)(?:\s+subsystem)?\s+and\s+",
                text,
            )
            if power_match:
                source = _clean_name(power_match.group("source"))
                target = _clean_name(power_match.group("target"))
                _add_entity(entities, source, artifact_id)
                _add_entity(entities, target, artifact_id)
                relationships.append(MBSERelationship(source, target, "powers", artifact_id))

            ethernet_match = re.search(
                r"(?P<source>[A-Z][A-Za-z0-9 ]+?)\s+(?:forwards|sends)\s+[^.]*?\s+to\s+(?:the\s+)?(?P<target>[A-Z][A-Za-z0-9 ]+?)\s+over\s+Ethernet",
                text,
            )
            if ethernet_match:
                source = _clean_name(ethernet_match.group("source"))
                target = _clean_name(ethernet_match.group("target"))
                _add_entity(entities, source, artifact_id)
                _add_entity(entities, target, artifact_id)
                relationships.append(
                    MBSERelationship(source, target, "ethernet_data", artifact_id)
                )

    unique_relationships: dict[tuple[str, str, str], MBSERelationship] = {}
    for rel in relationships:
        unique_relationships[(_key(rel.source), _key(rel.target), rel.relation)] = MBSERelationship(
            _clean_name(rel.source), _clean_name(rel.target), rel.relation, rel.source_ref
        )

    return {
        "schema": "ws-mbse-baseline-model-1",
        "generator": "deterministic_rules_baseline",
        "ai_ml_claimed": False,
        "cameo_magicdraw_interoperability_claimed": False,
        "entities": [
            {
                "name": entity.name,
                "entity_type": entity.entity_type,
                "source_refs": list(entity.source_refs),
            }
            for entity in sorted(entities.values(), key=lambda item: _key(item.name))
        ],
        "relationships": [
            {
                "source": rel.source,
                "target": rel.target,
                "relation": rel.relation,
                "source_ref": rel.source_ref,
            }
            for rel in sorted(
                unique_relationships.values(),
                key=lambda item: (_key(item.source), _key(item.target), item.relation),
            )
        ],
    }


def _prf(predicted: set[Any], expected: set[Any]) -> tuple[float, float]:
    if not predicted:
        precision = 1.0 if not expected else 0.0
    else:
        precision = len(predicted & expected) / len(predicted)
    recall = 1.0 if not expected else len(predicted & expected) / len(expected)
    return precision, recall


def score_against_ground_truth(model: dict[str, Any], fixture: dict[str, Any]) -> dict[str, float | int]:
    expected_entities = {
        (_key(str(node["name"])), str(node["type"]))
        for node in fixture.get("ground_truth", {}).get("nodes", [])
    }
    predicted_entities = {
        (_key(str(entity["name"])), str(entity["entity_type"]))
        for entity in model.get("entities", [])
    }

    id_to_name = {
        str(node["id"]): str(node["name"])
        for node in fixture.get("ground_truth", {}).get("nodes", [])
    }
    expected_relationships = {
        (
            _key(id_to_name[str(edge["source"])]),
            _key(id_to_name[str(edge["target"])]),
            str(edge["relation"]),
        )
        for edge in fixture.get("ground_truth", {}).get("edges", [])
    }
    predicted_relationships = {
        (_key(str(rel["source"])), _key(str(rel["target"])), str(rel["relation"]))
        for rel in model.get("relationships", [])
    }

    entity_precision, entity_recall = _prf(predicted_entities, expected_entities)
    relationship_precision, relationship_recall = _prf(
        predicted_relationships, expected_relationships
    )
    unsupported = len(predicted_relationships - expected_relationships)
    missed = len(expected_relationships - predicted_relationships)

    return {
        "entity_precision": round(entity_precision, 6),
        "entity_recall": round(entity_recall, 6),
        "relationship_precision": round(relationship_precision, 6),
        "relationship_recall": round(relationship_recall, 6),
        "unsupported_inference_count": unsupported,
        "missed_relationship_count": missed,
    }


def meets_fixture_targets(metrics: dict[str, float | int], fixture: dict[str, Any]) -> bool:
    targets = fixture.get("scoring", {})
    return bool(
        float(metrics["entity_precision"]) >= float(targets.get("entity_precision_target", 1.0))
        and float(metrics["entity_recall"]) >= float(targets.get("entity_recall_target", 1.0))
        and float(metrics["relationship_precision"])
        >= float(targets.get("relationship_precision_target", 1.0))
        and float(metrics["relationship_recall"])
        >= float(targets.get("relationship_recall_target", 1.0))
        and int(metrics["unsupported_inference_count"])
        <= int(targets.get("unsupported_inference_target", 0))
    )
