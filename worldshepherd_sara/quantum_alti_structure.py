"""Fail-closed physical-structure and reference-computation gate for WS-AlTi.

A composition, phase name, literature citation, or generated Hamiltonian is not a
physical structure. Before Worldshepherd may promote WS-ALTI-EXT-01, it must retain
an actual periodic structure artifact plus provenance and site-ordering identity.
Reference-computation records are bound to that frozen structure by digest.

This module validates evidence structure only. It does not determine whether a
candidate structure represents the full WS-AlTi M1-MSZ-Prime deposited alloy and
does not replace DFT, microscopy, diffraction, coupon, or materials qualification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Mapping


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_PLACEHOLDER_TOKENS = (
    "placeholder",
    "todo",
    "tbd",
    "unknown",
    "replace-me",
    "example-only",
    "<",
    ">",
)


class StructureFormat(str, Enum):
    CIF = "cif"
    POSCAR = "poscar"
    JSON = "json"


class StructureSourceType(str, Enum):
    EXPERIMENTAL_DATABASE = "experimental_database"
    COMPUTED_DATABASE = "computed_database"
    PEER_REVIEWED_PUBLICATION = "peer_reviewed_publication"
    WORLD_SHEPHERD_GENERATED = "worldshepherd_generated"


@dataclass(frozen=True)
class PeriodicStructureFreezeRecord:
    project_id: str
    structure_id: str
    composition: str
    phase_label: str
    structure_format: StructureFormat
    structure_digest: str
    source_type: StructureSourceType
    source_reference: str
    source_reference_digest: str
    periodicity: int
    space_group: str
    lattice_a_angstrom: float
    lattice_b_angstrom: float
    lattice_c_angstrom: float
    alpha_deg: float
    beta_deg: float
    gamma_deg: float
    atom_count: int
    species_counts: Mapping[str, int]
    site_ordering_digest: str
    modeling_scope: str
    generated_from_composition_only: bool = False
    claim_control: str = (
        "Frozen periodic structure candidate only. Acceptance does not establish that this structure is the full deposited "
        "WS-AlTi alloy, nor does it validate phase fraction, precipitation sequence, manufacturability, or material performance."
    )


@dataclass(frozen=True)
class StructureFreezeDecision:
    accepted: bool
    reasons: tuple[str, ...]
    structure_id: str
    structure_digest: str
    gate_id: str = "WS-ALTI-EXT-01"
    precondition_id: str = "WS-ALTI-P0-PHYSICAL-STRUCTURE-FROZEN"
    claim_control: str = (
        "Structural acceptance means the candidate is fully identified and provenance-controlled enough for downstream computation. "
        "It is not a DFT result, Hamiltonian result, coupon result, or materials qualification."
    )


@dataclass(frozen=True)
class ReferenceComputationRecord:
    project_id: str
    structure_id: str
    structure_digest: str
    computation_id: str
    code_name: str
    code_version: str
    method: str
    exchange_correlation: str
    basis_or_pseudopotential: str
    kpoint_definition: str
    spin_treatment: str
    convergence_energy_ev: float
    convergence_force_ev_per_angstrom: float
    input_digest: str
    output_digest: str
    total_energy_ev: float
    reference_kind: str
    source_reference: str
    claim_control: str = (
        "Reference-computation record only. Numerical agreement does not substitute for physical coupon validation and does not "
        "establish quantum advantage."
    )


@dataclass(frozen=True)
class ReferenceComputationDecision:
    accepted: bool
    reasons: tuple[str, ...]
    computation_id: str
    bound_structure_digest: str


def sha256_bytes(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    return sha256_bytes(payload.encode("utf-8"))


def structure_file_digest(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _is_sha(value: str) -> bool:
    return bool(_SHA256.fullmatch(value.strip().lower()))


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(token in lowered for token in _PLACEHOLDER_TOKENS)


def _positive_finite(value: float) -> bool:
    return value > 0 and value < float("inf")


def _angle(value: float) -> bool:
    return 0.0 < value < 180.0


def validate_structure_freeze(
    record: PeriodicStructureFreezeRecord,
    *,
    structure_file: str | Path | None = None,
) -> StructureFreezeDecision:
    reasons: list[str] = []
    if record.project_id != "WS-ALTI":
        reasons.append("project_id must be WS-ALTI")
    for field_name in ("structure_id", "composition", "phase_label", "source_reference", "space_group", "modeling_scope"):
        value = str(getattr(record, field_name))
        if _is_placeholder(value):
            reasons.append(f"{field_name} must be concrete and non-placeholder")
    if record.generated_from_composition_only:
        reasons.append("composition-only generation cannot satisfy the physical-structure freeze gate")
    if record.periodicity != 3:
        reasons.append("WS-AlTi electronic-structure benchmark requires a 3D periodic structure")
    if not _is_sha(record.structure_digest):
        reasons.append("structure_digest must be a sha256 digest")
    if not _is_sha(record.source_reference_digest):
        reasons.append("source_reference_digest must be a sha256 digest")
    if not _is_sha(record.site_ordering_digest):
        reasons.append("site_ordering_digest must be a sha256 digest")
    if record.atom_count <= 0:
        reasons.append("atom_count must be positive")
    if not record.species_counts or any(not species.strip() or count <= 0 for species, count in record.species_counts.items()):
        reasons.append("species_counts must contain positive counts for named species")
    elif sum(record.species_counts.values()) != record.atom_count:
        reasons.append("species_counts must sum to atom_count")
    for name in ("lattice_a_angstrom", "lattice_b_angstrom", "lattice_c_angstrom"):
        if not _positive_finite(float(getattr(record, name))):
            reasons.append(f"{name} must be positive")
    for name in ("alpha_deg", "beta_deg", "gamma_deg"):
        if not _angle(float(getattr(record, name))):
            reasons.append(f"{name} must be in (0, 180)")

    if structure_file is None:
        reasons.append("actual structure file is required; manifest-only freeze is prohibited")
    else:
        path = Path(structure_file)
        if not path.is_file() or path.stat().st_size == 0:
            reasons.append("actual structure file must exist and be non-empty")
        else:
            actual = structure_file_digest(path)
            if actual.lower() != record.structure_digest.lower():
                reasons.append("structure file digest does not match frozen structure_digest")

    return StructureFreezeDecision(
        accepted=not reasons,
        reasons=tuple(reasons),
        structure_id=record.structure_id,
        structure_digest=record.structure_digest,
    )


def validate_reference_computation(
    record: ReferenceComputationRecord,
    *,
    frozen_structure: PeriodicStructureFreezeRecord,
) -> ReferenceComputationDecision:
    reasons: list[str] = []
    if record.project_id != "WS-ALTI":
        reasons.append("project_id must be WS-ALTI")
    if record.structure_id != frozen_structure.structure_id:
        reasons.append("reference computation structure_id does not match frozen structure")
    if record.structure_digest.lower() != frozen_structure.structure_digest.lower():
        reasons.append("reference computation is not bound to frozen structure digest")
    for field_name in (
        "computation_id", "code_name", "code_version", "method", "exchange_correlation",
        "basis_or_pseudopotential", "kpoint_definition", "spin_treatment", "reference_kind", "source_reference",
    ):
        if _is_placeholder(str(getattr(record, field_name))):
            reasons.append(f"{field_name} must be concrete and non-placeholder")
    for field_name in ("input_digest", "output_digest", "structure_digest"):
        if not _is_sha(str(getattr(record, field_name))):
            reasons.append(f"{field_name} must be a sha256 digest")
    if not _positive_finite(record.convergence_energy_ev):
        reasons.append("convergence_energy_ev must be positive")
    if not _positive_finite(record.convergence_force_ev_per_angstrom):
        reasons.append("convergence_force_ev_per_angstrom must be positive")
    if not (-1e9 < record.total_energy_ev < 1e9):
        reasons.append("total_energy_ev is not finite/reasonable")

    return ReferenceComputationDecision(
        accepted=not reasons,
        reasons=tuple(reasons),
        computation_id=record.computation_id,
        bound_structure_digest=record.structure_digest,
    )


def structure_template_as_dict() -> dict[str, object]:
    """Return a deliberately incomplete acquisition template.

    Placeholder values are intentional: validate_structure_freeze must reject this
    template until an actual structure artifact and provenance have been supplied.
    """
    return {
        "schema_version": "1.0",
        "gate_id": "WS-ALTI-EXT-01",
        "precondition_id": "WS-ALTI-P0-PHYSICAL-STRUCTURE-FROZEN",
        "record": {
            "project_id": "WS-ALTI",
            "structure_id": "<replace-me>",
            "composition": "<replace-me>",
            "phase_label": "<replace-me>",
            "structure_format": "cif|poscar|json",
            "structure_digest": "<sha256-of-actual-structure-file>",
            "source_type": "experimental_database|computed_database|peer_reviewed_publication|worldshepherd_generated",
            "source_reference": "<doi/mp-id/database-id/repository-reference>",
            "source_reference_digest": "<sha256-of-retained-source-metadata>",
            "periodicity": 3,
            "space_group": "<replace-me>",
            "lattice_a_angstrom": None,
            "lattice_b_angstrom": None,
            "lattice_c_angstrom": None,
            "alpha_deg": None,
            "beta_deg": None,
            "gamma_deg": None,
            "atom_count": None,
            "species_counts": {},
            "site_ordering_digest": "<sha256-of-canonical-site-list>",
            "modeling_scope": "<e.g. precipitate reference, host, interface, SQS substitution model>",
            "generated_from_composition_only": False
        },
        "required_artifacts": [
            "actual CIF/POSCAR/JSON periodic structure file",
            "retained source/provenance metadata",
            "canonical site/species ordering representation",
            "structure SHA-256 and source/site-ordering SHA-256 values"
        ],
        "claim_control": (
            "Template only. It must fail validation until replaced by a real periodic structure artifact with provenance. "
            "A nominal WS-AlTi alloy composition is not sufficient to infer atomic coordinates or phase occupancy."
        )
    }
