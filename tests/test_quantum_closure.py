from worldshepherd_sara.quantum_closure import generate_closure_packages


def test_every_current_lane_below_97_is_either_active_closure_or_held():
    payload = generate_closure_packages()
    assert payload["target"] == 97
    assert len(payload["packages"]) == 7

    for row in payload["packages"]:
        assert row["mission_readiness_score"] < 97
        assert row["gap_to_target"] > 0
        assert row["internal_closure_status"] == "IMPLEMENTED_AND_CI_GATED"
        assert row["internal_completed"]
        if row["project_id"] == "WS-GLOB":
            assert row["mission_use_decision"] == "NO_GO_QUANTUM_EXECUTION_CLASSICAL_DOMINATES"
            assert row["closure_status"] == "QUANTUM_EXECUTION_NOT_JUSTIFIED"
            assert row["mission_closure_status"] == "HELD_CLASSICAL_DOMINANCE"
            assert row["external_evidence_required"] == []
            assert row["closure_sequence"] == ()
        else:
            assert row["mission_use_decision"] == "NO_GO_BELOW_97"
            assert row["mission_closure_status"] == "BLOCKED_ON_EVIDENCE"
            assert row["external_evidence_required"]
            assert row["closure_sequence"]


def test_active_closure_packages_do_not_claim_external_evidence_complete():
    payload = generate_closure_packages()
    for row in payload["packages"]:
        if row["project_id"] == "WS-GLOB":
            continue
        combined = " ".join(row["external_evidence_required"]).lower()
        assert "real-qpu" in combined or "sensor" in combined or "physical" in combined or "qpu" in combined or "full-wave" in combined or "mission-relevant" in combined
