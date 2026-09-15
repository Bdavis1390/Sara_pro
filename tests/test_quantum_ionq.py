from worldshepherd_sara.quantum_ionq import bell_payload, run_bell_on_ionq_hardware, build_sara_qpu_external_evidence
from worldshepherd_sara.quantum_provider import validate_gate_model_execution


def test_bell_payload_rejects_simulator():
    try:
        bell_payload(backend="simulator", shots=100)
    except ValueError as exc:
        assert "qpu.*" in str(exc)
    else:
        raise AssertionError("simulator should be rejected")


def test_mocked_ionq_qpu_execution_normalizes_to_provider_record():
    calls = []

    def fake(token, method, path, payload=None):
        calls.append((method, path))
        if method == "POST" and path == "/jobs":
            return {"id": "job-123", "status": "submitted"}
        if path == "/jobs/job-123":
            return {
                "id": "job-123",
                "status": "completed",
                "backend": "qpu.forte-1",
                "dry_run": False,
                "project_id": "project-1",
                "submitted_at": "2026-08-17T17:00:00Z",
                "started_at": "2026-08-17T17:00:02Z",
                "completed_at": "2026-08-17T17:00:08Z",
                "execution_duration_ms": 5000,
                "shots": 1000,
                "stats": {"qubits": 2, "gate_counts": {"1q": 1, "2q": 1}},
                "settings": {"compilation": {}},
                "output": {"compilation": {"qubit_map": [0, 1]}},
            }
        if path.endswith("/results/probabilities"):
            return {"0": 0.49, "3": 0.51}
        if path.endswith("/cost"):
            return {"actual_cost": 1.25}
        if path == "/backends/qpu.forte-1":
            return {"backend": "qpu.forte-1", "characterization_id": "char-1", "degraded": False}
        raise AssertionError((method, path))

    result = run_bell_on_ionq_hardware(
        token="runtime-only-token",
        backend="qpu.forte-1",
        shots=1000,
        poll_seconds=0.1,
        timeout_seconds=1.0,
        request_json=fake,
    )
    assert result.job_id == "job-123"
    assert result.queue_seconds == 2.0
    assert result.latency_seconds == 8.0
    assert result.probabilities == {"00": 0.49, "11": 0.51}
    assert result.cost_usd == 1.25
    accepted, reasons = validate_gate_model_execution(result.provider_record())
    assert accepted is True
    assert reasons == ()

    external = build_sara_qpu_external_evidence(result)
    assert external.provider_or_lab == "IonQ Quantum Cloud"
    assert external.backend_or_device == "qpu.forte-1"
    assert external.metadata["campaign_gate_id"] == "SARA-QRF-EXT-01"
    assert ("GET", "/jobs/job-123/results/probabilities") in calls
