"""Worldshepherd Quantum Readiness Fabric (QRF).

This module does not claim possession of quantum hardware or quantum advantage.
It provides an evidence-gated control model for deciding when a Worldshepherd
project may legitimately use quantum simulation, real QPU execution, resource
estimation, quantum sensing/networking partners, or post-quantum controls.

The design intentionally keeps the core dependency-free. Vendor adapters
(Qiskit, Braket, CUDA-Q, Q#, etc.) can sit behind the backend contract without
making the governance layer provider-specific.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping


class EvidenceLevel(str, Enum):
    CONCEPT = "concept"
    CLASSICAL_BASELINE = "classical_baseline"
    IDEAL_SIMULATION = "ideal_simulation"
    NOISY_SIMULATION = "noisy_simulation"
    RESOURCE_ESTIMATED = "resource_estimated"
    QPU_EXECUTED = "qpu_executed"
    REPRODUCED_QPU = "reproduced_qpu"
    INDEPENDENTLY_REPRODUCED = "independently_reproduced"


class QuantumDomain(str, Enum):
    COMPUTING = "quantum_computing"
    SENSING = "quantum_sensing"
    NETWORKING = "quantum_networking"
    MATERIALS = "quantum_materials"
    SECURITY = "post_quantum_security"


class BackendClass(str, Enum):
    CLASSICAL = "classical"
    STATEVECTOR = "statevector_simulator"
    NOISY_SIMULATOR = "noisy_simulator"
    RESOURCE_ESTIMATOR = "fault_tolerant_resource_estimator"
    QPU = "qpu"
    EXTERNAL_SENSOR = "external_quantum_sensor"
    EXTERNAL_NETWORK = "external_quantum_network"


class ClaimClass(str, Enum):
    CLASSICAL_ONLY = "classical_only"
    QUANTUM_INSPIRED = "quantum_inspired"
    QUANTUM_SIMULATED = "quantum_simulated"
    QUANTUM_EXECUTED = "quantum_executed"
    QUANTUM_VALIDATED = "quantum_validated"
    QUANTUM_ADVANTAGE_CANDIDATE = "quantum_advantage_candidate"


_EVIDENCE_ORDER = {
    EvidenceLevel.CONCEPT: 0,
    EvidenceLevel.CLASSICAL_BASELINE: 1,
    EvidenceLevel.IDEAL_SIMULATION: 2,
    EvidenceLevel.NOISY_SIMULATION: 3,
    EvidenceLevel.RESOURCE_ESTIMATED: 4,
    EvidenceLevel.QPU_EXECUTED: 5,
    EvidenceLevel.REPRODUCED_QPU: 6,
    EvidenceLevel.INDEPENDENTLY_REPRODUCED: 7,
}


@dataclass(frozen=True)
class QuantumBackendRecord:
    provider: str
    backend: str
    backend_class: BackendClass
    modality: str = "unspecified"
    calibration_id: str | None = None
    native_gate_set: tuple[str, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class QuantumRunEvidence:
    project_id: str
    experiment_id: str
    domain: QuantumDomain
    evidence_level: EvidenceLevel
    backend: QuantumBackendRecord
    algorithm: str
    classical_baseline_id: str | None = None
    circuit_digest: str | None = None
    qasm_or_qir_digest: str | None = None
    shots: int | None = None
    logical_qubits: int | None = None
    physical_qubits_estimate: int | None = None
    logical_gate_count: int | None = None
    estimated_runtime_seconds: float | None = None
    result_digest: str | None = None
    uncertainty: float | None = None
    seed: int | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectQuantumProfile:
    project_id: str
    domains: tuple[QuantumDomain, ...]
    allowed_claim_ceiling: ClaimClass
    required_minimum_evidence: EvidenceLevel
    classical_baseline_required: bool = True
    partner_hardware_required: bool = True
    recommended_algorithms: tuple[str, ...] = ()
    prohibited_shortcuts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReadinessDecision:
    accepted: bool
    claim_class: ClaimClass
    reasons: tuple[str, ...]


def evidence_at_least(actual: EvidenceLevel, required: EvidenceLevel) -> bool:
    return _EVIDENCE_ORDER[actual] >= _EVIDENCE_ORDER[required]


def classify_claim(evidence: QuantumRunEvidence) -> ClaimClass:
    """Return the strongest defensible claim from a single evidence record."""
    if evidence.backend.backend_class == BackendClass.CLASSICAL:
        return ClaimClass.CLASSICAL_ONLY
    if evidence.evidence_level in {
        EvidenceLevel.IDEAL_SIMULATION,
        EvidenceLevel.NOISY_SIMULATION,
        EvidenceLevel.RESOURCE_ESTIMATED,
    }:
        return ClaimClass.QUANTUM_SIMULATED
    if evidence.evidence_level == EvidenceLevel.QPU_EXECUTED:
        return ClaimClass.QUANTUM_EXECUTED
    if evidence.evidence_level in {
        EvidenceLevel.REPRODUCED_QPU,
        EvidenceLevel.INDEPENDENTLY_REPRODUCED,
    }:
        return ClaimClass.QUANTUM_VALIDATED
    return ClaimClass.QUANTUM_INSPIRED


def evaluate_run(
    profile: ProjectQuantumProfile,
    evidence: QuantumRunEvidence,
) -> ReadinessDecision:
    reasons: list[str] = []

    if evidence.project_id != profile.project_id:
        reasons.append("project_id does not match the governed profile")
    if evidence.domain not in profile.domains:
        reasons.append("quantum domain is not approved for this project")
    if not evidence_at_least(evidence.evidence_level, profile.required_minimum_evidence):
        reasons.append(
            f"evidence level {evidence.evidence_level.value} is below required "
            f"{profile.required_minimum_evidence.value}"
        )
    if profile.classical_baseline_required and not evidence.classical_baseline_id:
        reasons.append("classical baseline is required before quantum attribution")
    if evidence.backend.backend_class == BackendClass.QPU and not evidence.result_digest:
        reasons.append("QPU execution requires an immutable result digest")
    if evidence.evidence_level == EvidenceLevel.RESOURCE_ESTIMATED:
        if evidence.physical_qubits_estimate is None or evidence.estimated_runtime_seconds is None:
            reasons.append("resource-estimated claims require qubit and runtime estimates")
    if evidence.evidence_level in {
        EvidenceLevel.REPRODUCED_QPU,
        EvidenceLevel.INDEPENDENTLY_REPRODUCED,
    } and evidence.circuit_digest is None:
        reasons.append("reproduced QPU claims require a circuit digest")

    claim = classify_claim(evidence)
    claim_rank = list(ClaimClass).index(claim)
    ceiling_rank = list(ClaimClass).index(profile.allowed_claim_ceiling)
    if claim_rank > ceiling_rank:
        reasons.append(
            f"claim {claim.value} exceeds project ceiling {profile.allowed_claim_ceiling.value}"
        )

    return ReadinessDecision(not reasons, claim, tuple(reasons))


def cross_backend_reproducible(records: Iterable[QuantumRunEvidence]) -> bool:
    """Require at least two QPU providers/backends and identical circuit/result identity.

    This is intentionally strict. A richer statistical equivalence test belongs in the
    execution adapter, but governance should not call one vendor run 'reproduced'.
    """
    rows = [r for r in records if r.backend.backend_class == BackendClass.QPU]
    if len(rows) < 2:
        return False
    if len({(r.backend.provider, r.backend.backend) for r in rows}) < 2:
        return False
    circuit_digests = {r.circuit_digest for r in rows}
    if None in circuit_digests or len(circuit_digests) != 1:
        return False
    result_digests = {r.result_digest for r in rows}
    return None not in result_digests and len(result_digests) == 1


PROJECT_PROFILES: dict[str, ProjectQuantumProfile] = {
    "SARA-QRF": ProjectQuantumProfile(
        project_id="SARA-QRF",
        domains=(QuantumDomain.COMPUTING, QuantumDomain.SECURITY),
        allowed_claim_ceiling=ClaimClass.QUANTUM_VALIDATED,
        required_minimum_evidence=EvidenceLevel.CLASSICAL_BASELINE,
        partner_hardware_required=True,
        recommended_algorithms=("provider-agnostic job orchestration", "resource estimation"),
        prohibited_shortcuts=("simulator result labeled as QPU result", "missing backend calibration/provenance"),
    ),
    "WS-ALTI": ProjectQuantumProfile(
        project_id="WS-ALTI",
        domains=(QuantumDomain.MATERIALS, QuantumDomain.COMPUTING),
        allowed_claim_ceiling=ClaimClass.QUANTUM_VALIDATED,
        required_minimum_evidence=EvidenceLevel.CLASSICAL_BASELINE,
        partner_hardware_required=True,
        recommended_algorithms=("VQE", "quantum subspace methods", "Hamiltonian simulation"),
        prohibited_shortcuts=("replace DFT/experiment with unvalidated VQE",),
    ),
    "WS-METASURFACE": ProjectQuantumProfile(
        project_id="WS-METASURFACE",
        domains=(QuantumDomain.COMPUTING, QuantumDomain.SENSING, QuantumDomain.MATERIALS),
        allowed_claim_ceiling=ClaimClass.QUANTUM_VALIDATED,
        required_minimum_evidence=EvidenceLevel.CLASSICAL_BASELINE,
        partner_hardware_required=True,
        recommended_algorithms=("QAOA benchmark", "quantum sensing partner test", "materials Hamiltonian study"),
        prohibited_shortcuts=("call signed classical coupling entanglement",),
    ),
    "WS-APNT": ProjectQuantumProfile(
        project_id="WS-APNT",
        domains=(QuantumDomain.SENSING, QuantumDomain.NETWORKING, QuantumDomain.SECURITY),
        allowed_claim_ceiling=ClaimClass.QUANTUM_VALIDATED,
        required_minimum_evidence=EvidenceLevel.CLASSICAL_BASELINE,
        partner_hardware_required=True,
        recommended_algorithms=("atomic-clock integration", "quantum inertial/magnetic sensing", "PQC"),
        prohibited_shortcuts=("claim in-house quantum sensor without calibrated hardware",),
    ),
    "WS-GLOB": ProjectQuantumProfile(
        project_id="WS-GLOB",
        domains=(QuantumDomain.COMPUTING,),
        allowed_claim_ceiling=ClaimClass.QUANTUM_SIMULATED,
        required_minimum_evidence=EvidenceLevel.CLASSICAL_BASELINE,
        partner_hardware_required=False,
        recommended_algorithms=("oracle/circuit formulation only after problem mapping",),
        prohibited_shortcuts=("treat numerology/permutation structure as quantum evidence",),
    ),
    "WS-EM-PROPULSION": ProjectQuantumProfile(
        project_id="WS-EM-PROPULSION",
        domains=(QuantumDomain.MATERIALS, QuantumDomain.SENSING),
        allowed_claim_ceiling=ClaimClass.QUANTUM_SIMULATED,
        required_minimum_evidence=EvidenceLevel.CLASSICAL_BASELINE,
        partner_hardware_required=True,
        recommended_algorithms=("materials electronic-structure study", "quantum sensor metrology"),
        prohibited_shortcuts=("use quantum simulation as evidence of anomalous thrust",),
    ),
    "WS-AUTONOMOUS-LOGISTICS": ProjectQuantumProfile(
        project_id="WS-AUTONOMOUS-LOGISTICS",
        domains=(QuantumDomain.COMPUTING, QuantumDomain.SECURITY),
        allowed_claim_ceiling=ClaimClass.QUANTUM_VALIDATED,
        required_minimum_evidence=EvidenceLevel.CLASSICAL_BASELINE,
        partner_hardware_required=True,
        recommended_algorithms=("QAOA", "hybrid combinatorial optimization", "PQC"),
        prohibited_shortcuts=("deploy quantum path without classical cost/latency win",),
    ),
}
