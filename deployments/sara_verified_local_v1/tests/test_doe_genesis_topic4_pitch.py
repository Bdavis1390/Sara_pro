import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "doe_genesis_topic4_pitch_candidate_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _word_count(text: str) -> int:
    return len(text.split())


def test_pitch_candidate_is_bounded_and_not_a_submission_claim():
    payload = _payload()
    assert payload["schema"] == "ws-doe-genesis-pitch-candidate-1"
    assert payload["opportunity"]["pitch_required_before_full_application"] is True
    assert payload["opportunity"]["max_company_pitches"] == 3
    assert payload["applicant"]["formation_status"] == "IN_FORMATION"
    assert payload["applicant"]["award_eligibility_claimed"] is False
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert "not a submitted application" in boundary
    assert "does not claim an operational physical autonomous laboratory" in boundary
    assert "no partner commitment" in boundary


def test_working_pitch_responses_stay_inside_conservative_limits():
    payload = _payload()
    limits = payload["working_word_limits"]
    responses = payload["responses"]
    for key in (
        "summary_topic_mission_alignment",
        "technical_promise",
        "commercialization_potential",
        "team_qualifications",
    ):
        assert _word_count(responses[key]) <= limits[key], (
            f"{key}: {_word_count(responses[key])} > {limits[key]}"
        )


def test_pitch_preserves_current_evidence_and_registration_gaps():
    payload = _payload()
    applicant = payload["applicant"]
    assert applicant["sam_status"] == "UNVERIFIED"
    assert applicant["uei_status"] == "UNVERIFIED"
    assert applicant["sba_company_registry_status"] == "UNVERIFIED"
    assert applicant["doe_application_hub_status"] == "UNVERIFIED"

    team = payload["responses"]["team_qualifications"].lower()
    assert "in formation" in team
    assert "does not claim an operational physical autonomous laboratory" in team
    assert "national laboratory integration" in team


def test_phase_i_plan_is_falsifiable_and_keeps_ai_behind_execution_boundary():
    payload = _payload()
    plan = " ".join(payload["phase_i_measurement_plan"]).lower()
    for required in (
        "deterministic experiment replay",
        "false promotion rate",
        "hidden-ground-truth recovery",
        "hardware-interface-in-the-loop",
        "without granting the ai autonomous consequential execution authority",
    ):
        assert required in plan
