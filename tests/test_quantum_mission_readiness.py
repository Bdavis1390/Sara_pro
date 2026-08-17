import pytest

from worldshepherd_sara.quantum_mission_readiness import (
    CURRENT_QUANTUM_MISSION_INPUTS,
    MissionEvidenceStage,
    MissionReadinessInputs,
    calibrate_mission_readiness,
    current_quantum_mission_calibration,
)


def test_synthetic_surrogate_cannot_score_above_30():
    row = MissionReadinessInputs(
        project_id="TEST",
        mission_lane="synthetic",
        evidence_stage=MissionEvidenceStage.SYNTHETIC_SURROGATE,
        mission_fidelity=20,
        classical_comparator=15,
        quantum_evidence_reproducibility=15,
        integration_interoperability=15,
        security_provenance=10,
        degraded_latency_cost=15,
        physical_environment_validation=10,
    )
    decision = calibrate_mission_readiness(row)
    assert decision.raw_score == 100
    assert decision.evidence_cap == 30
    assert decision.mission_readiness_score == 30
    assert decision.readiness_band == "MISSION_SURROGATE"


def test_integrated_simulation_is_capped_below_hardware_backed():
    row = MissionReadinessInputs(
        project_id="TEST",
        mission_lane="integrated simulator",
        evidence_stage=MissionEvidenceStage.INTEGRATED_SIMULATION,
        mission_fidelity=20,
        classical_comparator=15,
        quantum_evidence_reproducibility=15,
        integration_interoperability=15,
        security_provenance=10,
        degraded_latency_cost=15,
        physical_environment_validation=10,
    )
    decision = calibrate_mission_readiness(row)
    assert decision.mission_readiness_score == 55
    assert decision.readiness_band == "INTEGRATED_LAB"


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


def test_current_quantum_calibration_covers_all_project_inputs():
    results = current_quantum_mission_calibration()
    assert len(results) == len(CURRENT_QUANTUM_MISSION_INPUTS)
    by_project = {row.project_id: row for row in results}

    assert by_project["SARA-QRF"].mission_readiness_score == 55
    assert by_project["SARA-QRF"].readiness_band == "INTEGRATED_LAB"
    assert by_project["WS-METASURFACE"].mission_readiness_score == 30
    assert by_project["WS-AUTONOMOUS-LOGISTICS"].mission_readiness_score == 30
    assert by_project["WS-APNT"].mission_readiness_score == 15
    assert by_project["WS-ALTI"].mission_readiness_score == 15
    assert by_project["WS-EM-PROPULSION"].mission_readiness_score == 15
    assert by_project["WS-GLOB"].mission_readiness_score == 15
