from pathlib import Path

from worldshepherd_sara.quantum_alti_structure import sha256_bytes
from worldshepherd_sara.quantum_external_evidence import ExternalEvidenceRecord, ExternalEvidenceType
from worldshepherd_sara.quantum_external_ingest import (
    ArtifactBinding,
    ExternalEvidenceEnvelope,
    evaluate_external_evidence_batch,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64


def _sara_record(raw_digest: str, gate_id: str = "SARA-QRF-EXT-01") -> ExternalEvidenceRecord:
    return ExternalEvidenceRecord(
        project_id="SARA-QRF",
        evidence_type=ExternalEvidenceType.QPU_EXECUTION,
        source_id="ibm-quantum-platform:job-fixture",
        raw_artifact_digest=raw_digest,
        collected_utc="2026-08-17T16:30:00Z",
        provider_or_lab="IBM Quantum Platform fixture",
        configuration_digest=SHA_A,
        result_digest=SHA_B,
        job_or_run_id="job-fixture",
        backend_or_device="ibm-fixture-backend",
        latency_seconds=10.0,
        cost_usd=0.0,
        environment="remote_cloud_qpu",
        metadata={
            "campaign_gate_id": gate_id,
            "test_protocol_digest": SHA_A,
            "program_digest": SHA_B,
            "transpiled_program_digest": SHA_C,
            "backend_properties_digest": SHA_A,
            "queue_seconds": "2.0",
            "failure_mode": "none_observed",
        },
    )


def test_valid_current_gate_record_requires_local_raw_rehash(tmp_path):
    raw = tmp_path / "ibm-job.json"
    raw.write_text('{"job":"fixture"}', encoding="utf-8")
    record = _sara_record(sha256_bytes(raw.read_bytes()))
    envelope = ExternalEvidenceEnvelope(
        record=record,
        artifact_bindings=(ArtifactBinding("raw_artifact_digest", str(raw)),),
    )

    decision = evaluate_external_evidence_batch([envelope], base_dir=tmp_path)

    assert decision.project_id == "SARA-QRF"
    assert decision.current_gate_id == "SARA-QRF-EXT-01"
    assert decision.records_accepted_for_campaign_evaluation == 1
    assert decision.campaign_gate_satisfied is True
    assert decision.ready_for_technical_review is True
    assert decision.achieved_stage == "single_external_hardware"
    assert decision.next_gate_id == "SARA-QRF-EXT-02"
    assert decision.record_decisions[0].raw_artifact_verified is True


def test_later_gate_record_is_rejected_even_when_raw_artifact_matches(tmp_path):
    raw = tmp_path / "later.json"
    raw.write_text('{"job":"later"}', encoding="utf-8")
    record = _sara_record(sha256_bytes(raw.read_bytes()), gate_id="SARA-QRF-EXT-02")
    envelope = ExternalEvidenceEnvelope(record, (ArtifactBinding("raw_artifact_digest", str(raw)),))

    decision = evaluate_external_evidence_batch([envelope], base_dir=tmp_path)

    assert decision.ready_for_technical_review is False
    assert decision.records_accepted_for_campaign_evaluation == 0
    assert decision.achieved_stage == "integrated_simulation"
    assert decision.next_gate_id == "SARA-QRF-EXT-01"
    assert decision.record_decisions[0].current_gate_match is False
    assert any("does not match current active gate" in reason for reason in decision.record_decisions[0].reasons)


def test_declared_raw_digest_without_binding_is_rejected(tmp_path):
    raw = tmp_path / "unbound.json"
    raw.write_text("unbound", encoding="utf-8")
    record = _sara_record(sha256_bytes(raw.read_bytes()))
    envelope = ExternalEvidenceEnvelope(record, ())

    decision = evaluate_external_evidence_batch([envelope], base_dir=tmp_path)

    assert decision.ready_for_technical_review is False
    assert decision.record_decisions[0].raw_artifact_verified is False
    assert any("must have a local artifact binding" in reason for reason in decision.record_decisions[0].reasons)


def test_mutated_raw_artifact_is_rejected(tmp_path):
    raw = tmp_path / "mutated.json"
    raw.write_text("original", encoding="utf-8")
    digest = sha256_bytes(raw.read_bytes())
    record = _sara_record(digest)
    raw.write_text("mutated", encoding="utf-8")
    envelope = ExternalEvidenceEnvelope(record, (ArtifactBinding("raw_artifact_digest", str(raw)),))

    decision = evaluate_external_evidence_batch([envelope], base_dir=tmp_path)

    assert decision.ready_for_technical_review is False
    verification = decision.record_decisions[0].artifact_verifications[0]
    assert verification.verified is False
    assert verification.expected_digest == digest
    assert verification.actual_digest != digest


def test_mixed_project_batch_is_rejected_before_campaign_evaluation(tmp_path):
    raw = tmp_path / "mixed.json"
    raw.write_text("mixed", encoding="utf-8")
    digest = sha256_bytes(raw.read_bytes())
    sara = ExternalEvidenceEnvelope(
        _sara_record(digest),
        (ArtifactBinding("raw_artifact_digest", str(raw)),),
    )
    apnt_record = ExternalEvidenceRecord(
        project_id="WS-APNT",
        evidence_type=ExternalEvidenceType.QUANTUM_SENSOR,
        source_id="sensor-fixture",
        raw_artifact_digest=digest,
        collected_utc="2026-08-17T16:30:00Z",
        provider_or_lab="sensor lab fixture",
        configuration_digest=SHA_A,
        calibration_id="cal-fixture",
        truth_reference_id="truth-fixture",
        uncertainty=0.1,
        backend_or_device="sensor-fixture",
        environment="calibration_lab",
        metadata={"campaign_gate_id": "WS-APNT-EXT-02"},
    )
    apnt = ExternalEvidenceEnvelope(
        apnt_record,
        (ArtifactBinding("raw_artifact_digest", str(raw)),),
    )

    decision = evaluate_external_evidence_batch([sara, apnt], base_dir=tmp_path)

    assert decision.project_id is None
    assert decision.ready_for_technical_review is False
    assert decision.records_accepted_for_campaign_evaluation == 0
    assert all(any("exactly one project_id" in reason for reason in row.reasons) for row in decision.record_decisions)
