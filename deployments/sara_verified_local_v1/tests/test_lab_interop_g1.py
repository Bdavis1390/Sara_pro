from worldshepherd_sara.lab_interop_g1 import FAULTS, evaluate_g1, run_g1_case


def test_g1_nominal_path_completes():
    report = run_g1_case()
    assert report["events"][-1]["outcome"] == "SUCCESS"
    assert report["capability_status"] == "SIMULATED_ONLY"


def test_g1_all_faults_are_fail_closed():
    for fault in FAULTS:
        report = run_g1_case(fault)
        assert report["safe_state"] is True, fault


def test_g1_semantic_mismatch_is_rejected():
    report = run_g1_case("F7_UNIT_MISMATCH")
    assert report["events"][0]["decision"] == "DENY"
    assert report["reason"] == "semantic_unit_mismatch"


def test_g1_missing_data_is_explicit():
    report = run_g1_case("F2_DROPPED_TELEMETRY")
    assert any(event["kind"] == "missing_data" for event in report["events"])


def test_g1_hashes_and_claims_are_bounded():
    report = run_g1_case("F5_SENSOR_DISAGREEMENT")
    assert report["configuration_digest"].startswith("sha256:")
    assert report["evidence_digest"].startswith("sha256:")
    assert not any(report["claims"].values())


def test_g1_gate_uses_weakest_interoperability_dimension():
    report = evaluate_g1()
    assert report["scores"] == {"I_C": 1.0, "I_S": 1.0, "I_E": 1.0}
    assert report["I_overall"] == 1.0
    assert report["gate"] == "G1_SYNTHETIC_PASS"
    assert report["physical_validation_performed"] is False
