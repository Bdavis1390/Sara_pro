import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "doe_genesis_topic4_pitch_candidate_v2.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _word_count(text: str) -> int:
    return len(text.split())


def test_verified_pitch_limits_are_enforced():
    payload = _payload()
    limits = payload["opportunity"]["verified_pitch_word_limits"]
    responses = payload["responses"]
    for key, limit in limits.items():
        assert _word_count(responses[key]) <= limit, (
            f"{key}: {_word_count(responses[key])} > {limit}"
        )


def test_red_team_prior_art_prevents_duplicate_novelty_claims():
    payload = _payload()
    findings = " ".join(item["finding"] + " " + item["implication"] for item in payload["red_team_findings"]).lower()
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert "american science cloud" in findings
    assert "model access gateway" in findings
    assert "madsci" in findings
    assert "more than a dozen self-driving laboratories" in findings
    assert "does not claim invention of autonomous laboratories" in boundary


def test_pitch_differentiates_as_assurance_plane():
    payload = _payload()
    summary = payload["responses"]["summary_topic_mission_alignment"].lower()
    technical = payload["responses"]["technical_promise"].lower()
    commercial = payload["responses"]["commercialization_potential"].lower()
    assert "independent experiment-assurance layer" in summary
    assert "assurance plane, not another laboratory scheduler" in technical
    assert "existing platforms" in commercial
    assert "replay" in commercial
    assert "falsification" in commercial


def test_current_registration_and_physical_evidence_gaps_remain_visible():
    payload = _payload()
    applicant = payload["applicant"]
    for key in (
        "sam_status",
        "uei_status",
        "sba_company_registry_status",
        "doe_application_hub_status",
    ):
        assert applicant[key] == "UNVERIFIED"
    assert applicant["award_eligibility_claimed"] is False
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert "does not claim an operational physical autonomous laboratory" in boundary
    assert "no partner commitment" in boundary
    assert "customer willingness-to-pay evidence" in boundary


def test_phase_i_go_no_go_metrics_do_not_claim_physical_validation():
    payload = _payload()
    metrics = payload["phase_i_go_no_go_metrics"]
    assert len(metrics) >= 5
    assert any(item["metric"] == "false_promotion_rate" for item in metrics)
    assert any(item["metric"] == "experiment_cycle_overhead" for item in metrics)
    for item in metrics:
        assert "PHYSICAL" not in item["scope"]
