from lab_interop_g1 import CLAIM_STATE, FAULTS, evaluate, run_case


def test_nominal_completes():
    r = run_case()
    assert r["events"][-1]["outcome"] == "SUCCESS"
    assert r["claim_state"] == "SIMULATED_ONLY"


def test_all_faults_fail_closed():
    for fault in FAULTS:
        r = run_case(fault)
        assert r["safe_state"], fault
        assert r["reason"] != "nominal"


def test_semantic_unit_mismatch_denied():
    r = run_case("F7_UNIT_MISMATCH")
    assert r["events"][0]["decision"] == "DENY"
    assert r["reason"] == "semantic_unit_mismatch"


def test_replay_denied():
    r = run_case("F9_REPLAY")
    assert r["events"][0]["decision"] == "DENY"


def test_evidence_is_hash_bound():
    r = run_case("F2_DROPPED_TELEMETRY")
    assert len(r["configuration_digest"]) == 64
    assert len(r["evidence_digest"]) == 64
    assert any(e["kind"] == "missing_data" for e in r["events"])


def test_claims_remain_bounded():
    r = run_case()
    assert CLAIM_STATE == "SIMULATED_ONLY"
    assert not any(r["claims"].values())


def test_g1_pass_requires_all_three_dimensions():
    r = evaluate()
    assert r["scores"] == {"I_C": 1.0, "I_S": 1.0, "I_E": 1.0}
    assert r["I_overall"] == 1.0
    assert r["gate"] == "G1_SYNTHETIC_PASS"
