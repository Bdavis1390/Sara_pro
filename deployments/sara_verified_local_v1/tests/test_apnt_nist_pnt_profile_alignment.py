import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "apnt_nist_pnt_profile_alignment_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_reference_state_and_closed_comment_period_are_preserved():
    payload = _payload()
    reference = payload["reference"]
    assert reference["document"].startswith("NIST IR 8323 Rev. 2 ipd")
    assert reference["published"] == "2026-05-06"
    assert reference["comment_deadline"] == "2026-07-06"
    assert reference["comment_period_state"] == "CLOSED"
    assert payload["alignment_state"] == "DRAFT_ALIGNMENT_ONLY_NOT_CONFORMANCE"


def test_all_six_csf_functions_are_mapped_with_explicit_gaps():
    payload = _payload()
    functions = payload["profile_functions"]
    assert [item["function"] for item in functions] == [
        "GOVERN",
        "IDENTIFY",
        "PROTECT",
        "DETECT",
        "RESPOND",
        "RECOVER",
    ]
    assert all(item["worldshepherd_existing"] for item in functions)
    assert all(item["missing_or_unverified"] for item in functions)


def test_physical_third_party_and_nist_claims_remain_fail_closed():
    payload = _payload()
    boundary = " ".join(payload["claims_boundary"]).lower()
    gates = " ".join(payload["promotion_gates"]).lower()
    assert "not nist conformance" in boundary
    assert "synthetic software evidence" in boundary
    assert "third-party" in boundary
    assert "do not claim production pnt cybersecurity readiness" in gates
    assert "do not claim physical apnt accuracy" in gates


def test_next_tevv_campaign_extends_beyond_simple_gnss_degradation():
    events = _payload()["next_tevv_events"]
    joined = " ".join(events).lower()
    assert "third-party" in joined
    assert "spoofing" in joined
    assert "timing" in joined
    assert "common-mode" in joined
    assert "re-entry" in joined
    assert "provenance" in joined
