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
from itertools import combinations
from math import isfinite, sqrt
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
    outcome_distribution: Mapping[str, float] = field(default_factory=dict)
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


@dataclass(frozen=True)
class CrossBackendReproducibilityDecision:
    reproducible: bool
    reasons: tuple[str, ...]
    providers_backends: tuple[str, ...]
    canonical_program_digest: str | None
    max_total_variation_distance_observed: float | None
    min_bhattacharyya_fidelity_observed: float | None
    max_total_variation_distance_allowed: float
    min_bhattacharyya_fidelity_required: float
    claim_control: str = (
        "Statistical cross-backend agreement supports a reproduced-QPU evidence claim only for the frozen canonical workload and declared tolerances. "
        "It does not establish quantum advantage, physical-model validity, or mission readiness by itself."
    )


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
    } and evidence.circuit_digest is None and evidence.qasm_or_qir_digest is None:
        reasons.append("reproduced QPU claims require a canonical circuit/program digest")

    claim = classify_claim(evidence)
    claim_rank = list(ClaimClass).index(claim)
    ceiling_rank = list(ClaimClass).index(profile.allowed_claim_ceiling)
    if claim_rank > ceiling_rank:
        reasons.append(
            f"claim {claim.value} exceeds project ceiling {profile.allowed_claim_ceiling.value}"
        )

    return ReadinessDecision(not reasons, claim, tuple(reasons))


def _canonical_program_digest(record: QuantumRunEvidence) -> str | None:
    return record.qasm_or_qir_digest or record.circuit_digest


def _normalized_distribution(values: Mapping[str, float]) -> dict[str, float] | None:
    if not values:
        return None
    normalized: dict[str, float] = {}
    total = 0.0
    for key, raw in values.items():
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if not isfinite(value) or value < 0:
            return None
        normalized[str(key)] = value
        total += value
    if total <= 0:
        return None
    return {key: value / total for key, value in normalized.items()}


def total_variation_distance(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    """Return TVD for two count/probability mappings after normalization."""
    p = _normalized_distribution(left)
    q = _normalized_distribution(right)
    if p is None or q is None:
        raise ValueError("distributions must be non-empty, finite and non-negative")
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(key, 0.0) - q.get(key, 0.0)) for key in keys)


def bhattacharyya_fidelity(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    """Return squared Bhattacharyya coefficient in [0,1] after normalization."""
    p = _normalized_distribution(left)
    q = _normalized_distribution(right)
    if p is None or q is None:
        raise ValueError("distributions must be non-empty, finite and non-negative")
    keys = set(p) | set(q)
    coefficient = sum(sqrt(p.get(key, 0.0) * q.get(key, 0.0)) for key in keys)
    return min(1.0, max(0.0, coefficient * coefficient))


def evaluate_cross_backend_reproducibility(
    records: Iterable[QuantumRunEvidence],
    *,
    max_total_variation_distance: float = 0.10,
    min_bhattacharyya_fidelity: float = 0.95,
) -> CrossBackendReproducibilityDecision:
    """Evaluate sampled-QPU reproduction using canonical identity plus distributions.

    Independent hardware runs should retain distinct immutable result identities. Exact
    equality of sampled result digests is neither expected nor required. Reproduction
    instead requires the same frozen canonical workload and declared pairwise statistical
    tolerances across at least two distinct real QPU backends.
    """
    if not 0.0 <= max_total_variation_distance <= 1.0:
        raise ValueError("max_total_variation_distance must be in [0,1]")
    if not 0.0 <= min_bhattacharyya_fidelity <= 1.0:
        raise ValueError("min_bhattacharyya_fidelity must be in [0,1]")

    rows = [record for record in records if record.backend.backend_class == BackendClass.QPU]
    reasons: list[str] = []
    backend_ids = tuple(sorted({f"{r.backend.provider}/{r.backend.backend}" for r in rows}))

    if len(rows) < 2:
        reasons.append("at least two real QPU records are required")
    if len(backend_ids) < 2:
        reasons.append("at least two distinct provider/backend identities are required")

    projects = {r.project_id for r in rows}
    algorithms = {r.algorithm for r in rows}
    baselines = {r.classical_baseline_id for r in rows}
    if len(projects) > 1:
        reasons.append("all reproduction records must belong to the same project")
    if len(algorithms) > 1:
        reasons.append("all reproduction records must use the same governed algorithm label")
    if None in baselines or len(baselines) != 1:
        reasons.append("all reproduction records must bind to the same classical baseline")

    program_digests = {_canonical_program_digest(r) for r in rows}
    canonical_digest = next(iter(program_digests)) if len(program_digests) == 1 else None
    if None in program_digests or len(program_digests) != 1:
        reasons.append("all reproduction records must share one canonical program digest")

    result_digests = [r.result_digest for r in rows]
    if any(digest is None for digest in result_digests):
        reasons.append("every QPU reproduction record requires an immutable result digest")
    elif len(set(result_digests)) != len(result_digests):
        reasons.append("independent QPU runs must retain distinct result-record digests")

    experiment_ids = [r.experiment_id for r in rows]
    if len(set(experiment_ids)) != len(experiment_ids):
        reasons.append("independent QPU runs require distinct experiment/run identities")

    distributions: list[dict[str, float]] = []
    for record in rows:
        normalized = _normalized_distribution(record.outcome_distribution)
        if normalized is None:
            reasons.append(f"{record.experiment_id} lacks a valid sampled outcome distribution")
        else:
            distributions.append(normalized)

    tvd_values: list[float] = []
    fidelity_values: list[float] = []
    if len(distributions) == len(rows) and len(rows) >= 2:
        for left, right in combinations(distributions, 2):
            tvd_values.append(total_variation_distance(left, right))
            fidelity_values.append(bhattacharyya_fidelity(left, right))

    max_tvd_observed = max(tvd_values) if tvd_values else None
    min_fidelity_observed = min(fidelity_values) if fidelity_values else None
    if max_tvd_observed is not None and max_tvd_observed > max_total_variation_distance:
        reasons.append(
            f"pairwise total-variation distance {max_tvd_observed:.6f} exceeds declared limit {max_total_variation_distance:.6f}"
        )
    if min_fidelity_observed is not None and min_fidelity_observed < min_bhattacharyya_fidelity:
        reasons.append(
            f"pairwise Bhattacharyya fidelity {min_fidelity_observed:.6f} is below declared minimum {min_bhattacharyya_fidelity:.6f}"
        )

    return CrossBackendReproducibilityDecision(
        reproducible=not reasons,
        reasons=tuple(reasons),
        providers_backends=backend_ids,
        canonical_program_digest=canonical_digest,
        max_total_variation_distance_observed=max_tvd_observed,
        min_bhattacharyya_fidelity_observed=min_fidelity_observed,
        max_total_variation_distance_allowed=max_total_variation_distance,
        min_bhattacharyya_fidelity_required=min_bhattacharyya_fidelity,
    )


def cross_backend_reproducible(
    records: Iterable[QuantumRunEvidence],
    *,
    max_total_variation_distance: float = 0.10,
    min_bhattacharyya_fidelity: float = 0.95,
) -> bool:
    """Compatibility wrapper returning the governed statistical reproduction verdict."""
    return evaluate_cross_backend_reproducibility(
        records,
        max_total_variation_distance=max_total_variation_distance,
        min_bhattacharyya_fidelity=min_bhattacharyya_fidelity,
    ).reproducible


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
