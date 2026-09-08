import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "pinpoint_apnt_partner_gate_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_expired_abstract_gate_fails_closed_for_prime():
    payload = _payload()
    assert payload["topic"]["abstract_required_for_full_proposal"] is True
    state = payload["worldshepherd_capture_state"]
    assert state["abstract_submission_evidence"] == "NONE_FOUND_IN_CONNECTED_GMAIL_OR_GOOGLE_DRIVE"
    assert state["prime_status_current_cycle"] == "NO_GO_ABSENT_TIMELY_CONFORMING_ABSTRACT_EVIDENCE"
    assert state["full_proposal_submitted"] is False


def test_partner_lane_does_not_replace_core_sensor_physics():
    payload = _payload()
    assert payload["worldshepherd_capture_state"]["partner_status_current_cycle"] == "HIGH_PRIORITY_PARTNER_OR_SUBCONTRACTOR_LANE"
    core = payload["darpa_boundary"]["core_research_must_focus_on"]
    assert "microscale inertial-sensor physics" in core
    assert "nonlinear controls" in core
    assert "six-degree-of-freedom IMU development" in core
    assert "External or alternate sensing" in payload["darpa_boundary"]["worldshepherd_must_not_substitute"]


def test_all_current_worldshepherd_evidence_is_synthetic_only():
    payload = _payload()
    assert payload["current_evidence"]
    assert all(item["status"] == "SYNTHETIC_SOFTWARE_EVIDENCE_ONLY" for item in payload["current_evidence"])
    state = payload["worldshepherd_capture_state"]
    assert state["core_sensor_physics_claimed"] is False
    assert state["nonlinear_imu_hardware_claimed"] is False
    assert state["gps_quality_inertial_performance_claimed"] is False


def test_partner_candidates_do_not_claim_interest_or_pinpoint_participation():
    payload = _payload()
    for candidate in payload["physics_partner_screening"]:
        assert candidate["outreach_status"] == "NOT_PERFORMED"
        assert candidate["interest_or_pinpoint_participation"] in {
            "UNVERIFIED",
            "REQUIRES_PUBLIC_TEAMING_DILIGENCE",
        }


def test_claims_boundary_rejects_physical_navigation_promotion():
    boundary = " ".join(_payload()["claims_boundary"]).lower()
    for phrase in (
        "no pinpoint full-proposal eligibility is claimed",
        "no worldshepherd nonlinear mems imu",
        "gps-quality inertial navigation",
        "does not establish partner interest",
        "cannot substitute for the core sensor physics",
    ):
        assert phrase in boundary
