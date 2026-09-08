import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "nist_tevv_athlon_public_comment_candidate_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_comment_candidate_is_prepared_but_not_submitted():
    payload = _payload()
    assert payload["submission_state"] == "PREPARED_NOT_SUBMITTED"
    assert payload["submission_requires_explicit_human_approval"] is True
    assert payload["submitter_identity"] == "TO_BE_SUPPLIED_BY_HUMAN"


def test_candidate_preserves_public_release_and_nonproprietary_boundary():
    payload = _payload()
    assert payload["proprietary_information_included"] is False
    assert payload["public_release_assumed_possible"] is True
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert "has not been submitted" in boundary
    assert "proprietary" in boundary
    assert "human review" in boundary


def test_reference_and_deadline_match_current_draft_state():
    payload = _payload()
    reference = payload["reference"]
    assert reference["document"].startswith("NIST AI 200-2 ipd")
    assert reference["comment_deadline"] == "2026-10-06"
    assert reference["source"] == "https://doi.org/10.6028/NIST.AI.200-2.ipd"


def test_comment_covers_core_evidence_governance_gaps():
    payload = _payload()
    themes = {item["id"]: item for item in payload["comment_themes"]}
    expected = {
        "C1-STABLE-IDENTIFIERS",
        "C2-EVIDENCE-PROVENANCE",
        "C3-MEASUREMENT-VS-DECISION",
        "C4-NEGATIVE-EVIDENCE",
        "C5-REVIEW-SUPERSESSION",
        "C6-EVIDENCE-SCOPE",
        "C7-AGENTIC-EXECUTION-BOUNDARY",
        "C8-UNCERTAINTY-CALIBRATION",
    }
    assert expected == set(themes)
    assert all(item["nist_request_for_input_alignment"] for item in themes.values())


def test_candidate_does_not_claim_nist_status():
    payload = _payload()
    not_claimed = {item.lower() for item in payload["implementation_basis"]["not_claimed"]}
    assert "nist conformance" in not_claimed
    assert "nist endorsement" in not_claimed
    assert "nist certification" in not_claimed
    assert "nist approval" in not_claimed
