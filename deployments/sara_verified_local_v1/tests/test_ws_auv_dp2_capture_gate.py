import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "fixtures" / "ws_auv_dp2_capture_gate_v1.json"
MISSION = ROOT / "fixtures" / "auv_underwater_mission_synthetic_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_dp2_prime_is_fail_closed_with_current_evidence():
    payload = _load(GATE)
    decision = payload["capture_decision"]
    assert payload["opportunity"]["direct_to_phase_ii_only"] is True
    assert decision["prime_status"] == "NO_GO_WITH_CURRENT_EVIDENCE"
    assert decision["partner_status"] == "HIGH_PRIORITY_PARTNER_LANE"
    assert len(decision["minimum_partner_evidence_needed"]) >= 5


def test_all_three_darpa_feasibility_domains_are_explicitly_accounted_for():
    payload = _load(GATE)
    domains = {item["domain"]: item for item in payload["darpa_required_feasibility_domains"]}
    assert set(domains) == {
        "vehicle_dynamics_and_hydrodynamic_modeling",
        "acoustic_characterization_and_localization",
        "formation_stability_and_communication_resilience",
    }
    assert domains["vehicle_dynamics_and_hydrodynamic_modeling"]["worldshepherd_status"].startswith("GAP")
    assert domains["acoustic_characterization_and_localization"]["worldshepherd_status"].startswith("GAP")
    assert domains["formation_stability_and_communication_resilience"]["worldshepherd_status"] == "PARTIAL_SYNTHETIC_SOFTWARE_RELEVANCE_ONLY"


def test_existing_worldshepherd_evidence_is_not_misclassified_as_physical_auv_validation():
    payload = _load(GATE)
    evidence = payload["existing_worldshepherd_evidence"]
    assert any(item["artifact"] == "apnt_destroyer_strait_v1.json" for item in evidence)
    assert any(item["artifact"] == "hmaa_link_loss_scenario.json" for item in evidence)
    assert any(item["artifact"] == "mission_replay_synthetic_v1.json" for item in evidence)
    for item in evidence:
        assert "PHYSICAL_VALIDATION" not in item["status"]


def test_underwater_fixture_is_explicitly_synthetic_and_policy_gated():
    payload = _load(MISSION)
    boundary = " ".join(payload["claims_boundary"]).lower()
    assert payload["classification"] == "UNCLASSIFIED_SYNTHETIC_FIXTURE"
    assert "synthetic underwater mission assurance scenario only" in boundary
    assert "does not validate navigation accuracy" in boundary
    assert "subject to policy authorization" in boundary


def test_underwater_scenario_preserves_degraded_navigation_and_stale_data_behavior():
    payload = _load(MISSION)
    states = {item["expected_state"]: item for item in payload["timeline"]}
    degraded = states["DEGRADED_NAV_AND_COMMS"]
    local = states["LOCAL_AUTONOMY_ONLY"]
    assert degraded["communications"]["acoustic_mesh"] == "DEGRADED"
    assert local["communications"]["acoustic_mesh"] == "INTERMITTENT"
    assert local["collaborative_sensor_data"]["freshness_state"] == "STALE"
    assert "defer_collaborative_target_update" in local["proposed_actions"]
    assert "log_policy_decision" in local["proposed_actions"]


def test_surface_reconciliation_preserves_conflict_and_review_controls():
    payload = _load(MISSION)
    surface = next(item for item in payload["timeline"] if item["expected_state"] == "SURFACE_RECONCILIATION")
    assert "flag_conflicting_observations" in surface["proposed_actions"]
    assert "require_review_before_model_update" in surface["proposed_actions"]
    metrics = payload["qualification_metrics"]
    assert "surface_reconciliation_preserves_conflicts" in metrics
    assert "mission_replay_complete" in metrics
