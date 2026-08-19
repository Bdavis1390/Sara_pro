"""Stage-locked external evidence acquisition campaigns for the Worldshepherd QRF.

The campaign layer converts each project's remaining 97-point closure gap into a
sequence of evidence-acquisition gates. Gate identifiers remain stable as a project
advances: completed historical gates are filtered from the active campaign rather
than renumbered. Later-stage evidence cannot skip the first currently active gate.

Campaign completion is not mission approval. A structurally satisfied gate still
requires separate technical review before a mission-readiness stage is promoted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from worldshepherd_sara.quantum_external_evidence import (
    ExternalEvidenceRecord,
    ExternalEvidenceType,
    validate_external_evidence,
)
from worldshepherd_sara.quantum_mission_readiness import (
    CURRENT_QUANTUM_MISSION_INPUTS,
    MISSION_READY_TARGET,
    MissionEvidenceStage,
)


_STAGE_ORDER: tuple[MissionEvidenceStage, ...] = (
    MissionEvidenceStage.CONCEPT,
    MissionEvidenceStage.SYNTHETIC_SURROGATE,
    MissionEvidenceStage.CALIBRATED_MODEL,
    MissionEvidenceStage.INTEGRATED_SIMULATION,
    MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE,
    MissionEvidenceStage.REPRODUCED_HARDWARE,
    MissionEvidenceStage.HARDWARE_IN_LOOP,
    MissionEvidenceStage.RELEVANT_ENVIRONMENT,
    MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
)
_STAGE_INDEX = {stage: index for index, stage in enumerate(_STAGE_ORDER)}


@dataclass(frozen=True)
class EvidenceTypeMinimum:
    evidence_type: ExternalEvidenceType
    minimum_records: int


@dataclass(frozen=True)
class CampaignGate:
    gate_id: str
    project_id: str
    ordinal: int
    from_stage: MissionEvidenceStage
    to_stage: MissionEvidenceStage
    evidence_minimums: tuple[EvidenceTypeMinimum, ...]
    minimum_distinct_providers: int = 1
    minimum_distinct_devices: int = 0
    required_metadata_keys: tuple[str, ...] = ()
    allowed_environments: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    acceptance_statement: str = ""


@dataclass(frozen=True)
class ProjectEvidenceCampaign:
    project_id: str
    mission_lane: str
    current_stage: MissionEvidenceStage
    target_stage: MissionEvidenceStage
    target_score: int
    gates: tuple[CampaignGate, ...]
    claim_control: str


@dataclass(frozen=True)
class GateEvaluation:
    gate_id: str
    satisfied: bool
    reasons: tuple[str, ...]
    accepted_record_count: int


@dataclass(frozen=True)
class CampaignEvaluation:
    project_id: str
    starting_stage: str
    achieved_stage: str
    target_stage: str
    target_score: int
    next_gate_id: str | None
    complete: bool
    gate_evaluations: tuple[GateEvaluation, ...]
    claim_control: str


def _m(evidence_type: ExternalEvidenceType, minimum_records: int) -> EvidenceTypeMinimum:
    return EvidenceTypeMinimum(evidence_type=evidence_type, minimum_records=minimum_records)


def _gate(
    project_id: str,
    ordinal: int,
    from_stage: MissionEvidenceStage,
    to_stage: MissionEvidenceStage,
    *minimums: EvidenceTypeMinimum,
    providers: int = 1,
    devices: int = 0,
    metadata: tuple[str, ...] = (),
    environments: tuple[str, ...] = (),
    preconditions: tuple[str, ...] = (),
    acceptance: str,
) -> CampaignGate:
    return CampaignGate(
        gate_id=f"{project_id}-EXT-{ordinal:02d}",
        project_id=project_id,
        ordinal=ordinal,
        from_stage=from_stage,
        to_stage=to_stage,
        evidence_minimums=tuple(minimums),
        minimum_distinct_providers=providers,
        minimum_distinct_devices=devices,
        required_metadata_keys=metadata,
        allowed_environments=environments,
        preconditions=preconditions,
        acceptance_statement=acceptance,
    )


def _sara() -> tuple[CampaignGate, ...]:
    p = "SARA-QRF"
    return (
        _gate(p, 1, MissionEvidenceStage.INTEGRATED_SIMULATION, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 1), devices=1,
              metadata=("test_protocol_digest", "program_digest", "transpiled_program_digest", "backend_properties_digest", "queue_seconds", "failure_mode"),
              environments=("remote_cloud_qpu", "integration_lab"),
              acceptance="Retain one named real-QPU execution with immutable program/backend/result provenance and measured queue, latency, cost, and failure telemetry."),
        _gate(p, 2, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE, MissionEvidenceStage.REPRODUCED_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 2), devices=1,
              metadata=("replication_series_id", "test_protocol_digest", "program_digest"),
              acceptance="Repeat the frozen workload at least twice under one replication series and quantify stability."),
        _gate(p, 3, MissionEvidenceStage.REPRODUCED_HARDWARE, MissionEvidenceStage.HARDWARE_IN_LOOP,
              _m(ExternalEvidenceType.QPU_EXECUTION, 1), devices=1,
              metadata=("sara_workflow_digest", "degraded_state_result_digest", "fallback_result_digest", "test_protocol_digest"),
              environments=("hardware_in_loop", "integration_lab"),
              acceptance="Run the QPU path inside SARA with deterministic classical fallback and degraded-state evidence."),
        _gate(p, 4, MissionEvidenceStage.HARDWARE_IN_LOOP, MissionEvidenceStage.RELEVANT_ENVIRONMENT,
              _m(ExternalEvidenceType.QPU_EXECUTION, 2), devices=1,
              metadata=("mission_scenario_id", "truth_reference_digest", "operator_log_digest", "test_protocol_digest"),
              environments=("relevant_environment",),
              acceptance="Execute repeated end-to-end trials in a declared relevant environment with truth/reference instrumentation."),
        _gate(p, 5, MissionEvidenceStage.RELEVANT_ENVIRONMENT, MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
              _m(ExternalEvidenceType.QPU_EXECUTION, 3), devices=1,
              metadata=("operational_scenario_id", "acceptance_criteria_digest", "operator_log_digest", "test_protocol_digest"),
              environments=("operational_demonstration",),
              acceptance="Complete an operational demonstration series against predeclared acceptance criteria."),
    )


def _apnt() -> tuple[CampaignGate, ...]:
    p = "WS-APNT"
    return (
        _gate(p, 1, MissionEvidenceStage.CONCEPT, MissionEvidenceStage.SYNTHETIC_SURROGATE,
              providers=0, preconditions=("WS-APNT-P0-SIMULATED-SENSOR-BENCHMARK",),
              acceptance="Freeze a simulated sensor/error model and truth-reference benchmark before accepting device evidence."),
        _gate(p, 2, MissionEvidenceStage.SYNTHETIC_SURROGATE, MissionEvidenceStage.CALIBRATED_MODEL,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 1), devices=1,
              metadata=("observable", "units", "sample_rate_hz", "calibration_certificate_digest", "test_protocol_digest"),
              environments=("calibration_lab", "integration_lab"),
              acceptance="Acquire a calibrated named sensor/device dataset against a truth reference and uncertainty budget."),
        _gate(p, 3, MissionEvidenceStage.CALIBRATED_MODEL, MissionEvidenceStage.INTEGRATED_SIMULATION,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 2), devices=1,
              metadata=("interface_schema_digest", "denied_reference_injection", "fusion_algorithm_digest", "test_protocol_digest"),
              acceptance="Replay calibrated data through the APNT fusion/control interface including denied/degraded-reference cases."),
        _gate(p, 4, MissionEvidenceStage.INTEGRATED_SIMULATION, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 1), devices=1,
              metadata=("live_stream", "interface_schema_digest", "truth_reference_digest", "test_protocol_digest"),
              environments=("hardware_bench", "integration_lab"),
              acceptance="Run a live named quantum sensor through the APNT interface against a truth reference."),
        _gate(p, 5, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE, MissionEvidenceStage.REPRODUCED_HARDWARE,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 2), devices=1,
              metadata=("replication_series_id", "truth_reference_digest", "test_protocol_digest"),
              acceptance="Repeat the live sensor trial and quantify run-to-run stability."),
        _gate(p, 6, MissionEvidenceStage.REPRODUCED_HARDWARE, MissionEvidenceStage.HARDWARE_IN_LOOP,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 2), devices=1,
              metadata=("navigation_solution_digest", "degraded_mode_digest", "fallback_result_digest", "test_protocol_digest"),
              environments=("hardware_in_loop",),
              acceptance="Close the sensor in the APNT navigation/control loop with degraded-mode and classical fallback tests."),
        _gate(p, 7, MissionEvidenceStage.HARDWARE_IN_LOOP, MissionEvidenceStage.RELEVANT_ENVIRONMENT,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 3), devices=1,
              metadata=("route_or_profile_id", "truth_reference_digest", "environmental_conditions_digest", "test_protocol_digest"),
              environments=("relevant_environment",),
              acceptance="Demonstrate repeatable APNT performance under relevant motion/environment and denied/degraded-reference conditions."),
        _gate(p, 8, MissionEvidenceStage.RELEVANT_ENVIRONMENT, MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 3), devices=1,
              metadata=("operational_scenario_id", "acceptance_criteria_digest", "truth_reference_digest", "operator_log_digest"),
              environments=("operational_demonstration",),
              acceptance="Complete an operational APNT demonstration series against predeclared criteria."),
    )


def _alti() -> tuple[CampaignGate, ...]:
    p = "WS-ALTI"
    return (
        _gate(p, 1, MissionEvidenceStage.CONCEPT, MissionEvidenceStage.SYNTHETIC_SURROGATE,
              _m(ExternalEvidenceType.MATERIALS_HAMILTONIAN, 1),
              metadata=("geometry_source", "composition_id", "test_protocol_digest"),
              preconditions=("WS-ALTI-P0-PHYSICAL-STRUCTURE-FROZEN",),
              acceptance="Freeze a physically specified Al-Ti-Mg-Sc-Zr structure and reduced Hamiltonian with provenance."),
        _gate(p, 2, MissionEvidenceStage.SYNTHETIC_SURROGATE, MissionEvidenceStage.CALIBRATED_MODEL,
              _m(ExternalEvidenceType.MATERIALS_HAMILTONIAN, 1),
              metadata=("dft_method", "reference_energy_units", "exact_active_space_method", "geometry_source", "test_protocol_digest"),
              acceptance="Establish HF/exact-active-space/DFT references for the same frozen structure."),
        _gate(p, 3, MissionEvidenceStage.CALIBRATED_MODEL, MissionEvidenceStage.INTEGRATED_SIMULATION,
              _m(ExternalEvidenceType.MATERIALS_HAMILTONIAN, 1),
              metadata=("variational_ansatz", "optimizer", "noise_model_digest", "reference_error", "test_protocol_digest"),
              acceptance="Run the exact-versus-variational workflow against frozen classical references with explicit noise assumptions."),
        _gate(p, 4, MissionEvidenceStage.INTEGRATED_SIMULATION, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 1), devices=1,
              metadata=("materials_problem_id", "hamiltonian_digest", "reference_result_digest", "test_protocol_digest"),
              acceptance="Execute the justified reduced materials workload on a named QPU and compare to exact/DFT reference."),
        _gate(p, 5, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE, MissionEvidenceStage.REPRODUCED_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 2), devices=1,
              metadata=("replication_series_id", "materials_problem_id", "reference_result_digest", "test_protocol_digest"),
              acceptance="Repeat the materials workload and quantify hardware-result stability/reference error."),
        _gate(p, 6, MissionEvidenceStage.REPRODUCED_HARDWARE, MissionEvidenceStage.HARDWARE_IN_LOOP,
              _m(ExternalEvidenceType.QPU_EXECUTION, 1), _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 1), devices=1,
              metadata=("coupon_id", "process_log_digest", "predicted_observable", "measured_observable", "test_protocol_digest"),
              environments=("materials_lab", "hardware_in_loop"),
              acceptance="Link governed computation to a physical coupon/process and compare a predicted observable to calibrated measurement."),
        _gate(p, 7, MissionEvidenceStage.HARDWARE_IN_LOOP, MissionEvidenceStage.RELEVANT_ENVIRONMENT,
              _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 3),
              metadata=("coupon_family_id", "process_log_digest", "environmental_conditions_digest", "test_protocol_digest"),
              environments=("relevant_environment", "materials_lab"),
              acceptance="Validate prediction-to-coupon correlation across a repeated coupon family."),
        _gate(p, 8, MissionEvidenceStage.RELEVANT_ENVIRONMENT, MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
              _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 3),
              metadata=("demonstrator_id", "acceptance_criteria_digest", "process_log_digest", "independent_measurement_digest"),
              environments=("operational_demonstration",),
              acceptance="Demonstrate the materials-computation workflow against predeclared physical criteria without replacing qualification."),
    )


def _metasurface() -> tuple[CampaignGate, ...]:
    p = "WS-METASURFACE"
    return (
        _gate(p, 1, MissionEvidenceStage.SYNTHETIC_SURROGATE, MissionEvidenceStage.CALIBRATED_MODEL,
              _m(ExternalEvidenceType.CALIBRATED_PHYSICS_MODEL, 1),
              metadata=("full_wave_solver", "mesh_or_discretization_digest", "frequency_grid_digest", "tile_state_map_digest", "test_protocol_digest"),
              acceptance="Calibrate the reduced tile objective to authoritative Maxwell/FEM/FDTD results with quantified error."),
        _gate(p, 2, MissionEvidenceStage.CALIBRATED_MODEL, MissionEvidenceStage.INTEGRATED_SIMULATION,
              _m(ExternalEvidenceType.CALIBRATED_PHYSICS_MODEL, 2), _m(ExternalEvidenceType.MISSION_OPTIMIZATION, 2),
              metadata=("instance_family_digest", "classical_optimizer", "reduced_model_digest", "test_protocol_digest"),
              acceptance="Run a calibrated instance family through the reduced model and strong classical optimizer."),
        _gate(p, 3, MissionEvidenceStage.INTEGRATED_SIMULATION, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 1), devices=1,
              metadata=("instance_family_digest", "classical_reference_digest", "end_to_end_objective", "test_protocol_digest"),
              acceptance="Execute a calibrated metasurface optimization instance on a named QPU with end-to-end comparison."),
        _gate(p, 4, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE, MissionEvidenceStage.REPRODUCED_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 2), devices=1,
              metadata=("replication_series_id", "instance_family_digest", "classical_reference_digest", "test_protocol_digest"),
              acceptance="Repeat calibrated QPU optimization and compare quality, latency, cost and stability."),
        _gate(p, 5, MissionEvidenceStage.REPRODUCED_HARDWARE, MissionEvidenceStage.HARDWARE_IN_LOOP,
              _m(ExternalEvidenceType.QPU_EXECUTION, 1), _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 1), devices=1,
              metadata=("rf_hardware_id", "tile_command_digest", "measured_field_digest", "fallback_result_digest", "test_protocol_digest"),
              environments=("hardware_in_loop", "rf_lab"),
              acceptance="Close optimization through real RF tile hardware and compare commanded versus measured response."),
        _gate(p, 6, MissionEvidenceStage.HARDWARE_IN_LOOP, MissionEvidenceStage.RELEVANT_ENVIRONMENT,
              _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 3),
              metadata=("rf_hardware_id", "environmental_conditions_digest", "truth_reference_digest", "test_protocol_digest"),
              environments=("relevant_environment",),
              acceptance="Repeat measured RF performance under relevant electromagnetic/environmental conditions."),
        _gate(p, 7, MissionEvidenceStage.RELEVANT_ENVIRONMENT, MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
              _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 3),
              metadata=("operational_scenario_id", "acceptance_criteria_digest", "operator_log_digest", "independent_measurement_digest"),
              environments=("operational_demonstration",),
              acceptance="Complete an operational metasurface demonstration series against frozen EM criteria."),
    )


def _logistics() -> tuple[CampaignGate, ...]:
    p = "WS-AUTONOMOUS-LOGISTICS"
    return (
        _gate(p, 1, MissionEvidenceStage.SYNTHETIC_SURROGATE, MissionEvidenceStage.CALIBRATED_MODEL,
              _m(ExternalEvidenceType.MISSION_OPTIMIZATION, 3),
              metadata=("mission_source", "instance_family_digest", "classical_optimizer", "latency_budget_seconds", "test_protocol_digest"),
              acceptance="Freeze a mission-relevant route/assignment family and CP-SAT/MILP/strong-heuristic baselines."),
        _gate(p, 2, MissionEvidenceStage.CALIBRATED_MODEL, MissionEvidenceStage.INTEGRATED_SIMULATION,
              _m(ExternalEvidenceType.MISSION_OPTIMIZATION, 5),
              metadata=("communications_model_digest", "queue_model_digest", "degraded_state_definition", "classical_optimizer", "test_protocol_digest"),
              acceptance="Benchmark the frozen family end-to-end with communications, queue, cost and degraded-state assumptions."),
        _gate(p, 3, MissionEvidenceStage.INTEGRATED_SIMULATION, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 1), _m(ExternalEvidenceType.MISSION_OPTIMIZATION, 1), devices=1,
              metadata=("instance_family_digest", "classical_reference_digest", "end_to_end_latency_seconds", "test_protocol_digest"),
              acceptance="Run one frozen mission instance on a named QPU and compare feasible quality, latency, cost and fallback."),
        _gate(p, 4, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE, MissionEvidenceStage.REPRODUCED_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 2), _m(ExternalEvidenceType.MISSION_OPTIMIZATION, 2), devices=1,
              metadata=("replication_series_id", "instance_family_digest", "classical_reference_digest", "test_protocol_digest"),
              acceptance="Repeat QPU-backed mission optimization and quantify feasibility, objective, queue variance and cost."),
        _gate(p, 5, MissionEvidenceStage.REPRODUCED_HARDWARE, MissionEvidenceStage.HARDWARE_IN_LOOP,
              _m(ExternalEvidenceType.MISSION_OPTIMIZATION, 3),
              metadata=("vehicle_or_mission_interface_digest", "degraded_state_result_digest", "fallback_result_digest", "operator_log_digest", "test_protocol_digest"),
              environments=("hardware_in_loop", "integration_lab"),
              acceptance="Close optimizer into mission/vehicle interface with classical fallback and degraded tests."),
        _gate(p, 6, MissionEvidenceStage.HARDWARE_IN_LOOP, MissionEvidenceStage.RELEVANT_ENVIRONMENT,
              _m(ExternalEvidenceType.MISSION_OPTIMIZATION, 5),
              metadata=("mission_scenario_id", "environmental_conditions_digest", "truth_reference_digest", "operator_log_digest", "test_protocol_digest"),
              environments=("relevant_environment",),
              acceptance="Repeat mission optimization under relevant constraints/degraded states with mission truth data."),
        _gate(p, 7, MissionEvidenceStage.RELEVANT_ENVIRONMENT, MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
              _m(ExternalEvidenceType.MISSION_OPTIMIZATION, 5),
              metadata=("operational_scenario_id", "acceptance_criteria_digest", "fallback_result_digest", "operator_log_digest"),
              environments=("operational_demonstration",),
              acceptance="Complete operational logistics demonstrations against feasibility, quality, latency, cost and fallback criteria."),
    )


def _em_propulsion() -> tuple[CampaignGate, ...]:
    p = "WS-EM-PROPULSION"
    separate = "WS-EMP-PROPULSION-CLAIM-GATE-SEPARATE"
    return (
        _gate(p, 1, MissionEvidenceStage.CONCEPT, MissionEvidenceStage.SYNTHETIC_SURROGATE,
              _m(ExternalEvidenceType.MATERIALS_HAMILTONIAN, 1),
              preconditions=("WS-EMP-P0-MEASURABLE-SUPPORT-TASK-FROZEN", separate),
              metadata=("material_system_id", "target_observable", "test_protocol_digest"),
              acceptance="Freeze one legitimate quantum-materials/metrology support task without using it as propulsion-force evidence."),
        _gate(p, 2, MissionEvidenceStage.SYNTHETIC_SURROGATE, MissionEvidenceStage.CALIBRATED_MODEL,
              _m(ExternalEvidenceType.MATERIALS_HAMILTONIAN, 1), _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 3),
              preconditions=(separate,), metadata=("target_observable", "calibration_chain_digest", "null_matrix_digest", "test_protocol_digest"),
              environments=("metrology_lab", "materials_lab"),
              acceptance="Calibrate the materials/metrology observable against independent measurement and completed null controls."),
        _gate(p, 3, MissionEvidenceStage.CALIBRATED_MODEL, MissionEvidenceStage.INTEGRATED_SIMULATION,
              _m(ExternalEvidenceType.MATERIALS_HAMILTONIAN, 1), _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 3),
              preconditions=(separate,), metadata=("model_prediction_digest", "measurement_result_digest", "uncertainty_budget_digest", "test_protocol_digest"),
              acceptance="Integrate model and measurement evidence while preserving the independent propulsion-force claim gate."),
        _gate(p, 4, MissionEvidenceStage.INTEGRATED_SIMULATION, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 1), devices=1, preconditions=(separate,),
              metadata=("observable", "calibration_certificate_digest", "null_matrix_digest", "test_protocol_digest"), environments=("metrology_lab",),
              acceptance="Use a named calibrated quantum sensor only for the declared metrology observable."),
        _gate(p, 5, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE, MissionEvidenceStage.REPRODUCED_HARDWARE,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 2), devices=1, preconditions=(separate,),
              metadata=("replication_series_id", "truth_reference_digest", "null_matrix_digest", "test_protocol_digest"),
              acceptance="Repeat the quantum-sensor metrology result under the frozen protocol/null matrix."),
        _gate(p, 6, MissionEvidenceStage.REPRODUCED_HARDWARE, MissionEvidenceStage.HARDWARE_IN_LOOP,
              _m(ExternalEvidenceType.QUANTUM_SENSOR, 2), _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 3), devices=1, preconditions=(separate,),
              metadata=("apparatus_configuration_digest", "environmental_monitor_digest", "null_matrix_digest", "test_protocol_digest"),
              environments=("hardware_in_loop", "metrology_lab"),
              acceptance="Integrate sensor into apparatus with environmental monitoring and blinded/null controls."),
        _gate(p, 7, MissionEvidenceStage.HARDWARE_IN_LOOP, MissionEvidenceStage.RELEVANT_ENVIRONMENT,
              _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 5), preconditions=(separate,),
              metadata=("apparatus_configuration_digest", "environmental_conditions_digest", "null_matrix_digest", "independent_measurement_digest"),
              environments=("relevant_environment",),
              acceptance="Repeat the metrology-support task in its relevant environment; propulsion-force claims remain separate."),
        _gate(p, 8, MissionEvidenceStage.RELEVANT_ENVIRONMENT, MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
              _m(ExternalEvidenceType.PHYSICAL_METROLOGY, 5), preconditions=(separate,),
              metadata=("operational_scenario_id", "acceptance_criteria_digest", "null_matrix_digest", "independent_measurement_digest"),
              environments=("operational_demonstration",),
              acceptance="Demonstrate only the bounded materials/metrology support capability; do not cite this as anomalous propulsion proof."),
    )


def _glob() -> tuple[CampaignGate, ...]:
    p = "WS-GLOB"
    return (
        _gate(p, 1, MissionEvidenceStage.CONCEPT, MissionEvidenceStage.SYNTHETIC_SURROGATE,
              providers=0, preconditions=("WS-GLOB-QMAPPING-PASSED", "WS-GLOB-NULL-MODEL-FROZEN", "WS-GLOB-CLASSICAL-COMPLEXITY-FROZEN"),
              acceptance="Admit only a measurable mapping with frozen null and classical complexity baselines."),
        _gate(p, 2, MissionEvidenceStage.SYNTHETIC_SURROGATE, MissionEvidenceStage.CALIBRATED_MODEL,
              providers=0, preconditions=("WS-GLOB-CALIBRATED-OBJECTIVE-FROZEN",),
              acceptance="Calibrate the admitted quantum problem to a declared measurable objective; recurrence alone is insufficient."),
        _gate(p, 3, MissionEvidenceStage.CALIBRATED_MODEL, MissionEvidenceStage.INTEGRATED_SIMULATION,
              providers=0, preconditions=("WS-GLOB-IDEAL-NOISY-SIM-EVIDENCE", "WS-GLOB-RESOURCE-ESTIMATE"),
              acceptance="Retain ideal/noisy simulation and resource-estimation evidence against the null/classical comparator."),
        _gate(p, 4, MissionEvidenceStage.INTEGRATED_SIMULATION, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 1), devices=1,
              metadata=("problem_mapping_digest", "classical_reference_digest", "null_model_digest", "test_protocol_digest"),
              acceptance="Execute the admitted measurable workload on one named QPU and compare to null/classical result."),
        _gate(p, 5, MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE, MissionEvidenceStage.REPRODUCED_HARDWARE,
              _m(ExternalEvidenceType.QPU_EXECUTION, 2), devices=1,
              metadata=("replication_series_id", "problem_mapping_digest", "classical_reference_digest", "null_model_digest"),
              acceptance="Repeat the real-QPU workload and quantify reproducibility versus the frozen baselines."),
        _gate(p, 6, MissionEvidenceStage.REPRODUCED_HARDWARE, MissionEvidenceStage.HARDWARE_IN_LOOP,
              _m(ExternalEvidenceType.QPU_EXECUTION, 1), devices=1, preconditions=("WS-GLOB-MISSION-CONTEXT-DECLARED",),
              metadata=("mission_interface_digest", "fallback_result_digest", "test_protocol_digest"), environments=("hardware_in_loop", "integration_lab"),
              acceptance="Only with a legitimate mission context, integrate the task with mission interface and classical fallback."),
        _gate(p, 7, MissionEvidenceStage.HARDWARE_IN_LOOP, MissionEvidenceStage.RELEVANT_ENVIRONMENT,
              _m(ExternalEvidenceType.QPU_EXECUTION, 2), devices=1, preconditions=("WS-GLOB-MISSION-CONTEXT-DECLARED",),
              metadata=("mission_scenario_id", "truth_reference_digest", "null_model_digest", "test_protocol_digest"), environments=("relevant_environment",),
              acceptance="Demonstrate the measurable task in a relevant mission environment; numerical coincidence is not evidence."),
        _gate(p, 8, MissionEvidenceStage.RELEVANT_ENVIRONMENT, MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
              _m(ExternalEvidenceType.QPU_EXECUTION, 3), devices=1, preconditions=("WS-GLOB-MISSION-CONTEXT-DECLARED",),
              metadata=("operational_scenario_id", "acceptance_criteria_digest", "null_model_digest", "operator_log_digest"), environments=("operational_demonstration",),
              acceptance="Complete an operational demonstration only for the admitted measurable task."),
    )


_GATE_BUILDERS = {
    "SARA-QRF": _sara,
    "WS-APNT": _apnt,
    "WS-ALTI": _alti,
    "WS-METASURFACE": _metasurface,
    "WS-AUTONOMOUS-LOGISTICS": _logistics,
    "WS-EM-PROPULSION": _em_propulsion,
    "WS-GLOB": _glob,
}


def _validate_campaign(campaign: ProjectEvidenceCampaign) -> None:
    if campaign.current_stage == campaign.target_stage:
        if campaign.gates:
            raise ValueError(f"{campaign.project_id}: completed campaign must have no active gates")
        return
    if not campaign.gates:
        raise ValueError(f"{campaign.project_id}: active campaign has no remaining gates")

    expected_from = campaign.current_stage
    expected_ordinal = campaign.gates[0].ordinal
    for gate in campaign.gates:
        if gate.ordinal != expected_ordinal:
            raise ValueError(f"{campaign.project_id}: non-contiguous stable gate ordinal at {gate.gate_id}")
        if gate.project_id != campaign.project_id:
            raise ValueError(f"{campaign.project_id}: gate project mismatch at {gate.gate_id}")
        if gate.from_stage != expected_from:
            raise ValueError(f"{campaign.project_id}: stage discontinuity at {gate.gate_id}")
        if _STAGE_INDEX[gate.to_stage] != _STAGE_INDEX[gate.from_stage] + 1:
            raise ValueError(f"{campaign.project_id}: stage skip prohibited at {gate.gate_id}")
        if gate.minimum_distinct_providers < 0 or gate.minimum_distinct_devices < 0:
            raise ValueError(f"{campaign.project_id}: negative diversity requirement")
        if not gate.evidence_minimums and not gate.preconditions:
            raise ValueError(f"{campaign.project_id}: gate has neither evidence nor precondition")
        for requirement in gate.evidence_minimums:
            if requirement.minimum_records <= 0:
                raise ValueError(f"{campaign.project_id}: evidence minimum must be positive")
        if _STAGE_INDEX[gate.to_stage] >= _STAGE_INDEX[MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE]:
            hardware_types = {
                ExternalEvidenceType.QPU_EXECUTION,
                ExternalEvidenceType.QUANTUM_SENSOR,
                ExternalEvidenceType.PHYSICAL_METROLOGY,
                ExternalEvidenceType.MISSION_OPTIMIZATION,
            }
            if not any(req.evidence_type in hardware_types for req in gate.evidence_minimums):
                raise ValueError(f"{campaign.project_id}: hardware-stage gate lacks hardware/runtime evidence")
        expected_from = gate.to_stage
        expected_ordinal += 1

    if expected_from != MissionEvidenceStage.OPERATIONAL_DEMONSTRATION:
        raise ValueError(f"{campaign.project_id}: campaign does not terminate at operational demonstration")


def build_external_campaigns() -> tuple[ProjectEvidenceCampaign, ...]:
    campaigns: list[ProjectEvidenceCampaign] = []
    current = {row.project_id: row for row in CURRENT_QUANTUM_MISSION_INPUTS}
    if set(current) != set(_GATE_BUILDERS):
        missing = sorted(set(current) ^ set(_GATE_BUILDERS))
        raise ValueError(f"campaign/project matrix mismatch: {missing}")

    for project_id, row in current.items():
        all_gates = _GATE_BUILDERS[project_id]()
        current_index = _STAGE_INDEX[row.evidence_stage]
        gates = tuple(gate for gate in all_gates if _STAGE_INDEX[gate.from_stage] >= current_index)
        campaign = ProjectEvidenceCampaign(
            project_id=project_id,
            mission_lane=row.mission_lane,
            current_stage=row.evidence_stage,
            target_stage=MissionEvidenceStage.OPERATIONAL_DEMONSTRATION,
            target_score=MISSION_READY_TARGET,
            gates=gates,
            claim_control=(
                "Campaign gates define the remaining evidence acquisition sequence only. Structural gate satisfaction does not validate "
                "the scientific/engineering claim, prove quantum advantage, or grant deployment authority."
            ),
        )
        _validate_campaign(campaign)
        campaigns.append(campaign)
    return tuple(campaigns)


def _record_matches_gate(record: ExternalEvidenceRecord, gate: CampaignGate) -> bool:
    return record.project_id == gate.project_id and record.metadata.get("campaign_gate_id") == gate.gate_id


def _evaluate_gate(gate: CampaignGate, records: Iterable[ExternalEvidenceRecord], completed_preconditions: set[str]) -> GateEvaluation:
    reasons: list[str] = []
    missing_preconditions = [item for item in gate.preconditions if item not in completed_preconditions]
    if missing_preconditions:
        reasons.append("missing preconditions: " + ", ".join(missing_preconditions))

    accepted: list[ExternalEvidenceRecord] = []
    for record in records:
        if not _record_matches_gate(record, gate):
            continue
        decision = validate_external_evidence(record)
        if decision.accepted_for_intake:
            accepted.append(record)

    for requirement in gate.evidence_minimums:
        count = sum(1 for record in accepted if record.evidence_type == requirement.evidence_type)
        if count < requirement.minimum_records:
            reasons.append(f"{requirement.evidence_type.value} records {count} < required {requirement.minimum_records}")

    if gate.minimum_distinct_providers:
        providers = {record.provider_or_lab for record in accepted if record.provider_or_lab.strip()}
        if len(providers) < gate.minimum_distinct_providers:
            reasons.append(f"distinct providers {len(providers)} < required {gate.minimum_distinct_providers}")

    if gate.minimum_distinct_devices:
        devices = {record.backend_or_device for record in accepted if record.backend_or_device}
        if len(devices) < gate.minimum_distinct_devices:
            reasons.append(f"distinct devices {len(devices)} < required {gate.minimum_distinct_devices}")

    metadata_coverage = {key for record in accepted for key, value in record.metadata.items() if value}
    missing_metadata = [key for key in gate.required_metadata_keys if key not in metadata_coverage]
    if missing_metadata:
        reasons.append("missing metadata coverage: " + ", ".join(missing_metadata))

    if gate.allowed_environments and accepted:
        if not any(record.environment in gate.allowed_environments for record in accepted):
            reasons.append("no accepted record in allowed environment: " + ", ".join(gate.allowed_environments))

    return GateEvaluation(gate_id=gate.gate_id, satisfied=not reasons, reasons=tuple(reasons), accepted_record_count=len(accepted))


def evaluate_campaign(
    campaign: ProjectEvidenceCampaign,
    records: Iterable[ExternalEvidenceRecord],
    *,
    completed_preconditions: Iterable[str] = (),
) -> CampaignEvaluation:
    frozen_records = tuple(records)
    preconditions = set(completed_preconditions)
    achieved = campaign.current_stage
    evaluations: list[GateEvaluation] = []
    next_gate_id: str | None = None

    for gate in campaign.gates:
        result = _evaluate_gate(gate, frozen_records, preconditions)
        evaluations.append(result)
        if not result.satisfied:
            next_gate_id = gate.gate_id
            break
        achieved = gate.to_stage

    complete = achieved == campaign.target_stage
    return CampaignEvaluation(
        project_id=campaign.project_id,
        starting_stage=campaign.current_stage.value,
        achieved_stage=achieved.value,
        target_stage=campaign.target_stage.value,
        target_score=campaign.target_score,
        next_gate_id=None if complete else next_gate_id,
        complete=complete,
        gate_evaluations=tuple(evaluations),
        claim_control=(
            "A satisfied campaign gate means the declared evidence package is structurally present and stage-locked. "
            "Technical validity, mission-readiness scoring, independent review and deployment authorization remain separate decisions."
        ),
    )


def campaigns_as_dict() -> dict[str, object]:
    campaigns = build_external_campaigns()

    def encode_gate(gate: CampaignGate) -> dict[str, object]:
        return {
            "gate_id": gate.gate_id,
            "project_id": gate.project_id,
            "ordinal": gate.ordinal,
            "from_stage": gate.from_stage.value,
            "to_stage": gate.to_stage.value,
            "evidence_minimums": [
                {"evidence_type": row.evidence_type.value, "minimum_records": row.minimum_records}
                for row in gate.evidence_minimums
            ],
            "minimum_distinct_providers": gate.minimum_distinct_providers,
            "minimum_distinct_devices": gate.minimum_distinct_devices,
            "required_metadata_keys": list(gate.required_metadata_keys),
            "allowed_environments": list(gate.allowed_environments),
            "preconditions": list(gate.preconditions),
            "acceptance_statement": gate.acceptance_statement,
        }

    return {
        "schema_version": "1.1",
        "system": "Worldshepherd QRF External Evidence Acquisition Campaign",
        "mission_readiness_target": MISSION_READY_TARGET,
        "stage_skipping_prohibited": True,
        "stable_gate_ids_preserved_after_promotion": True,
        "gate_binding_field": "metadata.campaign_gate_id",
        "campaigns": [
            {
                "project_id": campaign.project_id,
                "mission_lane": campaign.mission_lane,
                "current_stage": campaign.current_stage.value,
                "target_stage": campaign.target_stage.value,
                "target_score": campaign.target_score,
                "active_gate_count": len(campaign.gates),
                "first_active_gate_id": campaign.gates[0].gate_id if campaign.gates else None,
                "gates": [encode_gate(gate) for gate in campaign.gates],
                "claim_control": campaign.claim_control,
            }
            for campaign in campaigns
        ],
        "claim_control": (
            "This artifact is an evidence-acquisition plan and stage-transition contract. It contains no fabricated external evidence "
            "and cannot itself raise any project's mission-readiness score."
        ),
    }
