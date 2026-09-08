import json
from pathlib import Path

from worldshepherd_sara.apnt import derive_apnt_decision


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "apnt_nist_adversarial_gap_suite_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_is_synthetic_negative_evidence_not_capability_claim():
    payload = _payload()
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert payload["classification"] == "UNCLASSIFIED_SYNTHETIC_FIXTURE"
    assert "synthetic" in boundary
    assert "not derived from real" in boundary
    assert "failing current baseline" in boundary
    assert "anti-spoofing" in boundary
    assert "promotion" in payload["promotion_gate"].lower()


def test_current_baseline_intentionally_misses_profile_relevant_blind_spots():
    payload = _payload()
    observed = {}

    for scenario in payload["scenarios"]:
        decision = derive_apnt_decision(scenario["source_state"])
        observed[scenario["scenario_id"]] = decision.operational_state

        assert scenario["current_baseline_expected_to_detect"] is False
        assert decision.operational_state != scenario["expected_safe_awareness_state"]
        assert decision.operational_state == "NORMAL"

    assert set(observed) == {
        "coherent_spoofing_nominal_health",
        "timing_offset_only",
        "common_mode_failure_indicator",
        "missing_source_provenance",
    }


def test_future_signal_requirements_cover_consistency_timing_dependency_and_provenance():
    payload = _payload()
    required = {
        item["scenario_id"]: item["required_future_signal"].lower()
        for item in payload["scenarios"]
    }
    assert "consistency" in required["coherent_spoofing_nominal_health"]
    assert "timing" in required["timing_offset_only"]
    assert "dependency" in required["common_mode_failure_indicator"]
    assert "provenance" in required["missing_source_provenance"]


def test_profile_gap_suite_does_not_silently_change_existing_apnt_logic():
    nominal = {
        "gnss_primary": {"health": "NOMINAL", "confidence": 0.98},
        "ins_primary": {"health": "NOMINAL", "confidence": 0.92},
        "alt_pnt_1": {"health": "AVAILABLE", "confidence": 0.80},
    }
    decision = derive_apnt_decision(nominal)
    assert decision.operational_state == "NORMAL"
    assert decision.recovery_options == ()
