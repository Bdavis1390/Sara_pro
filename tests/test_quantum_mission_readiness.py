import pytest

from worldshepherd_sara.quantum_mission_readiness import (
    CURRENT_QUANTUM_MISSION_INPUTS,
    MISSION_READY_TARGET,
    MissionEvidenceStage,
    MissionReadinessInputs,
    calibrate_mission_readiness,
    current_quantum_mission_calibration,
)


def _maxed(stage: MissionEvidenceStage) -> MissionReadinessInputs:
    return MissionReadinessInputs(
        project_id="TEST",
        mission_lane="threshold-test",
        evidence_stage=stage,
        mission_fidelity=20,
        classical_comparator=15,
        quantum_evidence_reproducibility=15,
        integration_interoperability=15,
        security_provenance=10,
        degraded_latency_cost=15,
        physical_environment_validation=10,
    )


def test_target_is_97():
    assert MISSION_READY_TARGET == 97


def test_every_pre_operational_stage_is_hard_capped_below_97():
    for stage in MissionEvidenceStage:
        decision = calibrate_mission_readiness(_maxed(stage))
        if stage is MissionEvidenceStage.OPERATIONAL_DEMONSTRATION:
            assert decision.mission_readiness_score == 100
            assert decision.meets_target
            assert decision.mission_use_decision == "CANDIDATE_FOR_SEPARATE_OPERATIONAL_APPROVAL"
        else:
            assert decision.mission_readiness_score < MISSION_READY_TARGET
            assert not decision.meets_target
            assert decision.mission_use_decision == "NO_GO_BELOW_97"
            assert decision.closure_status == "CLOSURE_REQUIRED"
            assert decision.required_target_stage == "operational_demonstration"
            assert decision.closure_sequence


def test_synthetic_surrogate_cannot_score_above_30():
    decision = calibrate_mission_readiness(_maxed(MissionEvidenceStage.SYNTHETIC_SURROGATE))
    assert decision.raw_score == 100
    assert decision.evidence_cap == 30
    assert decision.mission_readiness_score == 30
    assert decision.gap_to_target == 67
    assert decision.readiness_band == "MISSION_SURROGATE"
    assert decision.mission_use_decision == "NO_GO_BELOW_97"


def test_integrated_simulation_is_capped_at_55():
    decision = calibrate_mission_readiness(_maxed(MissionEvidenceStage.INTEGRATED_SIMULATION))
    assert decision.mission_readiness_score == 55
    assert decision.gap_to_target == 42
    assert decision.readiness_band == "INTEGRATED_LAB"
    assert decision.mission_use_decision == "NO_GO_BELOW_97"


def test_relevant_environment_is_still_below_97():
    decision = calibrate_mission_readiness(_maxed(MissionEvidenceStage.RELEVANT_ENVIRONMENT))
    assert decision.mission_readiness_score == 92
    assert decision.gap_to_target == 5
    assert decision.readiness_band == "PRE_MISSION_CLOSURE"
    assert decision.mission_use_decision == "NO_GO_BELOW_97"


def test_dimension_headroom_is_explicit():
    row = MissionReadinessInputs(
        project_id="TEST",
        mission_lane="headroom",
        evidence_stage=MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
        mission_fidelity=19,
        classical_comparator=15,
        quantum_evidence_reproducibility=15,
        integration_interoperability=15,
        security_provenance=10,
        degraded_latency_cost=14,
        physical_environment_validation=9,
    )
    decision = calibrate_mission_readiness(row)
    assert decision.raw_score == 97
    assert decision.meets_target
    assert decision.dimension_headroom["mission_fidelity"] == 1
    assert decision.dimension_headroom["degraded_latency_cost"] == 1
    assert decision.dimension_headroom["physical_environment_validation"] == 1


def test_invalid_dimension_is_rejected():
    row = MissionReadinessInputs(
        project_id="TEST",
        mission_lane="bad input",
        evidence_stage=MissionEvidenceStage.CONCEPT,
        mission_fidelity=21,
        classical_comparator=0,
        quantum_evidence_reproducibility=0,
        integration_interoperability=0,
        security_provenance=0,
        degraded_latency_cost=0,
        physical_environment_validation=0,
    )
    with pytest.raises(ValueError, match="mission_fidelity"):
        calibrate_mission_readiness(row)


def test_classically_dominated_lane_can_be_explicitly_held_without_promotion():
    row = MissionReadinessInputs(
        project_id="TEST-GLOB",
        mission_lane="classical dominance test",
        evidence_stage=MissionEvidenceStage.CONCEPT,
        mission_fidelity=5,
        classical_comparator=15,
        quantum_evidence_reproducibility=0,
        integration_interoperability=1,
        security_provenance=5,
        degraded_latency_cost=1,
        physical_environment_validation=0,
        mission_use_override="NO_GO_QUANTUM_EXECUTION_CLASSICAL_DOMINATES",
        closure_status_override="QUANTUM_EXECUTION_NOT_JUSTIFIED",
        next_gate_override="remain classical",
        closure_sequence_override=(),
    )
    decision = calibrate_mission_readiness(row)
    assert decision.mission_readiness_score == 15
    assert not decision.meets_target
    assert decision.mission_use_decision == "NO_GO_QUANTUM_EXECUTION_CLASSICAL_DOMINATES"
    assert decision.closure_status == "QUANTUM_EXECUTION_NOT_JUSTIFIED"
    assert decision.next_gate == "remain classical"
    assert decision.closure_sequence == ()


def test_current_quantum_calibration_is_hard_no_go_until_closed_or_held():
    results = current_quantum_mission_calibration()
    assert len(results) == len(CURRENT_QUANTUM_MISSION_INPUTS)
    by_project = {row.project_id: row for row in results}

    assert by_project["SARA-QRF"].mission_readiness_score == 55
    assert by_project["WS-METASURFACE"].mission_readiness_score == 30
    assert by_project["WS-AUTONOMOUS-LOGISTICS"].mission_readiness_score == 30
    assert by_project["WS-APNT"].mission_readiness_score == 30
    assert by_project["WS-APNT"].evidence_stage == "synthetic_surrogate"
    assert by_project["WS-APNT"].gap_to_target == 67
    assert "WS-APNT-SYN-001" in " ".join(by_project["WS-APNT"].evidence_refs)
    assert by_project["WS-ALTI"].mission_readiness_score == 15
    assert by_project["WS-EM-PROPULSION"].mission_readiness_score == 15
    assert by_project["WS-GLOB"].mission_readiness_score == 15
    assert by_project["WS-GLOB"].mission_use_decision == "NO_GO_QUANTUM_EXECUTION_CLASSICAL_DOMINATES"
    assert by_project["WS-GLOB"].closure_status == "QUANTUM_EXECUTION_NOT_JUSTIFIED"
    assert by_project["WS-GLOB"].closure_sequence == ()
    assert all(not row.meets_target for row in results)
    for project_id, row in by_project.items():
        if project_id == "WS-GLOB":
            assert row.mission_use_decision == "NO_GO_QUANTUM_EXECUTION_CLASSICAL_DOMINATES"
        else:
            assert row.mission_use_decision == "NO_GO_BELOW_97"
