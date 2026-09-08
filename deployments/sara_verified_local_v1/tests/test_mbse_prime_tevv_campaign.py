import json
from pathlib import Path

from worldshepherd_sara.mbse_baseline import (
    extract_legacy_model,
    meets_fixture_targets,
    score_against_ground_truth,
)
from worldshepherd_sara.qualification import (
    CapabilityStatus,
    DemandClass,
    EvidenceScope,
    ForecastHorizon,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    ReviewRecord,
    ReviewStatus,
    SourceRecord,
    SourceStatus,
)
from worldshepherd_sara.tevv_athlon import (
    MetrologyBlock,
    TEVVAthlonResult,
    TEVVEvent,
    TEVVMeasurement,
    TEVVTool,
    ToolCategory,
    make_tevv_plan,
    make_tevv_result,
    verify_result_digest,
)
from worldshepherd_sara.tevv_qualification_bridge import (
    QualificationTEVVBinding,
    compile_tevv_qualification_bundle,
    verify_tevv_qualification_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "fixtures" / "mbse_legacy_fixture_v1.json"
PERTURBED = ROOT / "fixtures" / "mbse_legacy_perturbed_v1.json"
REQ_ID = "PRE-RD-2026-9101"


def _fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _requirement() -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id=REQ_ID,
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title="NAVSEA MBSE synthetic reconstruction readiness gate",
            agency="Worldshepherd internal test",
            url="https://example.invalid/navsea-mbse-tevv",
            solicitation_or_topic="DON26BX05-NP003-INTERNAL-TEVV",
            source_status=SourceStatus.OFFICIAL_SOURCE_VERIFIED,
            retrieved_utc="2026-09-08T17:40:00Z",
        ),
        statement="Legacy-document reconstruction must preserve correctness and provenance under paraphrase before production or Cameo integration claims.",
        recurrence="Synthetic internal readiness campaign",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["NAVSEA_MBSE_EXTRACTION", "PRIME-TEVV", "PVK"],
        existing_capability=["deterministic extraction baseline", "synthetic known-ground-truth corpus"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["robust paraphrase/layout understanding", "Cameo round-trip validation"],
        experiment_or_demonstration_needed=["canonical and adversarial synthetic corpus scoring"],
        evidence_target=["entity/relationship precision and recall", "unsupported inference count"],
        claims_boundary=[
            "Synthetic software evidence only; no Navy, AEGIS, CUI, classified, or export-controlled data is used.",
            "This campaign does not establish Cameo interoperability, production reconstruction accuracy, or AI/ML capability.",
        ],
    )


def _plan():
    blocks = [
        MetrologyBlock(
            block_id="B-ENTITY",
            name="Entity reconstruction",
            definition="Correct reconstruction of known ground-truth entities.",
            evidence_required=["ground truth entities", "predicted entities"],
        ),
        MetrologyBlock(
            block_id="B-REL",
            name="Relationship reconstruction",
            definition="Correct reconstruction of known ground-truth relationships.",
            evidence_required=["ground truth relationships", "predicted relationships"],
        ),
        MetrologyBlock(
            block_id="B-UNSUPPORTED",
            name="Unsupported inference",
            definition="Relationships inferred without support in the known-ground-truth corpus.",
            evidence_required=["predicted relationships", "ground truth relationships"],
        ),
    ]
    tools = [
        TEVVTool(
            tool_id="T-GROUND-TRUTH",
            name="MBSE ground-truth scorer",
            category=ToolCategory.MODEL_TESTING,
            description="Scores extracted entities and relationships against the synthetic known-ground-truth fixtures.",
            version_or_digest="mbse_baseline.py@repository-head",
            source_refs=["mbse_legacy_fixture_v1.json", "mbse_legacy_perturbed_v1.json"],
        )
    ]
    events = [
        TEVVEvent(
            event_id="E-CANONICAL",
            name="Canonical synthetic corpus",
            description="Run the deterministic baseline against the original synthetic corpus.",
            block_ids=["B-ENTITY", "B-REL", "B-UNSUPPORTED"],
            tool_ids=["T-GROUND-TRUTH"],
            expected_evidence=["precision", "recall", "unsupported inference count"],
        ),
        TEVVEvent(
            event_id="E-PARAPHRASE",
            name="Paraphrase challenge",
            description="Run the same unchanged baseline against the adversarial paraphrased corpus.",
            block_ids=["B-ENTITY", "B-REL", "B-UNSUPPORTED"],
            tool_ids=["T-GROUND-TRUTH"],
            expected_evidence=["precision", "recall", "unsupported inference count", "retained failure"],
            adversarial=True,
        ),
    ]
    return make_tevv_plan(
        system_id="WS-MBSE-DETERMINISTIC-BASELINE",
        evaluation_goal="Determine whether the deterministic extraction baseline is robust enough to advance beyond a synthetic minimum benchmark.",
        decision_use="Hold, restrict, or advance only the internal software readiness boundary; never infer production or Cameo readiness.",
        operational_context="Unclassified synthetic fixtures with known ground truth.",
        stakeholders=["CRE1AWS", "SSPADAWANZZ"],
        lifecycle_stages=["baseline", "adversarial-regression"],
        system_attributes=["correctness", "unsupported inference", "robustness", "provenance"],
        blocks=blocks,
        tools=tools,
        events=events,
    )


