from __future__ import annotations

from typing import Any

from .graph_metrics import GraphScore, score_graph
from .mbse_extract import extract_candidate_relations
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def _expected_entities(fixture: dict[str, Any]) -> set[str]:
    return {str(node["name"]) for node in fixture["ground_truth"]["nodes"]}


def _expected_relations(fixture: dict[str, Any]) -> set[str]:
    names = {
        str(node["id"]): str(node["name"])
        for node in fixture["ground_truth"]["nodes"]
    }
    return {
        f"{names[str(edge['source'])]}->{names[str(edge['target'])]}:{edge['relation']}"
        for edge in fixture["ground_truth"]["edges"]
    }


def benchmark_synthetic_mbse(fixture: dict[str, Any]) -> GraphScore:
    relations = extract_candidate_relations(fixture["legacy_artifacts"])
    predicted_relations = {relation.canonical for relation in relations}
    predicted_entities = {
        name
        for relation in relations
        for name in (relation.source_name, relation.target_name)
    }
    return score_graph(
        expected_entities=_expected_entities(fixture),
        predicted_entities=predicted_entities,
        expected_relationships=_expected_relations(fixture),
        predicted_relationships=predicted_relations,
    )


def qualify_synthetic_mbse(
    *,
    fixture: dict[str, Any],
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    score = benchmark_synthetic_mbse(fixture)
    targets = fixture["scoring"]
    passed = (
        score.entity_precision >= float(targets["entity_precision_target"])
        and score.entity_recall >= float(targets["entity_recall_target"])
        and score.relationship_precision >= float(targets["relationship_precision_target"])
        and score.relationship_recall >= float(targets["relationship_recall_target"])
        and len(score.unsupported_entities) <= int(targets["unsupported_inference_target"])
        and len(score.unsupported_relationships) <= int(targets["unsupported_inference_target"])
    )

    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-2001",
        requirement_id=requirement.requirement_delta_id,
        test_id="mbse_synthetic_extraction_v1",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest=canonical_digest(
            {"fixture_id": fixture["fixture_id"], "classification": fixture["classification"]}
        ),
        configuration_digest=canonical_digest({"extractor": "conservative_rules_v1"}),
        inputs=[{"legacy_artifact_count": len(fixture["legacy_artifacts"])}],
        outputs=[
            {
                "entity_precision": score.entity_precision,
                "entity_recall": score.entity_recall,
                "relationship_precision": score.relationship_precision,
                "relationship_recall": score.relationship_recall,
                "unsupported_entities": list(score.unsupported_entities),
                "unsupported_relationships": list(score.unsupported_relationships),
                "missed_entities": list(score.missed_entities),
                "missed_relationships": list(score.missed_relationships),
            }
        ],
        metrics=[
            {"name": "entity_precision", "value": score.entity_precision},
            {"name": "entity_recall", "value": score.entity_recall},
            {"name": "relationship_precision", "value": score.relationship_precision},
            {"name": "relationship_recall", "value": score.relationship_recall},
        ],
        uncertainty=[
            {
                "name": "generalization",
                "state": "NOT_EVALUATED",
                "note": "Frozen synthetic fixture only",
            }
        ],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=(
            "Conservative extractor met frozen synthetic benchmark targets"
            if passed
            else "Conservative extractor did not meet frozen synthetic benchmark targets"
        ),
        negative_evidence=[
            {"unsupported_entities": list(score.unsupported_entities)},
            {"unsupported_relationships": list(score.unsupported_relationships)},
            {"missed_entities": list(score.missed_entities)},
            {"missed_relationships": list(score.missed_relationships)},
        ],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    bundle = compile_qualification_bundle(requirement, [evidence])
    bundle.pop("bundle_digest", None)
    bundle["fixture_id"] = fixture["fixture_id"]
    bundle["scope_note"] = (
        "Synthetic rule-based extraction benchmark only; no general AI, SysML/Cameo, Navy/Aegis, or classified-system claim."
    )
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle
