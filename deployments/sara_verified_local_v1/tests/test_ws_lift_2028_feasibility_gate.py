import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "ws_lift_2028_feasibility_gate_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_official_2028_constraints_and_ratio_tbd_are_preserved():
    payload = _payload()
    rules = payload["darpa_2028_announced_constraints"]
    assert rules["aircraft_weight_max_lb"] == 55.0
    assert rules["minimum_payload_lb"] == 220.0
    assert rules["course_nm_total"] == 10.0
    assert rules["loaded_course_nm"] == 8.0
    assert rules["unloaded_course_nm"] == 2.0
    assert rules["ratio_target"] == "TBD_BY_DARPA"


def test_internal_ratio_targets_use_correct_minimum_payload_mass_ceiling():
    payload = _payload()
    for item in payload["worldshepherd_targets"]:
        ratio = item["target_ratio"]
        payload_lb = item["minimum_payload_lb"]
        aircraft_max = item["maximum_aircraft_weight_for_ratio_lb"]
        gross = item["loaded_gross_weight_at_minimum_payload_lb"]
        assert aircraft_max == payload_lb / ratio
        assert gross == payload_lb + aircraft_max


def test_dp2_prime_is_fail_closed_without_empirical_four_to_one_evidence():
    payload = _payload()
    gate = payload["darpa_dp2_capture_gate"]
    assert gate["direct_to_phase_ii_only"] is True
    assert gate["worldshepherd_prime_status"] == "NO_GO_UNTIL_EMPIRICAL_4_TO_1_EVIDENCE_EXISTS"
    assert ">=4:1" in " ".join(payload["near_term_decisions"])


def test_long_range_target_is_not_misrepresented_as_darpa_requirement():
    payload = _payload()
    long_range = payload["long_range_requirement"]
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert long_range["minimum_range_nm"] == 4000.0
    assert long_range["relationship_to_darpa_2028"] == "SEPARATE_WORLDSHEPHERD_MISSION_REQUIREMENT"
    assert "not a darpa lift challenge requirement" in boundary


def test_validation_ladder_requires_physical_evidence_before_high_readiness():
    payload = _payload()
    ladder = payload["validation_ladder"]
    assert ladder[0].startswith("V0:")
    assert any("component bench evidence" in step for step in ladder)
    assert any("completed mission-course demonstration" in step for step in ladder)
    assert any("manufacturing repeatability" in step for step in ladder)
    assert any("certification and production-readiness evidence" in step for step in ladder)


def test_400_to_1_target_remains_extreme_and_unvalidated():
    payload = _payload()
    target = next(item for item in payload["worldshepherd_targets"] if item["target_ratio"] == 400.0)
    assert target["maximum_aircraft_weight_for_ratio_lb"] == 0.55
    assert target["status"] == "EXTREME_TARGET_REQUIRES_FUNDAMENTAL_MASS_ENERGY_AND_STRUCTURE_FEASIBILITY_PROOF"
