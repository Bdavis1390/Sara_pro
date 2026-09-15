"""Typed intake validation for external evidence needed to cross the 97 gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class ExternalEvidenceType(str, Enum):
    QPU_EXECUTION = "qpu_execution"
    QUANTUM_SENSOR = "quantum_sensor"
    MATERIALS_HAMILTONIAN = "materials_hamiltonian"
    CALIBRATED_PHYSICS_MODEL = "calibrated_physics_model"
    MISSION_OPTIMIZATION = "mission_optimization"
    PHYSICAL_METROLOGY = "physical_metrology"


@dataclass(frozen=True)
class ExternalEvidenceRecord:
    project_id: str
    evidence_type: ExternalEvidenceType
    source_id: str
    raw_artifact_digest: str
    collected_utc: str
    provider_or_lab: str
    configuration_digest: str
    repeat_count: int = 1
    calibration_id: str | None = None
    truth_reference_id: str | None = None
    uncertainty: float | None = None
    result_digest: str | None = None
    classical_baseline_digest: str | None = None
    job_or_run_id: str | None = None
    backend_or_device: str | None = None
    latency_seconds: float | None = None
    cost_usd: float | None = None
    environment: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalEvidenceDecision:
    accepted_for_intake: bool
    evidence_type: str
    reasons: tuple[str, ...]
    claim_control: str


def _is_sha256(value: str | None) -> bool:
    if value is None or not value.startswith("sha256:"):
        return False
    digest = value.split(":", 1)[1]
    return len(digest) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in digest)


def validate_external_evidence(record: ExternalEvidenceRecord) -> ExternalEvidenceDecision:
    reasons: list[str] = []
    if not record.project_id.strip():
        reasons.append("project_id is required")
    if not record.source_id.strip() or not record.provider_or_lab.strip():
        reasons.append("source_id and provider_or_lab are required")
    if not _is_sha256(record.raw_artifact_digest):
        reasons.append("raw_artifact_digest must be a full sha256 identity")
    if not _is_sha256(record.configuration_digest):
        reasons.append("configuration_digest must be a full sha256 identity")
    if "T" not in record.collected_utc or not record.collected_utc.endswith("Z"):
        reasons.append("collected_utc must be an explicit UTC timestamp ending in Z")
    if record.repeat_count <= 0:
        reasons.append("repeat_count must be positive")

    if record.evidence_type == ExternalEvidenceType.QPU_EXECUTION:
        if not record.backend_or_device or not record.job_or_run_id:
            reasons.append("QPU evidence requires backend/device and job/run ID")
        if not _is_sha256(record.result_digest):
            reasons.append("QPU evidence requires immutable result digest")
        if record.latency_seconds is None or record.latency_seconds < 0:
            reasons.append("QPU evidence requires measured end-to-end latency")
        if record.cost_usd is None or record.cost_usd < 0:
            reasons.append("QPU evidence requires measured/recorded execution cost")

    elif record.evidence_type == ExternalEvidenceType.QUANTUM_SENSOR:
        if not record.backend_or_device or not record.calibration_id:
            reasons.append("sensor evidence requires named device and calibration ID")
        if not record.truth_reference_id:
            reasons.append("sensor evidence requires a truth-reference ID")
        if record.uncertainty is None or record.uncertainty < 0:
            reasons.append("sensor evidence requires non-negative uncertainty")

    elif record.evidence_type == ExternalEvidenceType.MATERIALS_HAMILTONIAN:
        if not _is_sha256(record.classical_baseline_digest):
            reasons.append("materials Hamiltonian evidence requires classical-reference digest")
        for key in ("structure_digest", "hamiltonian_digest", "basis", "active_space"):
            if not record.metadata.get(key):
                reasons.append(f"materials Hamiltonian evidence requires metadata.{key}")

    elif record.evidence_type == ExternalEvidenceType.CALIBRATED_PHYSICS_MODEL:
        if not record.truth_reference_id:
            reasons.append("calibrated physics model requires truth/reference dataset ID")
        if record.uncertainty is None or record.uncertainty < 0:
            reasons.append("calibrated physics model requires validation uncertainty/error")
        if not _is_sha256(record.classical_baseline_digest):
            reasons.append("calibrated physics model requires authoritative baseline digest")

    elif record.evidence_type == ExternalEvidenceType.MISSION_OPTIMIZATION:
        if not _is_sha256(record.classical_baseline_digest):
            reasons.append("mission optimization requires classical baseline result digest")
        for key in ("instance_family_digest", "objective_definition", "constraint_definition"):
            if not record.metadata.get(key):
                reasons.append(f"mission optimization requires metadata.{key}")
        if record.latency_seconds is None or record.latency_seconds < 0:
            reasons.append("mission optimization requires end-to-end latency")
        if record.cost_usd is None or record.cost_usd < 0:
            reasons.append("mission optimization requires end-to-end compute cost")

    elif record.evidence_type == ExternalEvidenceType.PHYSICAL_METROLOGY:
        if not record.calibration_id or not record.truth_reference_id:
            reasons.append("physical metrology requires calibration and truth/null reference IDs")
        if record.uncertainty is None or record.uncertainty < 0:
            reasons.append("physical metrology requires uncertainty budget")
        if record.metadata.get("null_controls_completed") != "true":
            reasons.append("physical metrology requires completed null controls")

    return ExternalEvidenceDecision(
        accepted_for_intake=not reasons,
        evidence_type=record.evidence_type.value,
        reasons=tuple(reasons),
        claim_control=(
            "Acceptance means the evidence package is structurally complete enough for SARA intake; "
            "it does not by itself satisfy the 97 mission-readiness threshold or validate the underlying claim."
        ),
    )
