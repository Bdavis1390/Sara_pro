from worldshepherd_sara.lab_interop_g2 import (
    CAPABILITY_STATUS,
    Fault,
    evaluate_g2,
    run_protocol_case,
)


def test_nominal_protocol_path_succeeds():
    report = run_protocol_case(Fault.NONE)
    assert report["outcome"] == "SUCCESS"
    assert report["capability_status"] == "SIMULATED_ONLY"


def test_timeout_recovers_with_bounded_retry():
    report = run_protocol_case(Fault.TIMEOUT_ONCE)
    assert report["recovered"] is True
    assert [a["event"] for a in report["attempts"]] == ["timeout", "success"]


def test_adapter_restart_requires_state_resync():
    report = run_protocol_case(Fault.ADAPTER_RESTART)
    assert report["recovered"] is True
    assert "state_resync" in [a["event"] for a in report["attempts"]]


def test_version_skew_and_malformed_packets_fail_closed():
    for fault in (Fault.VERSION_SKEW, Fault.MALFORMED_PACKET):
        report = run_protocol_case(fault)
        assert report["safe_halt"] is True
        assert report["outcome"] == "SAFE_HALT"


def test_connection_churn_fails_safe_after_bounded_attempts():
    report = run_protocol_case(Fault.CONNECTION_CHURN)
    assert report["safe_halt"] is True
    assert len(report["attempts"]) == 4


def test_semantic_dictionary_drift_is_detected():
    report = run_protocol_case(Fault.SEMANTIC_DRIFT)
    assert report["semantic_ok"] is False
    assert report["safe_halt"] is True
    assert report["final_reason"] == "semantic_dictionary_drift"


def test_replay_is_rejected_after_valid_execution():
    report = run_protocol_case(Fault.REPLAY)
    assert report["replay_rejected"] is True
    assert report["attempts"][-1]["event"] == "replay_rejected"


def test_evidence_is_hash_bound_and_claims_stay_false():
    report = run_protocol_case(Fault.TIMEOUT_ONCE)
    assert report["configuration_digest"].startswith("sha256:")
    assert report["evidence_digest"].startswith("sha256:")
    assert not any(report["claims"].values())


def test_g2_gate_passes_only_as_simulated_protocol_evidence():
    report = evaluate_g2()
    assert report["gate"] == "G2_PROTOCOL_EMULATOR_PASS"
    assert report["capability_status"] == CAPABILITY_STATUS
    assert report["physical_validation_performed"] is False
    assert report["standards_conformance_claimed"] is False
    assert min(report["scores"].values()) == 1.0
