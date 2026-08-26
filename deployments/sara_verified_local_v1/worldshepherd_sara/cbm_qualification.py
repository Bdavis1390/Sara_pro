from __future__ import annotations

from typing import Any

from .cbm_twin import ExpectedEnvelope, TelemetrySample, evaluate_series, health_graph
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def qualify_synthetic_cbm(
    *, fixture: dict[str, Any], requirement: RequirementDeltaRecord,
    software_commit: str, executed_utc: str, operator: str,
) -> dict[str, Any]:
    envelopes = {
        item["metric"]: ExpectedEnvelope.model_validate(item)
        for item in fixture["expected_envelopes"]
    }
    samples = [TelemetrySample.model_validate(item) for item in fixture["telemetry"]]
    findings = evaluate_series(samples, envelopes)
    graph = health_graph(graph_id=fixture["fixture_id"], samples=samples, findings=findings)
    statuses = [finding.status for finding in findings]
    anomaly_count = sum(1 for status in statuses if status != "NOMINAL")
    traceable = all(edge.source_ref for edge in graph.edges)
    expected = fixture["expected"]
    passed = (
        statuses == expected["finding_statuses"]
        and anomaly_count == int(expected["anomaly_count"])
        and traceable is bool(expected["all_findings_traceable"])
    )

    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-8001",
        requirement_id=requirement.requirement_delta_id,
        test_id="cbm_twin_synthetic_v1",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest=canonical_digest({"fixture_id": fixture["fixture_id"], "classification": fixture["classification"]}),
        configuration_digest=canonical_digest({"expected_envelopes": fixture["expected_envelopes"]}),
        inputs=[{"telemetry_count": len(samples), "asset_id": fixture["asset_id"]}],
        outputs=[{"statuses": statuses, "anomaly_count": anomaly_count, "traceable": traceable}],
        metrics=[
            {"name": "anomaly_count", "value": anomaly_count, "expected": expected["anomaly_count"]},
            {"name": "all_findings_traceable", "value": traceable},
        ],
        uncertainty=[
            {"name": "predictive_maintenance_validity", "state": "NOT_EVALUATED"},
            {"name": "remaining_useful_life", "state": "NOT_EVALUATED"},
        ],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=("Synthetic envelope-based asset health classification met frozen expectations" if passed else "Synthetic asset health classification diverged from frozen expectations"),
        negative_evidence=[] if passed else [{"expected": expected, "observed_statuses": statuses, "anomaly_count": anomaly_count}],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    bundle = compile_qualification_bundle(requirement, [evidence], graph)
    bundle.pop("bundle_digest", None)
    bundle["fixture_id"] = fixture["fixture_id"]
    bundle["scope_note"] = "Synthetic telemetry/envelope CBM+ evidence only; no real platform, predictive-maintenance, RUL, or fleet-effectiveness claim."
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle
