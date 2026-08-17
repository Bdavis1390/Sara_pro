from worldshepherd_sara.quantum_external_evidence import (
    ExternalEvidenceRecord,
    ExternalEvidenceType,
    validate_external_evidence,
)


D = "sha256:" + "a" * 64
B = "sha256:" + "b" * 64


def base(kind: ExternalEvidenceType, **kwargs):
    values = dict(
        project_id="TEST",
        evidence_type=kind,
        source_id="source-1",
        raw_artifact_digest=D,
        collected_utc="2026-08-17T15:30:00Z",
        provider_or_lab="test-provider",
        configuration_digest=B,
    )
    values.update(kwargs)
    return ExternalEvidenceRecord(**values)


def test_qpu_intake_requires_job_result_latency_and_cost():
    decision = validate_external_evidence(base(ExternalEvidenceType.QPU_EXECUTION))
    assert not decision.accepted_for_intake
    assert len(decision.reasons) >= 3

    accepted = validate_external_evidence(
        base(
            ExternalEvidenceType.QPU_EXECUTION,
            backend_or_device="backend-x",
            job_or_run_id="job-1",
            result_digest=D,
            latency_seconds=12.5,
            cost_usd=0.0,
        )
    )
    assert accepted.accepted_for_intake


def test_sensor_intake_requires_calibration_truth_and_uncertainty():
    decision = validate_external_evidence(
        base(
            ExternalEvidenceType.QUANTUM_SENSOR,
            backend_or_device="sensor-x",
            calibration_id="cal-1",
            truth_reference_id="truth-1",
            uncertainty=0.002,
        )
    )
    assert decision.accepted_for_intake


def test_materials_intake_requires_structure_and_classical_reference():
    decision = validate_external_evidence(
        base(
            ExternalEvidenceType.MATERIALS_HAMILTONIAN,
            classical_baseline_digest=D,
            metadata={
                "structure_digest": D,
                "hamiltonian_digest": B,
                "basis": "declared-basis",
                "active_space": "declared-active-space",
            },
        )
    )
    assert decision.accepted_for_intake


def test_mission_optimization_intake_requires_full_end_to_end_context():
    decision = validate_external_evidence(
        base(
            ExternalEvidenceType.MISSION_OPTIMIZATION,
            classical_baseline_digest=D,
            latency_seconds=1.0,
            cost_usd=0.01,
            metadata={
                "instance_family_digest": B,
                "objective_definition": "frozen-v1",
                "constraint_definition": "frozen-v1",
            },
        )
    )
    assert decision.accepted_for_intake


def test_physical_metrology_rejects_missing_null_controls():
    decision = validate_external_evidence(
        base(
            ExternalEvidenceType.PHYSICAL_METROLOGY,
            calibration_id="cal-1",
            truth_reference_id="null-1",
            uncertainty=1e-6,
            metadata={"null_controls_completed": "false"},
        )
    )
    assert not decision.accepted_for_intake
