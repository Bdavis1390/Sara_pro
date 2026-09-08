import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "apnt_v2_input_evidence_contract_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_contract_is_draft_and_does_not_claim_implementation():
    payload = _payload()
    assert payload["status"] == "DRAFT_INTERFACE_CONTRACT_NOT_IMPLEMENTED"
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert "does not implement detection" in boundary
    assert "physical" in boundary


def test_contract_covers_all_preserved_blind_spot_evidence_categories():
    payload = _payload()
    categories = {item["category"] for item in payload["evidence_categories"]}
    assert categories == {
        "SOURCE_IDENTITY_AND_PROVENANCE",
        "SOURCE_HEALTH_AND_DECLARED_CONFIDENCE",
        "CROSS_SOURCE_CONSISTENCY",
        "TIMING_INTEGRITY",
        "DEPENDENCY_AND_INDEPENDENCE",
        "RECOVERY_AND_REENTRY",
    }


def test_thresholds_require_references_instead_of_embedded_fixture_constants():
    payload = _payload()
    by_category = {item["category"]: item for item in payload["evidence_categories"]}
    assert "threshold_reference" in by_category["CROSS_SOURCE_CONSISTENCY"]["required_fields"]
    assert "threshold_reference" in by_category["TIMING_INTEGRITY"]["required_fields"]
    assert "reentry_threshold_reference" in by_category["RECOVERY_AND_REENTRY"]["required_fields"]
    serialized = json.dumps(payload).lower()
    assert "thresholds and residual models must be justified" in serialized


def test_future_invariants_preserve_unknowns_cause_separation_and_human_authority():
    payload = _payload()
    invariants = " ".join(payload["future_decision_invariants"]).lower()
    assert "do not infer manipulation" in invariants
    assert "do not infer source independence" in invariants
    assert "missing evidence" in invariants
    assert "do not execute recovery actions automatically" in invariants
    assert "v1 decision" in invariants


def test_real_data_and_physical_assertions_require_separate_review():
    reviews = " ".join(_payload()["required_preimplementation_reviews"]).lower()
    assert "privacy/security/export-control" in reviews
    assert "failure-mode" in reviews
    assert "tevv" in reviews
    assert "partner/laboratory" in reviews
