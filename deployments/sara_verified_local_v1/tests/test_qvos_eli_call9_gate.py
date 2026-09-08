import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "qvos_eli_call9_gate_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_call9_full_offer_and_elba_availability_remain_pending():
    payload = _payload()
    assert payload["call"]["launch_date"] == "2026-09-15"
    assert payload["call"]["close_date"] == "2026-10-20"
    assert payload["call"]["full_offer_status"] == "PENDING_CALL_LAUNCH"
    assert payload["lead_instrument_candidate"]["call9_availability"] == "NOT_YET_CONFIRMED"


def test_eli_account_and_submission_state_fail_closed():
    state = _payload()["access_state"]
    assert state["eli_user_registry_account"] == "UNVERIFIED_IN_CONNECTED_GMAIL_AND_GOOGLE_DRIVE"
    assert state["uos_access"] == "UNVERIFIED"
    assert state["proposal_created"] is False
    assert state["proposal_submitted"] is False
    assert state["instrument_scientist_contacted"] is False


def test_commissioning_milestone_is_not_promoted_to_user_guarantee():
    context = _payload()["laser_context"]
    portal = context["portal_user_parameters"]
    milestone = context["august_2026_commissioning_milestone"]
    assert portal["guaranteed_peak_power_PW"] == 0.37
    assert portal["best_effort_peak_power_PW"] == 0.55
    assert milestone["peak_power_PW"] == 0.95
    assert milestone["status"] == "COMMISSIONING_MILESTONE_NOT_USER_GUARANTEED_PARAMETER"
    assert "Never substitute" in context["rule"]


def test_qvos_does_not_claim_physical_or_new_physics_validation():
    science = _payload()["qvos_scientific_position"]
    assert science["physical_strong_field_experiment_evidence"] == "NONE"
    assert science["eli_integration_evidence"] == "NONE"
    assert science["novel_physics_claimed"] is False
    forbidden = {item.lower() for item in science["do_not_pitch_as"]}
    assert "zero_point_energy_extraction" in forbidden
    assert "reactionless_propulsion" in forbidden


def test_instrument_score_is_not_used_before_full_offer():
    scorecard = _payload()["instrument_selection_scorecard"]
    assert sum(
        value
        for key, value in scorecard.items()
        if key.endswith("_weight")
    ) == 100
    assert scorecard["status"] == "DO_NOT_SCORE_UNTIL_FULL_CALL9_OFFER_IS_PUBLISHED"
    assert "not beamtime acceptance probability" in scorecard["note"].lower()


def test_claims_boundary_preserves_call_and_bsm_uncertainty():
    boundary = " ".join(_payload()["claims_boundary"]).lower()
    for phrase in (
        "full offer is not yet published",
        "does not establish call-9 availability",
        "0.95-pw commissioning milestone is not represented as a guaranteed",
        "does not claim physical strong-field-qed validation",
        "independent replication",
    ):
        assert phrase in boundary
