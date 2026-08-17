from worldshepherd_sara.quantum_closure import generate_closure_packages


def test_every_current_lane_below_97_has_active_closure_package():
    payload = generate_closure_packages()
    assert payload["target"] == 97
    assert len(payload["packages"]) == 7

    for row in payload["packages"]:
        assert row["mission_readiness_score"] < 97
        assert row["gap_to_target"] > 0
        assert row["mission_use_decision"] == "NO_GO_BELOW_97"
        assert row["internal_closure_status"] == "IMPLEMENTED_AND_CI_GATED"
        assert row["mission_closure_status"] == "BLOCKED_ON_EVIDENCE"
        assert row["internal_completed"]
        assert row["external_evidence_required"]
        assert row["closure_sequence"]


def test_closure_packages_do_not_claim_external_evidence_complete():
    payload = generate_closure_packages()
    for row in payload["packages"]:
        combined = " ".join(row["external_evidence_required"]).lower()
        assert "real-qpu" in combined or "sensor" in combined or "physical" in combined or "qpu" in combined
