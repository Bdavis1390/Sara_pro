"""Executable conformance suite for the draft Quantum Mission Evidence Profile.

The suite uses controlled fixtures to prove fail-closed governance behavior. Passing
these tests validates implementation behavior only; it is not external certification,
real-provider evidence, or mission readiness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from worldshepherd_sara.quantum_braket import BraketHybridJobRecord, build_braket_qpu_external_evidence, validate_braket_hybrid_job
from worldshepherd_sara.quantum_ddil_evidence import acknowledge_delayed_sync, create_ddil_custody, custody_identity_digest, validate_ddil_custody
from worldshepherd_sara.quantum_external_evidence import ExternalEvidenceRecord, ExternalEvidenceType, validate_external_evidence
from worldshepherd_sara.quantum_external_ingest import ArtifactBinding, ExternalEvidenceEnvelope, evaluate_external_evidence_batch
from worldshepherd_sara.quantum_external_review import ExternalEvidenceTechnicalReview, evaluate_technical_review, ingest_decision_digest
from worldshepherd_sara.quantum_readiness import BackendClass, EvidenceLevel, QuantumBackendRecord, QuantumDomain, QuantumRunEvidence, evaluate_cross_backend_reproducibility


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
SHA_C = "sha256:" + "c" * 64
SHA_D = "sha256:" + "d" * 64


@dataclass(frozen=True)
class ProfileConformanceCase:
    case_id: str
    title: str
    passed: bool
    expected_behavior: str
    observed_behavior: str
    claim_control: str


@dataclass(frozen=True)
class ProfileConformanceReport:
    profile: str
    profile_version: str
    passed: bool
    cases_total: int
    cases_passed: int
    cases: tuple[ProfileConformanceCase, ...]
    claim_control: str


def _sha(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _sara_record(*, raw_digest: str, gate_id: str = "SARA-QRF-EXT-01", result_digest: str = SHA_C) -> ExternalEvidenceRecord:
    return ExternalEvidenceRecord(
        project_id="SARA-QRF",
        evidence_type=ExternalEvidenceType.QPU_EXECUTION,
        source_id="fixture:qpu:job-001",
        raw_artifact_digest=raw_digest,
        collected_utc="2026-08-17T17:30:00Z",
        provider_or_lab="fixture-provider",
        configuration_digest=SHA_A,
        repeat_count=1,
        result_digest=result_digest,
        job_or_run_id="job-001",
        backend_or_device="fixture-qpu-a",
        latency_seconds=12.5,
        cost_usd=0.0,
        environment="remote_cloud_qpu",
        metadata={
            "campaign_gate_id": gate_id,
            "test_protocol_digest": SHA_A,
            "program_digest": SHA_B,
            "transpiled_program_digest": SHA_C,
            "backend_properties_digest": SHA_D,
            "queue_seconds": "2.5",
            "failure_mode": "none_observed",
        },
    )


def _qpu_run(*, run_id: str, provider: str, backend: str, result_digest: str, distribution: dict[str, float]) -> QuantumRunEvidence:
    return QuantumRunEvidence(
        project_id="SARA-QRF",
        experiment_id=run_id,
        domain=QuantumDomain.COMPUTING,
        evidence_level=EvidenceLevel.QPU_EXECUTED,
        backend=QuantumBackendRecord(provider=provider, backend=backend, backend_class=BackendClass.QPU),
        algorithm="QRF-BELL-001",
        classical_baseline_id="bell-classical-reference-v1",
        qasm_or_qir_digest="sha256:" + "1" * 64,
        result_digest=result_digest,
        outcome_distribution=distribution,
    )


def _braket_fixture(*, device_arn: str | None = None) -> BraketHybridJobRecord:
    return BraketHybridJobRecord(
        job_arn="arn:aws:braket:us-east-1:123456789012:job/ws-qrf-conformance",
        job_name="ws-qrf-conformance",
        status="COMPLETED",
        device_arn=device_arn or "arn:aws:braket:us-east-1::device/qpu/ionq/Forte-Enterprise-1",
        provider="IonQ",
        created_at="2026-08-17T17:00:00+00:00",
        started_at="2026-08-17T17:02:00+00:00",
        ended_at="2026-08-17T17:05:00+00:00",
        container_image_uri="123456789012.dkr.ecr.us-east-1.amazonaws.com/qrf@sha256:fixture",
        container_image_digest=SHA_A,
        source_artifact_digest=SHA_B,
        result_artifact_digest=SHA_C,
        program_digest=SHA_D,
        output_s3_uri="s3://fixture-bucket/jobs/ws-qrf-conformance/data",
        initial_queue_position="2",
        cost_usd=1.25,
        task_count=2,
        shots_total=2000,
        result_distribution={"00": 1000, "11": 970, "01": 15, "10": 15},
        metadata={"fixture": "true"},
    )


def _case(case_id: str, title: str, expected: str, fn: Callable[[], tuple[bool, str]]) -> ProfileConformanceCase:
    try:
        passed, observed = fn()
    except Exception as exc:  # report the failure rather than hiding it
        passed, observed = False, f"unexpected exception: {type(exc).__name__}: {exc}"
    return ProfileConformanceCase(
        case_id=case_id,
        title=title,
        passed=passed,
        expected_behavior=expected,
        observed_behavior=observed,
        claim_control="Controlled fixture conformance only; not external evidence.",
    )


def run_profile_conformance(*, repository_root: str | Path = ".") -> ProfileConformanceReport:
    root = Path(repository_root).resolve()
    cases: list[ProfileConformanceCase] = []

    with TemporaryDirectory(prefix="ws-qme-profile-") as temp:
        tmp = Path(temp)
        raw = tmp / "qpu-result.json"
        raw.write_text('{"fixture":"real-bytes"}\n', encoding="utf-8")
        correct_digest = _sha(raw)

        def digest_mismatch() -> tuple[bool, str]:
            record = _sara_record(raw_digest=SHA_A)
            decision = evaluate_external_evidence_batch(
                [ExternalEvidenceEnvelope(record, (ArtifactBinding("raw_artifact_digest", str(raw)),))],
                base_dir=tmp,
            )
            rejected = not decision.record_decisions[0].accepted_for_campaign_evaluation
            has_reason = any("does not match" in reason for reason in decision.record_decisions[0].reasons)
            return rejected and has_reason, f"accepted={decision.record_decisions[0].accepted_for_campaign_evaluation}; reasons={decision.record_decisions[0].reasons}"

        cases.append(_case("QME-01", "Reject raw-artifact digest mismatch", "mismatched local SHA-256 is rejected", digest_mismatch))

        def later_gate() -> tuple[bool, str]:
            record = _sara_record(raw_digest=correct_digest, gate_id="SARA-QRF-EXT-02")
            decision = evaluate_external_evidence_batch(
                [ExternalEvidenceEnvelope(record, (ArtifactBinding("raw_artifact_digest", str(raw)),))],
                base_dir=tmp,
            )
            row = decision.record_decisions[0]
            return (not row.current_gate_match and not row.accepted_for_campaign_evaluation), f"current_gate={decision.current_gate_id}; supplied={row.gate_id}; accepted={row.accepted_for_campaign_evaluation}"

        cases.append(_case("QME-02", "Reject later-stage gate skipping", "evidence aimed past the active gate is rejected", later_gate))

        def incomplete_sensor() -> tuple[bool, str]:
            record = ExternalEvidenceRecord(
                project_id="WS-APNT",
                evidence_type=ExternalEvidenceType.QUANTUM_SENSOR,
                source_id="fixture:sensor",
                raw_artifact_digest=SHA_A,
                collected_utc="2026-08-17T17:31:00Z",
                provider_or_lab="fixture-sensor-provider",
                configuration_digest=SHA_B,
                backend_or_device="sensor-fixture",
                uncertainty=0.1,
                metadata={"campaign_gate_id": "WS-APNT-EXT-02"},
            )
            decision = validate_external_evidence(record)
            return (not decision.accepted_for_intake and any("calibration" in r or "truth-reference" in r for r in decision.reasons)), f"accepted={decision.accepted_for_intake}; reasons={decision.reasons}"

        cases.append(_case("QME-03", "Reject incomplete quantum-sensor package", "sensor evidence missing calibration/truth reference is rejected", incomplete_sensor))

        def fake_hardware() -> tuple[bool, str]:
            simulator = _braket_fixture(device_arn="arn:aws:braket:us-east-1::device/quantum-simulator/amazon/sv1")
            decision = validate_braket_hybrid_job(simulator)
            return (not decision.accepted and any("QPU device ARN" in r for r in decision.reasons)), f"accepted={decision.accepted}; reasons={decision.reasons}"

        cases.append(_case("QME-04", "Reject simulator relabeled as provider hardware", "managed-service simulator cannot satisfy QPU hardware provenance", fake_hardware))

        def reused_result_identity() -> tuple[bool, str]:
            a = _qpu_run(run_id="run-a", provider="IBM", backend="qpu-a", result_digest=SHA_A, distribution={"00": .49, "11": .49, "01": .01, "10": .01})
            b = _qpu_run(run_id="run-b", provider="IonQ", backend="qpu-b", result_digest=SHA_A, distribution={"00": .49, "11": .49, "01": .01, "10": .01})
            decision = evaluate_cross_backend_reproducibility([a, b])
            return (not decision.reproducible and any("distinct result-record digests" in r for r in decision.reasons)), f"reproducible={decision.reproducible}; reasons={decision.reasons}"

        cases.append(_case("QME-05", "Reject reused result identity as independent reproduction", "independent runs require distinct immutable result records", reused_result_identity))

        def statistical_reproduction() -> tuple[bool, str]:
            a = _qpu_run(run_id="run-a", provider="IBM", backend="qpu-a", result_digest=SHA_A, distribution={"00": 490, "11": 490, "01": 10, "10": 10})
            b = _qpu_run(run_id="run-b", provider="IonQ", backend="qpu-b", result_digest=SHA_B, distribution={"00": 487, "11": 493, "01": 9, "10": 11})
            decision = evaluate_cross_backend_reproducibility([a, b], max_total_variation_distance=0.02, min_bhattacharyya_fidelity=0.999)
            return decision.reproducible, f"tvd={decision.max_total_variation_distance_observed}; fidelity={decision.min_bhattacharyya_fidelity_observed}; reasons={decision.reasons}"

        cases.append(_case("QME-06", "Accept statistically consistent distinct QPU distributions", "non-identical independent distributions pass predeclared statistical thresholds", statistical_reproduction))

        def managed_job_acceptance() -> tuple[bool, str]:
            fixture = _braket_fixture()
            job = validate_braket_hybrid_job(fixture)
            evidence = build_braket_qpu_external_evidence(fixture, project_id="SARA-QRF", campaign_gate_id="SARA-QRF-EXT-02")
            intake = validate_external_evidence(evidence)
            return (job.accepted and intake.accepted_for_intake), f"job_accepted={job.accepted}; typed_intake={intake.accepted_for_intake}; queue={job.queue_seconds}; runtime={job.runtime_seconds}"

        cases.append(_case("QME-07", "Accept evidence-complete managed QPU job fixture", "complete QPU managed-job provenance passes structural contract", managed_job_acceptance))

        # A structurally valid first-gate package provides a real ingest decision object for review-binding cases.
        valid_record = _sara_record(raw_digest=correct_digest)
        valid_ingest = evaluate_external_evidence_batch(
            [ExternalEvidenceEnvelope(valid_record, (ArtifactBinding("raw_artifact_digest", str(raw)),))],
            base_dir=tmp,
        )

        def exact_review_binding() -> tuple[bool, str]:
            review = ExternalEvidenceTechnicalReview(
                review_id="QME-FIXTURE-REVIEW-01",
                project_id="SARA-QRF",
                gate_id="SARA-QRF-EXT-01",
                ingest_decision_digest=ingest_decision_digest(valid_ingest),
                reviewer_identity="fixture-human-reviewer",
                reviewer_role="authorized_fixture_reviewer",
                reviewer_is_human=True,
                reviewed_utc="2026-08-17T17:40:00Z",
                technical_validity_accepted=True,
                provenance_accepted=True,
                uncertainty_or_error_reviewed=True,
                negative_evidence_reviewed=True,
                claims_control_accepted=True,
                conflict_of_interest_or_bias_considered=True,
                promotion_recommended=True,
                rationale="controlled conformance fixture",
                limitations="fixture only; no real QPU evidence",
            )
            decision = evaluate_technical_review(review, ingest_decision=valid_ingest)
            return (valid_ingest.ready_for_technical_review and decision.accepted_review_record and decision.promotion_recommended), f"ingest_ready={valid_ingest.ready_for_technical_review}; review_accepted={decision.accepted_review_record}; recommendation={decision.promotion_recommended}"

        cases.append(_case("QME-08", "Bind human review to exact ingest decision", "identified-human review succeeds only against exact retained ingest decision", exact_review_binding))

        def review_nonmutation() -> tuple[bool, str]:
            matrix = root / "data/quantum_project_matrix.json"
            before = _sha(matrix)
            review = ExternalEvidenceTechnicalReview(
                review_id="QME-FIXTURE-REVIEW-02",
                project_id="SARA-QRF",
                gate_id="SARA-QRF-EXT-01",
                ingest_decision_digest=ingest_decision_digest(valid_ingest),
                reviewer_identity="fixture-human-reviewer",
                reviewer_role="authorized_fixture_reviewer",
                reviewer_is_human=True,
                reviewed_utc="2026-08-17T17:41:00Z",
                technical_validity_accepted=True,
                provenance_accepted=True,
                uncertainty_or_error_reviewed=True,
                negative_evidence_reviewed=True,
                claims_control_accepted=True,
                conflict_of_interest_or_bias_considered=True,
                promotion_recommended=True,
                rationale="controlled conformance fixture",
                limitations="fixture only; no real state change",
            )
            decision = evaluate_technical_review(review, ingest_decision=valid_ingest)
            after = _sha(matrix)
            no_mutation = before == after and "separate canonical state-change action" in decision.next_governed_action
            return no_mutation, f"matrix_digest_before={before}; after={after}; next_action={decision.next_governed_action}"

        cases.append(_case("QME-09", "Human review recommendation does not mutate canonical state", "promotion recommendation requires a separate state-change action", review_nonmutation))

        def ddil_identity() -> tuple[bool, str]:
            artifact = tmp / "ddil.json"
            artifact.write_text('{"ddil":"fixture"}\n', encoding="utf-8")
            local = create_ddil_custody(
                artifact,
                project_id="SARA-QRF",
                node_id="field-node-fixture",
                local_sequence=1,
                local_configuration_digest=SHA_A,
                campaign_gate_id="SARA-QRF-EXT-03",
                collected_utc="2026-08-17T17:42:00Z",
            )
            identity = custody_identity_digest(local)
            synced = acknowledge_delayed_sync(
                local,
                provider_or_service="fixture-provider",
                provider_ack_id="ack-fixture",
                provider_artifact_digest=local.local_artifact_digest,
                synchronized_utc="2026-08-17T18:42:00Z",
            )
            decision = validate_ddil_custody(synced, artifact_path=artifact, expected_identity_digest=identity)
            return (decision.accepted and decision.identity_preserved and custody_identity_digest(synced) == identity), f"sync_state={synced.sync_state}; identity_preserved={decision.identity_preserved}; reasons={decision.reasons}"

        cases.append(_case("QME-10", "Preserve DDIL identity through delayed synchronization", "provider synchronization augments rather than regenerates local evidence identity", ddil_identity))

    passed_count = sum(case.passed for case in cases)
    return ProfileConformanceReport(
        profile="Worldshepherd Quantum Mission Evidence Profile",
        profile_version="draft-0.1",
        passed=passed_count == len(cases),
        cases_total=len(cases),
        cases_passed=passed_count,
        cases=tuple(cases),
        claim_control=(
            "A PASS demonstrates the draft profile's controlled software conformance cases only. It is not external certification, "
            "not a real-provider validation, and does not change Worldshepherd mission-readiness scores."
        ),
    )


def report_as_dict(report: ProfileConformanceReport) -> dict[str, object]:
    return asdict(report)
