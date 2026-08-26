from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.qualification import (
    CapabilityStatus,
    DemandClass,
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    EvidenceScope,
    ForecastHorizon,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    SourceRecord,
    SourceStatus,
    compile_qualification_bundle,
)


def _requirement(source_status: SourceStatus = SourceStatus.OFFICIAL_SOURCE_VERIFIED):
    return RequirementDeltaRecord(
        requirement_delta_id="PRE-RD-2026-0100",
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title="Synthetic APNT test requirement",
            agency="Worldshepherd test fixture",
            url="fixture://apnt",
            solicitation_or_topic="TEST-001",
            source_status=source_status,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement="Preserve source lineage through a degraded-navigation scenario.",
        recurrence="test fixture",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["APNT", "ECHO SENTINEL LINK"],
        existing_capability=["audit/provenance schema"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["real APNT sensor validation"],
        evidence_target=["replayable synthetic degradation trace"],
        claims_boundary=["synthetic fixture is not Navy or physical APNT validation"],
    )


def test_conflicting_or_unverified_source_is_not_capture_ready():
    assert _requirement(SourceStatus.UNVERIFIED).capture_ready() is False
    assert _requirement(SourceStatus.CONFLICTING_SOURCES).capture_ready() is False
    assert _requirement(SourceStatus.OFFICIAL_SOURCE_VERIFIED).capture_ready() is True


def test_evidence_graph_rejects_unknown_node_reference():
    with pytest.raises(ValidationError):
        EvidenceGraph(
            graph_id="g1",
            nodes=[EvidenceGraphNode(node_id="n1", node_type="source", label="GNSS")],
            edges=[
                EvidenceGraphEdge(
                    edge_id="e1",
                    source_node_id="n1",
                    target_node_id="missing",
                    relation="supports",
                )
            ],
        )


def test_physical_proven_status_fails_closed_without_physical_validation():
    with pytest.raises(ValidationError):
        QualificationEvidenceRecord(
            qualification_id="WS-QE-2026-0100",
            requirement_id="PRE-RD-2026-0100",
            test_id="TEST-PHYSICAL-001",
            evidence_scope=EvidenceScope.PHYSICAL,
            capability_status=CapabilityStatus.PROVEN_INTERNALLY,
            environment_digest="sha256:env",
            configuration_digest="sha256:cfg",
            result=ResultStatus.PASS,
            rationale="This must not be accepted without physical validation.",
            executed_utc="2026-08-26T00:00:00Z",
            operator="pytest",
            physical_validation_performed=False,
        )


def test_bundle_digest_is_deterministic():
    requirement = _requirement()
    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-0101",
        requirement_id=requirement.requirement_delta_id,
        test_id="APNT-SYNTH-001",
        evidence_scope=EvidenceScope.SIMULATION,
        capability_status=CapabilityStatus.SIMULATED_ONLY,
        environment_digest="sha256:env",
        configuration_digest="sha256:cfg",
        inputs=[{"name": "fixture", "digest": "sha256:fixture"}],
        outputs=[{"name": "trace", "digest": "sha256:trace"}],
        metrics=[{"name": "lineage_complete", "value": True}],
        uncertainty=[{"name": "physical_validity", "value": "UNKNOWN"}],
        result=ResultStatus.PASS,
        rationale="Synthetic lineage test passed.",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    graph = EvidenceGraph(
        graph_id="apnt-test",
        nodes=[
            EvidenceGraphNode(node_id="gnss", node_type="source", label="GNSS"),
            EvidenceGraphNode(node_id="confidence", node_type="derived", label="Confidence"),
        ],
        edges=[
            EvidenceGraphEdge(
                edge_id="e1",
                source_node_id="gnss",
                target_node_id="confidence",
                relation="contributes_to",
            )
        ],
    )

    first = compile_qualification_bundle(requirement, [evidence], graph)
    second = compile_qualification_bundle(requirement, [evidence], graph)
    assert first["bundle_digest"] == second["bundle_digest"]
