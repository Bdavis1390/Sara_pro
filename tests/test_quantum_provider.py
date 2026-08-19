from worldshepherd_sara.quantum_provider import GateModelExecutionRecord, as_qrf_run_evidence, validate_gate_model_execution


def _d(ch: str) -> str:
    return "sha256:" + ch * 64


def test_provider_neutral_record_accepts_real_qpu_execution():
    record = GateModelExecutionRecord(
        provider="IonQ Quantum Cloud",
        backend="qpu.forte-1",
        modality="trapped_ion_gate_model",
        job_id="job-1",
        collected_utc="2026-08-17T17:00:00Z",
        shots=1000,
        canonical_program_digest=_d("a"),
        compiled_program_digest=_d("b"),
        result_digest=_d("c"),
        configuration_digest=_d("d"),
        raw_artifact_digest=_d("e"),
        outcome_distribution={"00": 0.49, "11": 0.51},
        queue_seconds=2.0,
        latency_seconds=8.0,
        cost_usd=1.0,
        backend_properties_digest=_d("f"),
    )
    accepted, reasons = validate_gate_model_execution(record)
    assert accepted is True
    assert reasons == ()
    evidence = as_qrf_run_evidence(
        record,
        project_id="SARA-QRF",
        experiment_id="IONQ-1",
        algorithm="QRF-BELL-001",
        classical_baseline_id="QRF-BELL-CLASSICAL-001",
    )
    assert evidence.backend.provider == "IonQ Quantum Cloud"
    assert evidence.outcome_distribution["11"] == 0.51


def test_provider_neutral_record_rejects_simulator_and_bad_digest():
    record = GateModelExecutionRecord(
        provider="Any",
        backend="simulator",
        modality="gate_model",
        job_id="job-2",
        collected_utc="2026-08-17T17:00:00Z",
        shots=100,
        canonical_program_digest="bad",
        compiled_program_digest=_d("b"),
        result_digest=_d("c"),
        configuration_digest=_d("d"),
        raw_artifact_digest=_d("e"),
        outcome_distribution={"00": 1.0},
        queue_seconds=0.0,
        latency_seconds=0.1,
        cost_usd=0.0,
    )
    accepted, reasons = validate_gate_model_execution(record)
    assert accepted is False
    assert any("simulator" in reason for reason in reasons)
    assert any("canonical_program_digest" in reason for reason in reasons)
