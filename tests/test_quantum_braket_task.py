from __future__ import annotations

import pytest

from worldshepherd_sara.quantum_braket_task import (
    BraketQuantumTaskRecord,
    build_braket_task_external_evidence,
    execute_braket_bell_task,
    record_from_raw_payload,
    validate_braket_quantum_task,
)
from worldshepherd_sara.quantum_external_evidence import validate_external_evidence


DEVICE = "arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1"
TASK = "arn:aws:braket:us-west-1:123456789012:quantum-task/11111111-2222-3333-4444-555555555555"
SHA = "sha256:" + "a" * 64
PROGRAM = "OPENQASM 3.0; qubit[2] q; bit[2] c; h q[0]; cx q[0], q[1]; c = measure q;"


def _submitted(**metadata_overrides):
    metadata = {
        "quantumTaskArn": TASK,
        "status": "COMPLETED",
        "deviceArn": DEVICE,
        "shots": 1024,
        "numSuccessfulShots": 1024,
        "outputS3Bucket": "ws-qrf-test",
        "outputS3Directory": "qrf/bell/task-id",
        "createdAt": "2026-08-19T16:00:00+00:00",
        "endedAt": "2026-08-19T16:04:00+00:00",
    }
    metadata.update(metadata_overrides)
    return {
        "task_id": TASK,
        "task_metadata": metadata,
        "measurement_counts": {"00": 510, "11": 500, "01": 8, "10": 6},
        "measurement_probabilities": {"00": 510 / 1024, "11": 500 / 1024, "01": 8 / 1024, "10": 6 / 1024},
        "device_name": "Cepheus fixture",
        "device_status_at_submission": "ONLINE",
        "device_snapshot": {"action": "fixture", "qubitCount": 108},
    }


def _submitter(**kwargs):
    assert kwargs["device_arn"] == DEVICE
    assert kwargs["shots"] == 1024
    assert kwargs["s3_location"] == ("ws-qrf-test", "qrf/bell")
    return _submitted()


def test_on_demand_braket_bell_task_retains_frozen_program_provider_and_cost_basis():
    raw = execute_braket_bell_task(
        canonical_program_source=PROGRAM,
        device_arn=DEVICE,
        shots=1024,
        s3_bucket="ws-qrf-test",
        s3_prefix="qrf/bell",
        per_task_usd=0.30,
        per_shot_usd=0.000425,
        pricing_source="https://aws.amazon.com/braket/pricing/",
        submitter=_submitter,
    )
    assert raw["quantum_task_arn"] == TASK
    assert raw["provider"] == "rigetti"
    assert raw["shots_successful"] == 1024
    assert raw["output_s3_uri"] == "s3://ws-qrf-test/qrf/bell/task-id"
    assert raw["canonical_program_digest"].startswith("sha256:")
    assert raw["submission_spec_digest"].startswith("sha256:")
    assert raw["device_snapshot_digest"].startswith("sha256:")
    assert raw["braket_submission_spec"] == [["h", [0]], ["cnot", [0, 1]]]
    assert raw["cost_usd_predeclared_estimate"] == pytest.approx(0.7352)
    assert "estimate" in raw["claim_control"].lower()


def test_braket_task_runtime_rejects_simulator_before_submission():
    with pytest.raises(ValueError, match="QPU"):
        execute_braket_bell_task(
            canonical_program_source=PROGRAM,
            device_arn="arn:aws:braket:us-east-1::device/quantum-simulator/amazon/sv1",
            shots=100,
            s3_bucket="bucket",
            s3_prefix="prefix",
            per_task_usd=0,
            per_shot_usd=0,
            pricing_source="fixture",
            submitter=lambda **_: pytest.fail("submitter must not be called"),
        )


def test_braket_task_runtime_rejects_executed_device_mismatch():
    def wrong_device(**kwargs):
        return _submitted(deviceArn="arn:aws:braket:us-east-1::device/qpu/ionq/Forte-1")

    with pytest.raises(ValueError, match="does not match"):
        execute_braket_bell_task(
            canonical_program_source=PROGRAM,
            device_arn=DEVICE,
            shots=1024,
            s3_bucket="ws-qrf-test",
            s3_prefix="qrf/bell",
            per_task_usd=0.30,
            per_shot_usd=0.000425,
            pricing_source="fixture",
            submitter=wrong_device,
        )


def test_braket_task_runtime_rejects_noncompleted_task():
    def failed(**kwargs):
        return _submitted(status="FAILED")

    with pytest.raises(ValueError, match="did not complete"):
        execute_braket_bell_task(
            canonical_program_source=PROGRAM,
            device_arn=DEVICE,
            shots=1024,
            s3_bucket="ws-qrf-test",
            s3_prefix="qrf/bell",
            per_task_usd=0.30,
            per_shot_usd=0.000425,
            pricing_source="fixture",
            submitter=failed,
        )


def test_raw_task_converts_to_structurally_valid_external_evidence():
    raw = execute_braket_bell_task(
        canonical_program_source=PROGRAM,
        device_arn=DEVICE,
        shots=1024,
        s3_bucket="ws-qrf-test",
        s3_prefix="qrf/bell",
        per_task_usd=0.30,
        per_shot_usd=0.000425,
        pricing_source="fixture",
        submitter=_submitter,
    )
    record = record_from_raw_payload(raw, result_artifact_digest=SHA)
    decision = validate_braket_quantum_task(record)
    assert decision.accepted is True
    assert decision.end_to_end_seconds == 240.0

    evidence = build_braket_task_external_evidence(
        record,
        project_id="SARA-QRF",
        campaign_gate_id="SARA-QRF-EXT-01",
    )
    intake = validate_external_evidence(evidence)
    assert intake.accepted_for_intake is True
    assert evidence.provider_or_lab == "Amazon Braket / rigetti"
    assert evidence.backend_or_device == DEVICE
    assert evidence.job_or_run_id == TASK
    assert evidence.cost_usd == pytest.approx(0.7352)
    assert evidence.metadata["cost_is_estimate_not_invoice"] == "true"


def test_validation_rejects_bad_result_digest_and_zero_successful_shots():
    record = BraketQuantumTaskRecord(
        quantum_task_arn=TASK,
        status="COMPLETED",
        device_arn=DEVICE,
        provider="rigetti",
        created_at="2026-08-19T16:00:00Z",
        ended_at="2026-08-19T16:04:00Z",
        output_s3_uri="s3://bucket/prefix",
        shots_requested=1024,
        shots_successful=0,
        canonical_program_digest=SHA,
        submission_spec_digest=SHA,
        device_snapshot_digest=SHA,
        result_artifact_digest="bad",
        result_distribution={"00": 0.5, "11": 0.5},
        cost_usd=1.0,
        cost_basis="fixture",
        metadata={},
    )
    decision = validate_braket_quantum_task(record)
    assert decision.accepted is False
    assert any("shots_successful" in reason for reason in decision.reasons)
    assert any("result_artifact_digest" in reason for reason in decision.reasons)
