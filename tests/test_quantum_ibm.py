import pytest

from worldshepherd_sara.quantum_external_evidence import validate_external_evidence
from worldshepherd_sara.quantum_ibm import IBMQPUResult, build_sara_qpu_external_evidence, run_bell_on_ibm_hardware


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def test_ibm_hardware_adapter_requires_injected_token_before_network_access():
    with pytest.raises(ValueError, match="token"):
        run_bell_on_ibm_hardware(token="")


def test_ibm_hardware_adapter_rejects_invalid_shots_before_network_access():
    with pytest.raises(ValueError, match="shots"):
        run_bell_on_ibm_hardware(token="placeholder", shots=0)


def _hardware_result(**overrides):
    payload = dict(
        provider="IBM Quantum Platform",
        backend="ibm_test_backend",
        job_id="job-123",
        shots=4096,
        counts={"00": 2010, "11": 1990, "01": 48, "10": 48},
        correlated_fraction=4000 / 4096,
        circuit_digest=SHA_A,
        transpiled_circuit_digest=SHA_B,
        result_digest=SHA_C,
        calibration_id="2026-08-17T15:00:00Z",
        backend_num_qubits=127,
        native_operations=("cx", "measure", "rz", "sx", "x"),
        executed_at_utc="2026-08-17T15:45:00Z",
        backend_properties_digest=SHA_A,
        job_metrics={
            "timestamps": {
                "created": "2026-08-17T15:40:00Z",
                "running": "2026-08-17T15:42:00Z",
                "finished": "2026-08-17T15:45:00Z",
            },
            "usage": {"qpu_charge_time_seconds": 2.0},
        },
        job_metrics_digest=SHA_B,
        queue_seconds=120.0,
        platform_latency_seconds=300.0,
        wall_latency_seconds=301.0,
        qpu_charge_time_seconds=2.0,
        runtime_version="0.47.0",
    )
    payload.update(overrides)
    return IBMQPUResult(**payload)


def test_open_plan_ibm_result_converts_to_structurally_valid_sara_gate_record():
    evidence = build_sara_qpu_external_evidence(
        _hardware_result(),
        plan_name="open",
        cost_usd=0.0,
    )
    decision = validate_external_evidence(evidence)

    assert decision.accepted_for_intake is True
    assert evidence.project_id == "SARA-QRF"
    assert evidence.metadata["campaign_gate_id"] == "SARA-QRF-EXT-01"
    assert evidence.metadata["queue_seconds"] == "120.0"
    assert evidence.cost_usd == 0.0
    assert evidence.latency_seconds == 300.0
    assert evidence.backend_or_device == "ibm_test_backend"


def test_ibm_campaign_record_refuses_missing_backend_properties_digest():
    with pytest.raises(ValueError, match="properties digest"):
        build_sara_qpu_external_evidence(
            _hardware_result(backend_properties_digest=None),
            plan_name="open",
            cost_usd=0.0,
        )
