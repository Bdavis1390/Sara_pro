import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "doe_genesis_submission_readiness_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_submission_is_not_marked_ready_while_prime_and_amp_are_unresolved():
    payload = _payload()
    gates = {item["gate_id"]: item for item in payload["gates"]}
    assert payload["overall_status"] == "CONTENT_READY_ADMIN_ACCESS_NOT_READY"
    assert gates["G1_PRIME_IDENTITY"]["status"].startswith("BLOCKED")
    assert gates["G2_AMP_ACCESS"]["status"] == "NOT_EVIDENCED"
    assert gates["G7_SUBMISSION_AUTHORITY"]["status"].startswith("BLOCKED")


def test_connected_record_absence_is_not_overstated():
    payload = _payload()
    checks = payload["connected_record_checks"]
    assert checks["gmail_result"] == "NO_MATCHING_RECORD_FOUND"
    assert checks["drive_result"] == "NO_MATCHING_RECORD_FOUND"
    assert "does not prove no account exists elsewhere" in checks["interpretation"]


def test_pitch_stage_company_formation_is_recorded_separately_from_award_registration():
    payload = _payload()
    gates = {item["gate_id"]: item for item in payload["gates"]}
    assert gates["G3_FORMATION_AT_PITCH"]["status"] == "ALLOWED_WITH_DOWNSTREAM_REGISTRATION_GAP"
    assert gates["G4_SAM_SBA_REGISTRATIONS"]["status"] == "UNVERIFIED_NOT_PITCH_BLOCKER_BY_ITSELF"


def test_next_actions_preserve_human_submission_authority():
    payload = _payload()
    actions = " ".join(payload["next_actions_in_order"]).lower()
    assert "confirm the exact prime small-business identity" in actions
    assert "verify ati/connectwerx amp access" in actions
    assert "final applicant review" in actions
    assert "retain the connectwerx receipt email as echo evidence" in actions
