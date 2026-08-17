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


@dataclass(frozen=True)
class GlobMappingDecision:
    admissible_for_quantum_experiment: bool
    reasons: tuple[str, ...]
    mission_use_decision: str
    claim_control: str


def _sha(value: str) -> bool:
    return value.startswith("sha256:") and len(value.split(":", 1)[1]) == 64


def evaluate_glob_mapping(mapping: GlobQuantumMapping) -> GlobMappingDecision:
    reasons: list[str] = []
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
            reasons.append(f"{field} is required")
    if not _sha(mapping.quantum_object_digest):
        reasons.append("quantum_object_digest must be a full sha256 identity")
    if mapping.null_model_id is None:
        reasons.append("null/randomized model is required before quantum attribution")
    if mapping.resource_estimate_id is None:
        reasons.append("resource estimate is required before QPU execution is justified")

    return GlobMappingDecision(
        admissible_for_quantum_experiment=not reasons,
        reasons=tuple(reasons),
        mission_use_decision="NO_GO_BELOW_97",
        claim_control=(
            "Admissibility means a genuine computational mapping exists. It does not make numerical coincidences, "
            "permutation structure, prime indexing, or symbolic quantum language into physical quantum evidence."
        ),
    )
