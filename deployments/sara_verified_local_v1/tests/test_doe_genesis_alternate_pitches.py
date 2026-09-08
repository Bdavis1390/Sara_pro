import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "doe_genesis_alternate_pitch_candidates_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _word_count(text: str) -> int:
    return len(text.split())


def test_alternate_candidates_respect_three_pitch_strategy():
    payload = _payload()
    ranking = payload["internal_ranking"]
    assert len(ranking) == 3
    assert [item["rank"] for item in ranking] == [1, 2, 3]
    assert ranking[0]["topic"] == "Achieving AI-Driven Autonomous Laboratories"
    assert ranking[0]["readiness_score_internal"] > ranking[1]["readiness_score_internal"]
    assert ranking[1]["readiness_score_internal"] >= ranking[2]["readiness_score_internal"]


def test_alternate_pitch_responses_fit_conservative_working_limits():
    payload = _payload()
    limits = payload["working_word_limits"]
    for candidate in payload["candidates"].values():
        for key, response in candidate["responses"].items():
            assert _word_count(response) <= limits[key], (
                f"{candidate['topic']} {key}: {_word_count(response)} > {limits[key]}"
            )


def test_quantum_candidate_does_not_claim_quantum_hardware_or_advantage():
    payload = _payload()
    candidate = payload["candidates"]["topic2_quantum_workflow_assurance"]
    text = " ".join(candidate["responses"].values()).lower()
    assert "does not claim access to validated quantum hardware" in text
    assert "quantum advantage" in text
    assert "rather than claiming new quantum hardware or quantum advantage" in text


def test_materials_candidate_preserves_physical_validation_boundary():
    payload = _payload()
    candidate = payload["candidates"]["topic3_inverse_materials_design"]
    text = " ".join(candidate["responses"].values()).lower()
    assert "does not claim independently validated proprietary alloy performance" in text
    assert "without claiming any worldshepherd material has achieved predicted physical properties" in text


def test_readiness_scores_are_internal_not_award_probabilities():
    payload = _payload()
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert "award probability" in boundary
    assert "topic 4 remains the lead candidate" in boundary
