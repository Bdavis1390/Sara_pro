"""Mission-readiness calibration for Worldshepherd quantum project lanes.

This is not TRL, certification, deployment authority, or an acquisition decision.
It is an evidence-capped engineering calibration used to prevent synthetic or
simulator evidence from being mistaken for mission-ready capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MissionEvidenceStage(str, Enum):
    CONCEPT = "concept"
    SYNTHETIC_SURROGATE = "synthetic_surrogate"
    CALIBRATED_MODEL = "calibrated_model"
    INTEGRATED_SIMULATION = "integrated_simulation"
    SINGLE_EXTERNAL_HARDWARE = "single_external_hardware"
    REPRODUCED_HARDWARE = "reproduced_hardware"
    HARDWARE_IN_LOOP = "hardware_in_loop"
    RELEVANT_ENVIRONMENT = "relevant_environment"
    OPERATIONAL_DEMONSTRATION = "operational_demonstration"


_STAGE_CAP = {
    MissionEvidenceStage.CONCEPT: 15,
    MissionEvidenceStage.SYNTHETIC_SURROGATE: 30,
    MissionEvidenceStage.CALIBRATED_MODEL: 45,
    MissionEvidenceStage.INTEGRATED_SIMULATION: 55,
    MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE: 65,
    MissionEvidenceStage.REPRODUCED_HARDWARE: 75,
    MissionEvidenceStage.HARDWARE_IN_LOOP: 85,
    MissionEvidenceStage.RELEVANT_ENVIRONMENT: 92,
    MissionEvidenceStage.OPERATIONAL_DEMONSTRATION: 100,
}


@dataclass(frozen=True)
class MissionReadinessInputs:
    project_id: str
    mission_lane: str
    evidence_stage: MissionEvidenceStage
    mission_fidelity: int
    classical_comparator: int
    quantum_evidence_reproducibility: int
    integration_interoperability: int
    security_provenance: int
    degraded_latency_cost: int
    physical_environment_validation: int
    blockers: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class MissionReadinessDecision:
    project_id: str
    mission_lane: str
    evidence_stage: str
    raw_score: int
    evidence_cap: int
    mission_readiness_score: int
    readiness_band: str
    blockers: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    next_gate: str
    claim_control: str


_MAXIMA = {
    "mission_fidelity": 20,
    "classical_comparator": 15,
    "quantum_evidence_reproducibility": 15,
    "integration_interoperability": 15,
    "security_provenance": 10,
    "degraded_latency_cost": 15,
    "physical_environment_validation": 10,
}


def _validate(inputs: MissionReadinessInputs) -> None:
    if not inputs.project_id.strip() or not inputs.mission_lane.strip():
        raise ValueError("project_id and mission_lane are required")
    for field, maximum in _MAXIMA.items():
        value = getattr(inputs, field)
        if not isinstance(value, int) or not 0 <= value <= maximum:
            raise ValueError(f"{field} must be an integer in [0, {maximum}]")


def readiness_band(score: int) -> str:
    if score < 15:
        return "RESEARCH_ONLY"
    if score < 30:
        return "BENCH_READY"
    if score < 45:
        return "MISSION_SURROGATE"
    if score < 60:
        return "INTEGRATED_LAB"
    if score < 75:
        return "HARDWARE_BACKED"
    if score < 90:
        return "RELEVANT_ENVIRONMENT"
    return "OPERATIONALLY_DEMONSTRATED"


def _next_gate(stage: MissionEvidenceStage) -> str:
    return {
        MissionEvidenceStage.CONCEPT: "freeze a measurable problem and strong classical/truth baseline",
        MissionEvidenceStage.SYNTHETIC_SURROGATE: "replace synthetic instance with calibrated mission-relevant model/data",
        MissionEvidenceStage.CALIBRATED_MODEL: "execute integrated noisy/hardware-aware workflow with operational telemetry",
        MissionEvidenceStage.INTEGRATED_SIMULATION: "execute on named external QPU/sensor hardware with retained provenance",
        MissionEvidenceStage.SINGLE_EXTERNAL_HARDWARE: "repeat and reproduce hardware result on another run/backend where practical",
        MissionEvidenceStage.REPRODUCED_HARDWARE: "integrate hardware-in-loop with mission interfaces and degraded-state tests",
        MissionEvidenceStage.HARDWARE_IN_LOOP: "demonstrate in a relevant environment with truth/reference instrumentation",
        MissionEvidenceStage.RELEVANT_ENVIRONMENT: "complete operational demonstration under declared mission constraints",
        MissionEvidenceStage.OPERATIONAL_DEMONSTRATION: "sustain configuration control, regression evidence, and deployment authorization",
    }[stage]


def calibrate_mission_readiness(inputs: MissionReadinessInputs) -> MissionReadinessDecision:
    _validate(inputs)
    raw = sum(getattr(inputs, field) for field in _MAXIMA)
    cap = _STAGE_CAP[inputs.evidence_stage]
    score = min(raw, cap)
    return MissionReadinessDecision(
        project_id=inputs.project_id,
        mission_lane=inputs.mission_lane,
        evidence_stage=inputs.evidence_stage.value,
        raw_score=raw,
        evidence_cap=cap,
        mission_readiness_score=score,
        readiness_band=readiness_band(score),
        blockers=tuple(inputs.blockers),
        evidence_refs=tuple(inputs.evidence_refs),
        next_gate=_next_gate(inputs.evidence_stage),
        claim_control=(
            "Worldshepherd Mission Readiness Calibration is an internal evidence-governed engineering measure. "
            "It is not TRL, certification, deployment approval, combat suitability, safety approval, or proof of quantum advantage."
        ),
    )


CURRENT_QUANTUM_MISSION_INPUTS: tuple[MissionReadinessInputs, ...] = (
    MissionReadinessInputs(
        project_id="SARA-QRF",
        mission_lane="quantum orchestration and evidence control",
        evidence_stage=MissionEvidenceStage.INTEGRATED_SIMULATION,
        mission_fidelity=14,
        classical_comparator=14,
        quantum_evidence_reproducibility=12,
        integration_interoperability=13,
        security_provenance=8,
        degraded_latency_cost=6,
        physical_environment_validation=0,
        blockers=(
            "no real QPU execution retained yet",
            "QPU queue/cost/failure behavior not measured in the SARA control loop",
        ),
        evidence_refs=("QRF-BELL-001", "SARA evidence-registry bridge", "Python 3.10/3.12 CI"),
    ),
    MissionReadinessInputs(
        project_id="WS-APNT",
        mission_lane="quantum sensing and assured PNT integration",
        evidence_stage=MissionEvidenceStage.CONCEPT,
        mission_fidelity=11,
        classical_comparator=8,
        quantum_evidence_reproducibility=0,
        integration_interoperability=7,
        security_provenance=6,
        degraded_latency_cost=5,
        physical_environment_validation=0,
        blockers=("no calibrated quantum sensor/device/dataset under Worldshepherd test control",),
        evidence_refs=("WS-APNT-QS-001 design contract",),
    ),
    MissionReadinessInputs(
        project_id="WS-ALTI",
        mission_lane="quantum materials computation",
        evidence_stage=MissionEvidenceStage.CONCEPT,
        mission_fidelity=8,
        classical_comparator=6,
        quantum_evidence_reproducibility=0,
        integration_interoperability=5,
        security_provenance=5,
        degraded_latency_cost=2,
        physical_environment_validation=0,
        blockers=(
            "physically specified reduced Hamiltonian not yet frozen",
            "DFT/exact-active-space comparison not yet executed",
        ),
        evidence_refs=("WS-ALTI-QM-001 design contract",),
    ),
    MissionReadinessInputs(
        project_id="WS-METASURFACE",
        mission_lane="discrete tile-state quantum optimization challenger",
        evidence_stage=MissionEvidenceStage.SYNTHETIC_SURROGATE,
        mission_fidelity=8,
        classical_comparator=15,
        quantum_evidence_reproducibility=8,
        integration_interoperability=6,
        security_provenance=7,
        degraded_latency_cost=4,
        physical_environment_validation=0,
        blockers=(
            "current QAOA instance is synthetic and not calibrated to a full-wave EM model",
            "no real QPU execution",
        ),
        evidence_refs=("WS-META-QO-001",),
    ),
    MissionReadinessInputs(
        project_id="WS-AUTONOMOUS-LOGISTICS",
        mission_lane="hybrid quantum route/assignment optimization challenger",
        evidence_stage=MissionEvidenceStage.SYNTHETIC_SURROGATE,
        mission_fidelity=8,
        classical_comparator=15,
        quantum_evidence_reproducibility=8,
        integration_interoperability=6,
        security_provenance=7,
        degraded_latency_cost=5,
        physical_environment_validation=0,
        blockers=(
            "current optimization instance is synthetic and not a mission instance family",
            "QPU queue, cost, communications, and degraded-state performance are unmeasured",
        ),
        evidence_refs=("WS-LOG-QO-001",),
    ),
    MissionReadinessInputs(
        project_id="WS-EM-PROPULSION",
        mission_lane="quantum materials and metrology support only",
        evidence_stage=MissionEvidenceStage.CONCEPT,
        mission_fidelity=6,
        classical_comparator=7,
        quantum_evidence_reproducibility=0,
        integration_interoperability=3,
        security_provenance=5,
        degraded_latency_cost=1,
        physical_environment_validation=0,
        blockers=(
            "no project-specific quantum materials benchmark executed",
            "physical force claims remain gated by independent controlled measurement",
        ),
        evidence_refs=("WS-EMP-QM-001 design contract",),
    ),
    MissionReadinessInputs(
        project_id="WS-GLOB",
        mission_lane="conditional quantum problem mapping",
        evidence_stage=MissionEvidenceStage.CONCEPT,
        mission_fidelity=4,
        classical_comparator=9,
        quantum_evidence_reproducibility=0,
        integration_interoperability=2,
        security_provenance=5,
        degraded_latency_cost=1,
        physical_environment_validation=0,
        blockers=("no legitimate oracle/Hamiltonian/search objective mapping has passed the gate",),
        evidence_refs=("WS-GLOB-QMAPPING-001 design contract",),
    ),
)


def current_quantum_mission_calibration() -> tuple[MissionReadinessDecision, ...]:
    return tuple(calibrate_mission_readiness(row) for row in CURRENT_QUANTUM_MISSION_INPUTS)
