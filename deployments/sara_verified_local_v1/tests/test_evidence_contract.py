from __future__ import annotations

import copy

import pytest

from worldshepherd_sara.evidence_contract import (
    ClaimGraph,
    Decision,
    EvidenceContractError,
    PromotionPolicy,
    ReproductionClass,
    ast_root_digest,
    canonical_json_bytes,
    confidence_vector,
    evaluate_transition,
)


def base_record():
    return {
        "identity": {
            "ast_id": "AST-TEST-001",
            "schema_version": "1.0",
            "project_id": "worldshepherd",
            "artifact_id": "fixture",
        },
        "authority": {
            "actor": "SSPADAWANZZ",
            "role": "admin_operator",
            "authorized": True,
            "human_gate_approved": False,
        },
        "inputs": {"source_commit": "abc123", "artifact_hashes": {"fixture": "deadbeef"}},
        "environment": {"captured": True, "environment_id": "env-1"},
        "transformation": {"procedure": "controlled-test", "parameters": {}},
        "observations": {
            "complete": True,
            "negative_results": [],
            "anomalies": [],
        },
        "verification": {
            "result": "pass",
            "reproduction_class": "R2",
            "contradiction_severity": "NONE",
        },
        "provenance": {"integrity_ok": True, "parent_ast_ids": []},
        "claims": {
            "requested_scope": 2,
            "maximum_permitted_scope": 2,
            "permitted": ["controlled validation passed"],
            "prohibited": ["external validation"],
        },
    }


def test_canonical_json_is_order_independent():
    a = {"b": 1, "a": [3, 2, 1]}
    b = {"a": [3, 2, 1], "b": 1}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_ast_digest_changes_when_evidence_changes():
    record = base_record()
    digest_a = ast_root_digest(record)
    record["observations"]["anomalies"].append("new")
    assert ast_root_digest(record) != digest_a


def test_complete_record_promotes():
    result = evaluate_transition(base_record())
    assert result.decision == Decision.PROMOTE
    assert result.reasons == ()


def test_claim_above_evidence_is_denied():
    record = base_record()
    record["claims"]["requested_scope"] = 3
    result = evaluate_transition(record)
    assert result.decision == Decision.DENY
    assert "CLAIM_EXCEEDS_EVIDENCE" in result.reasons


def test_incomplete_provenance_holds():
    record = base_record()
    record["provenance"]["integrity_ok"] = False
    result = evaluate_transition(record)
    assert result.decision == Decision.HOLD
    assert "PROVENANCE_INCOMPLETE" in result.reasons


def test_failed_verification_denies():
    record = base_record()
    record["verification"]["result"] = "fail"
    assert evaluate_transition(record).decision == Decision.DENY


def test_material_contradiction_forces_review():
    record = base_record()
    record["verification"]["contradiction_severity"] = "MATERIAL"
    result = evaluate_transition(record)
    assert result.decision == Decision.REVIEW
    assert "MATERIAL_CONTRADICTION" in result.reasons


def test_critical_contradiction_demotes():
    record = base_record()
    record["verification"]["contradiction_severity"] = "CRITICAL"
    result = evaluate_transition(record)
    assert result.decision == Decision.DEMOTE


def test_reproduction_gate_holds_when_independence_insufficient():
    record = base_record()
    policy = PromotionPolicy(required_reproduction=ReproductionClass.R3)
    result = evaluate_transition(record, policy)
    assert result.decision == Decision.HOLD
    assert "REPRODUCTION_LEVEL_INSUFFICIENT" in result.reasons


def test_human_gate_is_fail_closed():
    record = base_record()
    policy = PromotionPolicy(human_gate_required=True)
    result = evaluate_transition(record, policy)
    assert result.decision == Decision.HOLD
    assert "HUMAN_GATE_REQUIRED" in result.reasons


def test_claim_graph_recursively_suspends_dependents():
    graph = ClaimGraph()
    graph.add_claim("C1", evidence_ids=["E1"])
    graph.add_claim("C2", parent_claims=["C1"])
    graph.add_claim("C3", parent_claims=["C2"])
    changed = graph.suspend_for_evidence("E1")
    assert changed == {"C1", "C2", "C3"}
    assert graph.status("C3") == "SUSPENDED"


def test_confidence_vector_is_not_an_opaque_aggregate():
    vector = confidence_vector(
        provenance_integrity=1.0,
        measurement_quality=0.9,
        reproducibility=0.6,
        independence=0.2,
        environmental_similarity=0.8,
        statistical_strength=0.7,
        external_support=0.1,
    )
    assert set(vector) == {
        "provenance_integrity",
        "measurement_quality",
        "reproducibility",
        "independence",
        "environmental_similarity",
        "statistical_strength",
        "external_support",
    }


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_confidence_vector_rejects_out_of_range_values(value):
    kwargs = {
        "provenance_integrity": 1.0,
        "measurement_quality": 1.0,
        "reproducibility": 1.0,
        "independence": 1.0,
        "environmental_similarity": 1.0,
        "statistical_strength": 1.0,
        "external_support": 1.0,
    }
    kwargs["independence"] = value
    with pytest.raises(EvidenceContractError):
        confidence_vector(**kwargs)
