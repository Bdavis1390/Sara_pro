import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "navsea_mbse_capture_gate_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_phase_i_and_phase_ii_positions_are_separate():
    payload = _payload()
    state = payload["capture_state"]
    assert state["phase_i_prime_position"] == "CONDITIONAL_CANDIDATE_PENDING_ADMIN_ELIGIBILITY"
    assert state["phase_ii_position"] == "NO_GO_UNTIL_SECURITY_AND_CAMEO_GATES_VERIFIED"
    assert state["proposal_submitted"] is False


def test_security_and_cameo_gaps_fail_closed():
    state = _payload()["capture_state"]
    assert state["dsip_registration_status"] == "UNVERIFIED_IN_CONNECTED_RECORDS"
    assert state["facility_clearance_path"] == "UNVERIFIED"
    assert state["personnel_clearance_path"] == "UNVERIFIED"
    assert state["cmmc_level_2_self_status"] == "NOT_ASSESSED"
    assert state["cameo_openapi_integration"] == "NOT_IMPLEMENTED"


def test_q_and_a_is_prepared_but_not_claimed_submitted():
    qa = _payload()["q_and_a_candidate"]
    assert qa["dsip_access_required"] is True
    assert qa["dsip_access_verified"] is False
    assert qa["submitted"] is False
    assert len(qa["questions"]) == 3


def test_phase_i_metrics_are_internal_targets_only():
    metrics = _payload()["go_no_go_metrics"]
    assert metrics["metric_status"] == "INTERNAL_PHASE_I_TARGETS_NOT_GOVERNMENT_ACCEPTANCE_THRESHOLDS"
    assert metrics["unsupported_relationship_fraction_max"] <= 0.01
    assert metrics["source_provenance_completeness_min"] >= 0.99


def test_claims_boundary_rejects_current_cameo_and_government_validation_claims():
    boundary = " ".join(_payload()["claims_boundary"]).lower()
    for required in (
        "no cameo/magicdraw interoperability is currently claimed",
        "no aegis, navy, cui, export-controlled, or classified data",
        "passing a synthetic fixture does not establish general legacy-document reconstruction accuracy",
        "phase ii security eligibility and clearance capability are not established",
        "no cmmc assessment",
    ):
        assert required in boundary
