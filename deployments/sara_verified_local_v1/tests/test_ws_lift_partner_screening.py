import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "ws_lift_partner_screening_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_partner_screening_has_at_least_five_ranked_candidates():
    payload = _payload()
    candidates = payload["candidates"]
    assert len(candidates) >= 5
    assert [item["rank"] for item in candidates] == list(range(1, len(candidates) + 1))
    assert all(0 <= item["internal_score"] <= 100 for item in candidates)


def test_no_partner_interest_or_commitment_is_claimed():
    payload = _payload()
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert "no interest" in boundary
    assert "teaming agreement" in boundary
    assert "not probabilities" in boundary
    assert all(
        item["outreach_status"] == "NOT_AUTHORIZED_OR_PERFORMED"
        for item in payload["candidates"]
    )


def test_defendtex_incomplete_run_is_preserved():
    payload = _payload()
    defendtex = next(item for item in payload["candidates"] if item["name"] == "DefendTex")
    evidence = defendtex["public_evidence"].lower()
    assert "9.63:1" in evidence
    assert "did not complete a scored run" in evidence
    assert "repeatability" in defendtex["principal_gap_or_risk"].lower()


def test_completed_run_baselines_are_distinguished_from_high_ratio_attempt():
    payload = _payload()
    avidrone = next(item for item in payload["candidates"] if item["name"] == "AVIDrone, Inc.")
    mtech = next(item for item in payload["candidates"] if item["name"] == "MTech Operations, LLC")
    assert "3.84:1" in avidrone["public_evidence"]
    assert "best completed" in avidrone["public_evidence"].lower()
    assert "3.64:1" in mtech["public_evidence"]
    assert "completed" in mtech["public_evidence"].lower()


def test_recommended_sequence_keeps_dp2_prime_fail_closed():
    payload = _payload()
    sequence = " ".join(payload["recommended_sequence"]).lower()
    assert "do not represent worldshepherd as prime" in sequence
    assert ">=4:1" in sequence
    assert "non-confidential" in sequence
