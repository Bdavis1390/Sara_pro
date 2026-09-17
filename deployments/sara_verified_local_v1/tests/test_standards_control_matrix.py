from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "standards_conformance_baseline.json"
MATRIX_PATH = ROOT / "standards_control_matrix.json"

PROMOTED_STATUSES = {"MET", "EXCEEDED"}
EXTERNAL_CLAIM_STATUSES = {"INDEPENDENT_REVIEW_READY", "FORMALLY_ASSESSED", "MET", "EXCEEDED"}
REQUIRED_RECORD_FIELDS = {
    "control_id",
    "standard_id",
    "domain",
    "control_objective",
    "owner_role",
    "reviewer_role",
    "current_status",
    "readiness_level",
    "evidence_required",
    "implementation_evidence_ids",
    "assessment_method",
    "latest_check_result",
    "gap_or_exception_disposition",
    "claims_boundary_reference",
    "next_action",
}
PROHIBITED_ASSERTIONS = {
    "certified",
    "accredited",
    "authorized",
    "approved",
    "validated",
    "cmmc conformant",
    "nist 800-171 implemented",
    "dfars satisfied",
    "fedramp authorized",
    "iso certified",
    "soc 2 attested",
    "bae validated",
    "doe validated",
    "field proven",
    "hardware validated",
}


def _load(path: Path) -> dict:
    assert path.is_file(), f"missing JSON file: {path}"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_matrix_schema_and_baseline_linkage() -> None:
    baseline = _load(BASELINE_PATH)
    matrix = _load(MATRIX_PATH)

    assert matrix["schema"] == "WS-INDUSTRY-STANDARDS-CONTROL-MATRIX-V1"
    assert matrix["source_baseline"] == baseline["record_id"]
    assert "does not establish certification" in matrix["claims_boundary"]
    assert "CMMC conformity" in matrix["claims_boundary"]
    assert "BAE validation" in matrix["claims_boundary"]


def test_each_baseline_standard_has_control_record() -> None:
    baseline = _load(BASELINE_PATH)
    matrix = _load(MATRIX_PATH)

    baseline_ids = {record["id"] for record in baseline["standard_sources"]}
    matrix_ids = {record["standard_id"] for record in matrix["control_records"]}

    assert baseline_ids.issubset(matrix_ids)
    assert matrix["summary"]["records"] == len(matrix["control_records"])


def test_control_records_have_required_fields_and_valid_status() -> None:
    matrix = _load(MATRIX_PATH)
    allowed_statuses = set(matrix["allowed_statuses"])
    observed_control_ids: set[str] = set()

    for record in matrix["control_records"]:
        assert REQUIRED_RECORD_FIELDS.issubset(record)
        assert record["control_id"] not in observed_control_ids
        observed_control_ids.add(record["control_id"])
        assert record["current_status"] in allowed_statuses
        assert record["evidence_required"], record["control_id"]
        assert record["assessment_method"], record["control_id"]
        assert record["claims_boundary_reference"] == "WS-STANDARDS-BASELINE-2026-09-01"
        assert record["gap_or_exception_disposition"], record["control_id"]


def test_met_or_exceeded_status_requires_evidence_and_passed_assessment() -> None:
    matrix = _load(MATRIX_PATH)

    for record in matrix["control_records"]:
        if record["current_status"] in PROMOTED_STATUSES:
            assert record["implementation_evidence_ids"], record["control_id"]
            assert record["latest_check_result"] in {"PASS", "FORMAL_PASS"}
            assert record.get("formal_assessment_reference_when_required")
            assert record["gap_or_exception_disposition"] in {"NO_OPEN_GAP", "ACCEPTED_EXCEPTION_WITH_OWNER"}


def test_external_claim_status_requires_reviewer_and_evidence_ids() -> None:
    matrix = _load(MATRIX_PATH)

    for record in matrix["control_records"]:
        if record["current_status"] in EXTERNAL_CLAIM_STATUSES:
            assert record["implementation_evidence_ids"], record["control_id"]
            assert "reviewer" in record["reviewer_role"].lower() or "assessor" in record["reviewer_role"].lower()
            assert record["latest_check_result"] not in {"NOT_RUN_FOR_THIS_CONTROL", "PARTIAL_PASS_INTERNAL_ONLY"}
            if record["current_status"] in {"FORMALLY_ASSESSED", "MET", "EXCEEDED"}:
                assert record["latest_check_result"] in {"PASS", "FORMAL_PASS"}, record["control_id"]
                assert record.get("formal_assessment_reference_when_required"), record["control_id"]


def test_status_counts_match_records_and_do_not_claim_formal_readiness() -> None:
    matrix = _load(MATRIX_PATH)
    counts = {status: 0 for status in matrix["allowed_statuses"]}
    for record in matrix["control_records"]:
        counts[record["current_status"]] += 1

    declared = matrix["summary"]["current_status_counts"]
    for status, count in declared.items():
        assert counts.get(status, 0) == count
    assert declared["MET"] == 0
    assert declared["EXCEEDED"] == 0
    assert declared["FORMALLY_ASSESSED"] == 0
    assert "no formal conformance or certification claim" in matrix["summary"]["highest_claimable_global_level"]


def test_matrix_blocks_false_readiness_language() -> None:
    matrix = _load(MATRIX_PATH)
    claim_surface = dict(matrix)
    meet_or_exceed_gate = dict(claim_surface.get("meet_or_exceed_gate", {}))
    meet_or_exceed_gate.pop("prohibited_self_assertions", None)
    claim_surface["meet_or_exceed_gate"] = meet_or_exceed_gate
    text = json.dumps(claim_surface, sort_keys=True).lower()

    for assertion in PROHIBITED_ASSERTIONS:
        assert assertion not in text


def test_next_priority_moves_toward_actual_controls() -> None:
    matrix = _load(MATRIX_PATH)
    next_priority = matrix["summary"]["next_priority"]

    assert "SBOM" in next_priority
    assert "vulnerability" in next_priority
    assert "secrets" in next_priority
    assert "SSDF" in next_priority
    assert "CUI boundary" in next_priority
    assert "ASVS" in next_priority
