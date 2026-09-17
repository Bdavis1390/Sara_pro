from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.gemara_full_projection import (
    GEMARA_SCHEMA_COMMIT,
    GEMARA_VERSION,
    build_full_gemara_documents,
)
from worldshepherd_sara.standards_interop import InteropCaseDefinition


CORPUS_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "standards_interop" / "corpus_v0_1.json"


def _cases() -> list[InteropCaseDefinition]:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    return [InteropCaseDefinition.model_validate(item) for item in raw["cases"]]


def test_all_frozen_cases_generate_three_full_gemara_documents():
    assert GEMARA_SCHEMA_COMMIT == "24e52e93bc71e28507e1942ce543e26ab58a7f25"
    assert GEMARA_VERSION == "v0.17.0-dev"

    for case in _cases():
        docs = build_full_gemara_documents(case)
        assert set(docs) == {"evaluation", "enforcement", "audit"}
        assert docs["evaluation"]["metadata"]["type"] == "EvaluationLog"
        assert docs["enforcement"]["metadata"]["type"] == "EnforcementLog"
        assert docs["audit"]["metadata"]["type"] == "AuditLog"
        assert docs["evaluation"]["target"]["id"] == "worldshepherd-sara-control-plane"
        assert docs["enforcement"]["target"]["id"] == "worldshepherd-sara-control-plane"
        assert docs["audit"]["target"]["id"] == "worldshepherd-sara-control-plane"


def test_denial_maps_to_failed_evaluation_and_enforced_disposition():
    case = next(c for c in _cases() if c.case_id == "INT-REMOTE-DENY")
    docs = build_full_gemara_documents(case)
    assert docs["evaluation"]["result"] == "Failed"
    assert docs["enforcement"]["disposition"] == "Enforced"
    assert docs["enforcement"]["actions"][0]["justification"]["assessments"][0]["result"] == "Failed"


def test_readonly_mismatch_does_not_upgrade_to_clear():
    case = next(c for c in _cases() if c.case_id == "INT-READONLY-MISMATCH")
    docs = build_full_gemara_documents(case)
    assert docs["evaluation"]["result"] == "Needs Review"
    assert docs["enforcement"]["disposition"] == "Undetermined"
    assert docs["audit"]["results"][0]["type"] == "Observation"
    assert docs["audit"]["results"][0]["recommendations"][0]["required"] is True


def test_evidence_digest_is_identical_across_all_three_documents():
    for case in _cases():
        docs = build_full_gemara_documents(case)
        eval_digest = docs["evaluation"]["evaluations"][0]["assessment-logs"][0]["evidence"][0]["source"]["digest"]
        audit_digest = docs["audit"]["results"][0]["evidence"][0]["source"]["digest"]
        assert eval_digest == audit_digest
        assert eval_digest.startswith("sha256:")