def _qualification_record(
    *,
    qualification_id: str,
    test_id: str,
    metrics: dict,
    result: ResultStatus,
    negative_evidence: list[dict],
) -> QualificationEvidenceRecord:
    ordered_metrics = [
        {"name": "entity_precision", "value": metrics["entity_precision"]},
        {"name": "entity_recall", "value": metrics["entity_recall"]},
        {"name": "relationship_precision", "value": metrics["relationship_precision"]},
        {"name": "relationship_recall", "value": metrics["relationship_recall"]},
        {"name": "unsupported_inference_count", "value": metrics["unsupported_inference_count"], "units": "count"},
    ]
    return QualificationEvidenceRecord(
        qualification_id=qualification_id,
        requirement_id=REQ_ID,
        test_id=test_id,
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.IMPLEMENTED_IN_SOFTWARE,
        environment_digest="sha256:" + ("1" if result is ResultStatus.PASS else "2") * 64,
        configuration_digest="sha256:" + "3" * 64,
        inputs=[{"fixture": test_id}],
        outputs=[{"metrics": metrics}],
        metrics=ordered_metrics,
        uncertainty=[{"scope": "synthetic fixture", "note": "No production-distribution uncertainty is claimed."}],
        result=result,
        rationale=(
            "Canonical synthetic target met."
            if result is ResultStatus.PASS
            else "Adversarial paraphrase target not met; failure retained."
        ),
        negative_evidence=negative_evidence,
        software_commit="repository-head",
        executed_utc="2026-09-08T17:41:00Z",
        operator="pytest",
        review=ReviewRecord(
            status=ReviewStatus.ACCEPTED,
            reviewer="synthetic-regression-review",
            reviewed_utc="2026-09-08T17:42:00Z",
        ),
    )


def _bindings(qualification_id: str, event_id: str, prefix: str) -> list[QualificationTEVVBinding]:
    coordinates = [
        (0, "B-ENTITY"),
        (1, "B-ENTITY"),
        (2, "B-REL"),
        (3, "B-REL"),
        (4, "B-UNSUPPORTED"),
    ]
    return [
        QualificationTEVVBinding(
            binding_id=f"WS-TEVV-BIND-{prefix}-{idx}",
            qualification_id=qualification_id,
            metric_index=metric_index,
            event_id=event_id,
            block_id=block_id,
            tool_id="T-GROUND-TRUTH",
        )
        for idx, (metric_index, block_id) in enumerate(coordinates, start=1)
    ]


def test_mbse_campaign_retains_paraphrase_failure_and_holds_readiness():
    canonical = _fixture(CANONICAL)
    perturbed = _fixture(PERTURBED)

    canonical_metrics = score_against_ground_truth(extract_legacy_model(canonical), canonical)
    perturbed_metrics = score_against_ground_truth(extract_legacy_model(perturbed), perturbed)

    assert meets_fixture_targets(canonical_metrics, canonical) is True
    assert meets_fixture_targets(perturbed_metrics, perturbed) is False

    canonical_qe = _qualification_record(
        qualification_id="WS-QE-2026-9101",
        test_id=canonical["fixture_id"],
        metrics=canonical_metrics,
        result=ResultStatus.PASS,
        negative_evidence=[],
    )
    perturbed_qe = _qualification_record(
        qualification_id="WS-QE-2026-9102",
        test_id=perturbed["fixture_id"],
        metrics=perturbed_metrics,
        result=ResultStatus.FAIL,
        negative_evidence=[
            {
                "kind": "PARAPHRASE_BRITTLENESS",
                "fixture_id": perturbed["fixture_id"],
                "metrics": perturbed_metrics,
                "interpretation": "The unchanged deterministic baseline does not satisfy the declared adversarial reconstruction targets.",
            }
        ],
    )

    plan = _plan()
    bundle = compile_tevv_qualification_bundle(
        _requirement(),
        plan,
        [canonical_qe, perturbed_qe],
        [
            *_bindings(canonical_qe.qualification_id, "E-CANONICAL", "canonical"),
            *_bindings(perturbed_qe.qualification_id, "E-PARAPHRASE", "paraphrase"),
        ],
    )

    assert verify_tevv_qualification_bundle(bundle) is True
    assert {item["result"] for item in bundle["evidence_index"]} == {"PASS", "FAIL"}
    assert bundle["negative_evidence"][0]["qualification_id"] == perturbed_qe.qualification_id
    assert bundle["physical_validation_claimed"] is False
    assert bundle["external_execution_claimed"] is False
    assert all(
        measurement["passed_acceptance_rule"] is None
        for measurement in bundle["measurement_candidates"]
    )

    measurements = [
        TEVVMeasurement.model_validate(item)
        for item in bundle["measurement_candidates"]
    ]
    result: TEVVAthlonResult = make_tevv_result(
        plan,
        measurements=measurements,
        synthesized_findings=[
            "The deterministic baseline satisfies the original synthetic fixture targets.",
            "The same unchanged baseline fails the adversarial paraphrase fixture, demonstrating insufficient robustness for broader legacy-document reconstruction claims.",
            "The failure is retained as negative evidence and is not averaged away by the canonical PASS.",
        ],
        unresolved_questions=[
            "What held-out document transformations should define the next robustness campaign?",
            "What human-correction burden is acceptable before future AI/ML or Cameo integration work advances?",
        ],
        decision="HOLD_DETERMINISTIC_BASELINE_FOR_ROBUST_DOCUMENT_RECONSTRUCTION",
    )

    assert verify_result_digest(result) is True
    assert result.decision == "HOLD_DETERMINISTIC_BASELINE_FOR_ROBUST_DOCUMENT_RECONSTRUCTION"
    assert result.external_execution_performed is False
    assert result.physical_validation_claimed is False
    assert result.nist_conformance_claimed is False
    assert result.nist_endorsement_claimed is False
