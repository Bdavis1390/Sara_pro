from __future__ import annotations

import json
from pathlib import Path

import pytest

from worldshepherd_sara.compliance import (
    ComplianceReadinessProfile,
    ControlEvidence,
    ControlEvidenceState,
)
from worldshepherd_sara.evidence_artifacts import (
    ArtifactRole,
    ComparisonOperator,
    ExpectedResult,
    QualificationTestDefinition,
    artifact_from_bytes,
    required_roles_present,
    verify_artifact,
)
from worldshepherd_sara.mbse_extract import candidate_graph, extract_candidate_relations

ROOT = Path(__file__).resolve().parents[1]


def test_artifact_hash_contract_detects_tampering_and_required_roles():
    artifact = artifact_from_bytes(
        artifact_id="input-1",
        role=ArtifactRole.INPUT,
        data=b"known fixture",
        media_type="text/plain",
        locator="fixture://input-1",
    )
    definition = QualificationTestDefinition(
        test_id="T-001",
        requirement_id="PRE-RD-2026-0001",
        description="bounded deterministic test",
        expected_results=[
            ExpectedResult(metric="state_match", operator=ComparisonOperator.EQ, target=1)
        ],
        required_artifact_roles=[ArtifactRole.INPUT],
    )
    assert verify_artifact(b"known fixture", artifact) is True
    assert verify_artifact(b"tampered fixture", artifact) is False
    assert required_roles_present(definition, [artifact]) is True


def test_compliance_readiness_defaults_fail_closed_and_present_requires_evidence():
    profile = ComplianceReadinessProfile(
        framework="NIST SP 800-171",
        controls=[
            ControlEvidence(control_id="AC.L1-3.1.1"),
            ControlEvidence(control_id="AU-example", state=ControlEvidenceState.GAP),
        ],
    )
    assert profile.externally_validated() is False
    assert profile.gap_summary()["UNKNOWN"] == 1
    assert "No CMMC/NIST 800-171 compliance" in profile.claims_boundary()
    with pytest.raises(ValueError):
        ControlEvidence(control_id="bad", state=ControlEvidenceState.PRESENT)


def test_synthetic_mbse_extractor_recovers_only_explicit_fixture_relations():
    fixture = json.loads((ROOT / "fixtures" / "mbse_legacy_fixture_v1.json").read_text())
    relations = extract_candidate_relations(fixture["legacy_artifacts"])
    canonical = {item.canonical for item in relations}
    expected = {
        "Power Distribution->Sensor A:powers",
        "Sensor A->Mission Processor:ethernet_data",
        "Mission Processor->Track Service:hosts",
        "Track Service->Operator Display:publishes_track_data",
        "Power Distribution->Mission Processor:powers",
    }
    assert canonical == expected
    graph = candidate_graph("synthetic-mbse-extract-v1", relations)
    assert len(graph.edges) == 5
    assert all(edge.source_ref and edge.source_ref.startswith("artifact:") for edge in graph.edges)
    assert all(edge.confidence is not None for edge in graph.edges)
