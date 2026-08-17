import pytest

from worldshepherd_sara.quantum_braket import (
    BraketHybridJobRecord,
    build_braket_qpu_external_evidence,
    validate_braket_hybrid_job,
)
from worldshepherd_sara.quantum_external_evidence import validate_external_evidence


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64


def _record(**overrides):
    payload = dict(
        job_arn="arn:aws:braket:us-east-1:123456789012:job/ws-qrf-fixture",
        job_name="ws-qrf-fixture",
        status="COMPLETED",
        device_arn="arn:aws:braket:us-east-1::device/qpu/ionq/Forte-Enterprise-1",
        provider="IonQ",
        created_at="2026-08-17T17:00:00+00:00",
        started_at="2026-08-17T17:02:00+00:00",
        ended_at="2026-08-17T17:05:00+00:00",
        container_image_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/qrf@sha256:fixture",
        container_image_digest=SHA_A,
        source_artifact_digest=SHA_B,
        result_artifact_digest=SHA_C,
        program_digest=SHA_D,
        output_s3_uri="s3://amazon-braket-us-east-1-123456789012/jobs/ws-qrf-fixture/data",
        initial_queue_position="2",
        cost_usd=3.25,
        task_count=2,
        shots_total=2000,
        result_distribution={"00": 1001, "11": 963, "01": 19, "10": 17},
        metadata={"fixture": "true"},
    )
    payload.update(overrides)
    return BraketHybridJobRecord(**payload)


def test_completed_braket_qpu_job_retains_queue_runtime_and_end_to_end_timing():
    decision = validate_braket_hybrid_job(_record())
    assert decision.accepted is True
    assert decision.queue_seconds == 120.0
    assert decision.runtime_seconds == 180.0
    assert decision.end_to_end_seconds == 300.0
    assert decision.job_metadata_digest.startswith("sha256:")


def test_braket_contract_rejects_simulator_as_provider_parity_hardware_evidence():
    decision = validate_braket_hybrid_job(
        _record(device_arn="arn:aws:braket:us-east-1::device/quantum-simulator/amazon/sv1")
    )
    assert decision.accepted is False
    assert any("QPU device ARN" in reason for reason in decision.reasons)


def test_braket_contract_rejects_non_completed_job():
    decision = validate_braket_hybrid_job(_record(status="FAILED"))
    assert decision.accepted is False
    assert any("COMPLETED" in reason for reason in decision.reasons)


def test_braket_contract_requires_retained_container_source_result_and_program_digests():
    decision = validate_braket_hybrid_job(_record(container_image_digest="not-a-digest"))
    assert decision.accepted is False
    assert any("container_image_digest" in reason for reason in decision.reasons)


def test_braket_qpu_record_converts_to_structurally_valid_external_evidence():
    evidence = build_braket_qpu_external_evidence(
        _record(),
        project_id="SARA-QRF",
        campaign_gate_id="SARA-QRF-EXT-02",
    )
    intake = validate_external_evidence(evidence)
    assert intake.accepted_for_intake is True
    assert evidence.provider_or_lab == "Amazon Braket / IonQ"
    assert evidence.metadata["campaign_gate_id"] == "SARA-QRF-EXT-02"
    assert evidence.metadata["container_image_digest"] == SHA_A
    assert evidence.metadata["source_artifact_digest"] == SHA_B
    assert evidence.metadata["program_digest"] == SHA_D
    assert evidence.latency_seconds == 300.0
    assert evidence.cost_usd == 3.25


def test_invalid_braket_job_cannot_be_converted_to_qrf_evidence():
    with pytest.raises(ValueError, match="not evidence-complete"):
        build_braket_qpu_external_evidence(
            _record(status="FAILED"),
            project_id="SARA-QRF",
            campaign_gate_id="SARA-QRF-EXT-02",
        )
