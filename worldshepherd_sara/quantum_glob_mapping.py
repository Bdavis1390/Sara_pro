"""Formal admissibility gate before any GLOB inquiry is sent to quantum execution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MappingType(str, Enum):
    ORACLE = "oracle"
    HAMILTONIAN = "hamiltonian"
    SEARCH = "search"
    SAMPLING = "sampling"
    OPTIMIZATION = "optimization"


@dataclass(frozen=True)
class GlobQuantumMapping:
    mapping_id: str
    mapping_type: MappingType
    input_contract: str
    output_contract: str
    measurable_target: str
    classical_baseline: str
    classical_complexity: str
    quantum_object_digest: str
    construction_cost: str
    verification_method: str
    resource_estimate_id: str | None = None
    null_model_id: str | None = None
    classical_dominates: bool = False
    quantum_execution_rationale: str | None = None


@dataclass(frozen=True)
class GlobMappingDecision:
    mapping_structurally_valid: bool
    admissible_for_quantum_experiment: bool
    qpu_execution_justified: bool
    reasons: tuple[str, ...]
    mission_use_decision: str
    claim_control: str


def _sha(value: str) -> bool:
    return value.startswith("sha256:") and len(value.split(":", 1)[1]) == 64


def evaluate_glob_mapping(mapping: GlobQuantumMapping) -> GlobMappingDecision:
    structural_reasons: list[str] = []
    for field in (
        "mapping_id",
        "input_contract",
        "output_contract",
        "measurable_target",
        "classical_baseline",
        "classical_complexity",
        "construction_cost",
        "verification_method",
    ):
        if not getattr(mapping, field).strip():
            structural_reasons.append(f"{field} is required")
    if not _sha(mapping.quantum_object_digest):
        structural_reasons.append("quantum_object_digest must be a full sha256 identity")
    if mapping.null_model_id is None:
        structural_reasons.append("null/randomized model is required before quantum attribution")

    mapping_valid = not structural_reasons
    execution_reasons: list[str] = []
    if mapping.resource_estimate_id is None:
        execution_reasons.append("resource estimate is required before QPU execution is justified")
    if mapping.classical_dominates:
        execution_reasons.append("declared classical baseline dominates this mapping; QPU execution is not justified")
    if mapping.quantum_execution_rationale is not None and not mapping.quantum_execution_rationale.strip():
        execution_reasons.append("quantum_execution_rationale cannot be blank when supplied")

    reasons = tuple(structural_reasons + execution_reasons)
    qpu_justified = mapping_valid and not execution_reasons
    return GlobMappingDecision(
        mapping_structurally_valid=mapping_valid,
        admissible_for_quantum_experiment=qpu_justified,
        qpu_execution_justified=qpu_justified,
        reasons=reasons,
        mission_use_decision="NO_GO_BELOW_97",
        claim_control=(
            "A structurally valid mapping means a genuine computational object exists. QPU execution is a separate decision. "
            "Numerical coincidences, permutation structure, prime indexing, or symbolic quantum language are not physical quantum evidence; "
            "a mapping that is classically trivial should remain a classical control rather than consuming QPU resources."
        ),
    )
