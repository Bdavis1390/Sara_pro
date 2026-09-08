import pytest
from pydantic import ValidationError

from worldshepherd_sara.claims_linter_physics import LintSeverity, lint_physics_claim
from worldshepherd_sara.physics_validation import (
    ApprovalState,
    ConfounderStatus,
    EvidenceProvenance,
    EvidenceScore,
    ExperimentRecord,
    GoverningEquation,
    IndependentReviewState,
    PhysicsLayer,
    PhysicsVerificationRecord,
    ReplicationState,
    SimulationRecord,
    ValidationState,
    apply_hard_gates,
    photon_force,
    photon_ratio,
)

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
DIGEST_D = "sha256:" + "d" * 64


def provenance(**overrides):
    payload = {
        "source_manifest_digest": DIGEST_C,
        "configuration_digest": DIGEST_D,
        "acquisition_time_utc": "2026-09-06T22:00:00Z",
        "time_reference": "UTC",
        "coordinate_frame": "laboratory/device frame",
        "custody_events": ["acquired by test operator", "raw evidence hash-bound"],
    }
    payload.update(overrides)
    return EvidenceProvenance(**payload)


def concept_record(**overrides):
    payload = {
        "record_id": "PHYS-TEST-0001",
        "artifact_id": "ART-TEST-0001",
        "project_id": "WORLDSHEPHERD-CORE",
        "physics_domain": ["electromagnetics"],
        "model_scope": "bounded test concept",
        "assumptions": ["laboratory frame"],
        "validation_state": "concept",
        "claim_label": "Hypothesis",
        "external_safe_statement": "Concept-stage model; no measured performance claimed.",
        "created_at": "2026-09-06T22:00:00Z",
        "updated_at": "2026-09-06T22:00:00Z",
    }
    payload.update(overrides)
    return PhysicsVerificationRecord(**payload)


def simulation_fields():
    return {
        "governing_equations": [
            GoverningEquation(
                expression="F=P/c",
                name="photon momentum baseline",
                domain_of_validity="ideal one-way radiative momentum transfer",
            )
        ],
        "boundary_conditions": ["closed bookkeeping surface"],
        "uncertainty_method": "first-order propagation",
        "simulation": SimulationRecord(
            solver="analytic",
            version="1",
            mesh_or_resolution="not applicable; analytic baseline",
            convergence_status="passed",
            input_digest=DIGEST_A,
            output_digest=DIGEST_B,
        ),
    }


def test_photon_baseline_and_ratio():
    force = photon_force(1000.0)
    assert force == pytest.approx(3.3356409519815205e-6)
    assert photon_ratio(force, 1000.0) == pytest.approx(1.0)


def test_concept_stage_record_is_backward_compatible():
    record = concept_record()
    assert record.schema_version == "ws-physics-record-1"
    assert record.validation_state == ValidationState.CONCEPT


def test_simulated_state_requires_simulation_metadata():
    with pytest.raises(ValidationError):
        concept_record(validation_state="simulated")


def test_physical_test_requires_calibrated_raw_evidence():
    payload = simulation_fields()
    payload.update(
        {
            "validation_state": "internal_test",
            "failure_modes": ["sensor drift"],
            "experiment": {
                "setup_id": "SETUP-1",
                "calibration_record_ids": [],
                "raw_data_digests": [DIGEST_A],
                "environment": {"temperature_c": 22.0},
                "operator": "SSPADAWANZZ",
                "measurement_equipment_used": True,
                "provenance": provenance().model_dump(mode="json"),
            },
        }
    )
    with pytest.raises(ValidationError):
        concept_record(**payload)


def test_physical_test_requires_echo_grade_provenance():
    payload = simulation_fields()
    payload.update(
        {
            "validation_state": "internal_test",
            "failure_modes": ["sensor drift"],
            "experiment": ExperimentRecord(
                setup_id="SETUP-PROV-MISSING",
                calibration_record_ids=["CAL-PROV-1"],
                raw_data_digests=[DIGEST_A],
                environment={"temperature_c": 22.0},
                operator="SSPADAWANZZ",
            ),
        }
    )
    with pytest.raises(ValidationError, match="ECHO-grade evidence provenance"):
        concept_record(**payload)


def test_p4_requires_energy_and_momentum_accounting():
    with pytest.raises(ValidationError):
        concept_record(physics_layer=PhysicsLayer.P4_BEYOND_STANDARD_MODEL)


def test_claims_linter_blocks_reactionless_claim():
    findings = lint_physics_claim("This is proven reactionless propulsion.", record=concept_record())
    assert any(item.rule_id == "PROP-01" and item.severity == LintSeverity.BLOCK for item in findings)
    assert any(item.rule_id == "MATURITY-01" and item.severity == LintSeverity.BLOCK for item in findings)


def test_qualified_language_downgrades_general_physics_trigger_to_info():
    findings = lint_physics_claim(
        "Concept-stage quantum model; no measured Worldshepherd-specific performance claimed."
    )
    assert any(item.rule_id == "Q-01" and item.severity == LintSeverity.INFO for item in findings)


def test_high_score_does_not_confirm_new_physics_without_replication():
    payload = simulation_fields()
    payload.update(
        {
            "validation_state": "internal_test",
            "failure_modes": ["thermal drift"],
            "experiment": ExperimentRecord(
                setup_id="SETUP-2",
                calibration_record_ids=["CAL-1"],
                raw_data_digests=[DIGEST_A],
                environment={"temperature_c": 22.0},
                operator="SSPADAWANZZ",
                confounders={"thermal": ConfounderStatus.TESTED_PASS},
                replication_state=ReplicationState.R1_INTERNAL,
                provenance=provenance(),
            ),
        }
    )
    record = concept_record(**payload)
    score = EvidenceScore(
        repeatability=100,
        control_quality=100,
        signal_quality=100,
        background_characterization=100,
        instrument_independence=100,
        model_consistency=100,
        falsification_strength=100,
    )
    result = apply_hard_gates(record=record, score=score)
    assert result["weighted_score"] == 100
    assert result["new_physics_confirmed"] is False
    assert "NO_INDEPENDENT_REPLICATION" in result["hard_gate_blocks"]
    assert "VALIDATION_STATE_TOO_LOW_FOR_EXTERNAL_RELEASE" in result["hard_gate_blocks"]
    assert result["external_claim_allowed"] is False


def test_independent_state_requires_review_evidence_and_approval():
    payload = simulation_fields()
    payload.update(
        {
            "validation_state": "independently_replicated",
            "failure_modes": ["thermal drift"],
            "experiment": ExperimentRecord(
                setup_id="SETUP-3",
                calibration_record_ids=["CAL-2"],
                raw_data_digests=[DIGEST_A],
                environment={},
                operator="EXTERNAL-LAB",
                confounders={"thermal": ConfounderStatus.TESTED_PASS},
                replication_state=ReplicationState.R3_INDEPENDENT,
                provenance=provenance(
                    custody_events=[
                        "acquired by independent laboratory",
                        "raw evidence hash-bound by independent laboratory",
                    ]
                ),
            ),
            "independent_review_state": IndependentReviewState.COMPLETED,
            "independent_evidence_refs": ["EXT-EVID-1"],
            "cre1aws_approval_state": ApprovalState.APPROVED,
        }
    )
    record = concept_record(**payload)
    assert record.validation_state == ValidationState.INDEPENDENTLY_REPLICATED
