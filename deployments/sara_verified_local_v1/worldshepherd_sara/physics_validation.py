from __future__ import annotations

from enum import Enum
from math import isfinite
from typing import Any

from pydantic import BaseModel, Field, model_validator

C_M_PER_S = 299_792_458.0
PHYSICS_SCHEMA_VERSION = "ws-physics-record-1"


class PhysicsLayer(str, Enum):
    P0_STANDARD_MODEL = "P0_STANDARD_MODEL"
    P1_GENERAL_RELATIVITY = "P1_GENERAL_RELATIVITY"
    P2_ESTABLISHED_ENGINEERING = "P2_ESTABLISHED_ENGINEERING"
    P3_EFFECTIVE_OR_FRONTIER = "P3_EFFECTIVE_OR_FRONTIER"
    P4_BEYOND_STANDARD_MODEL = "P4_BEYOND_STANDARD_MODEL"


class ValidationState(str, Enum):
    CONCEPT = "concept"
    LITERATURE_SUPPORTED = "literature_supported"
    SIMULATED = "simulated"
    INTERNAL_TEST = "internal_test"
    INDEPENDENTLY_REPLICATED = "independently_replicated"
    QUALIFIED = "qualified"
    CERTIFIED = "certified"


class IndependentReviewState(str, Enum):
    NONE = "none"
    REQUESTED = "requested"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ApprovalState(str, Enum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ConvergenceStatus(str, Enum):
    NOT_RUN = "not_run"
    FAILED = "failed"
    PARTIAL = "partial"
    PASSED = "passed"


class ReplicationState(str, Enum):
    R0_REPEAT = "R0_REPEAT"
    R1_INTERNAL = "R1_INTERNAL"
    R2_INSTRUMENT = "R2_INSTRUMENT"
    R3_INDEPENDENT = "R3_INDEPENDENT"


class ConfounderStatus(str, Enum):
    NOT_TESTED = "NOT_TESTED"
    TESTED_PASS = "TESTED_PASS"
    TESTED_FAIL = "TESTED_FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class GoverningEquation(BaseModel):
    expression: str = Field(min_length=1)
    name: str = Field(min_length=1)
    domain_of_validity: str = Field(min_length=1)
    source_id: str | None = None


class PhysicsParameter(BaseModel):
    name: str = Field(min_length=1)
    value: float | int | str | None = None
    unit: str = Field(min_length=1)
    source_type: str = Field(pattern=r"^(measured|literature|estimated|fitted|assumed)$")
    source_id: str | None = None
    uncertainty: str | None = None


class SimulationRecord(BaseModel):
    solver: str = Field(min_length=1)
    version: str = Field(min_length=1)
    mesh_or_resolution: str = Field(min_length=1)
    convergence_status: ConvergenceStatus
    input_digest: str = Field(pattern=r"^sha256:[0-9a-fA-F]{64}$")
    output_digest: str = Field(pattern=r"^sha256:[0-9a-fA-F]{64}$")
    verification_notes: list[str] = Field(default_factory=list)


class ExperimentRecord(BaseModel):
    setup_id: str = Field(min_length=1)
    calibration_record_ids: list[str] = Field(default_factory=list)
    raw_data_digests: list[str] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
    operator: str = Field(min_length=1)
    measurement_equipment_used: bool = True
    preregistered_prediction_ids: list[str] = Field(default_factory=list)
    confounders: dict[str, ConfounderStatus] = Field(default_factory=dict)
    replication_state: ReplicationState = ReplicationState.R0_REPEAT

    @model_validator(mode="after")
    def validate_evidence_chain(self) -> "ExperimentRecord":
        for digest in self.raw_data_digests:
            if not digest.startswith("sha256:") or len(digest) != 71:
                raise ValueError("raw_data_digests must contain sha256:<64 hex> values")
        if self.measurement_equipment_used and not self.calibration_record_ids:
            raise ValueError("measurement equipment requires at least one calibration record")
        return self


class EvidenceScore(BaseModel):
    repeatability: float = Field(ge=0, le=100)
    control_quality: float = Field(ge=0, le=100)
    signal_quality: float = Field(ge=0, le=100)
    background_characterization: float = Field(ge=0, le=100)
    instrument_independence: float = Field(ge=0, le=100)
    model_consistency: float = Field(ge=0, le=100)
    falsification_strength: float = Field(ge=0, le=100)

    def weighted_score(self) -> float:
        score = (
            0.20 * self.repeatability
            + 0.20 * self.control_quality
            + 0.15 * self.signal_quality
            + 0.10 * self.background_characterization
            + 0.15 * self.instrument_independence
            + 0.10 * self.model_consistency
            + 0.10 * self.falsification_strength
        )
        return round(score, 2)


class PhysicsVerificationRecord(BaseModel):
    schema_version: str = Field(default=PHYSICS_SCHEMA_VERSION, pattern=r"^ws-physics-record-1$")
    record_id: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    physics_domain: list[str] = Field(min_length=1)
    physics_layer: PhysicsLayer = PhysicsLayer.P2_ESTABLISHED_ENGINEERING
    model_scope: str = Field(min_length=1)
    reference_frame: str | None = None
    governing_equations: list[GoverningEquation] = Field(default_factory=list)
    conservation_constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(min_length=1)
    boundary_conditions: list[str] = Field(default_factory=list)
    initial_conditions: list[str] = Field(default_factory=list)
    parameters: list[PhysicsParameter] = Field(default_factory=list)
    unit_system: str = Field(default="SI", min_length=1)
    uncertainty_method: str | None = None
    sensitivity_method: str | None = None
    simulation: SimulationRecord | None = None
    experiment: ExperimentRecord | None = None
    failure_modes: list[str] = Field(default_factory=list)
    hazard_controls: list[str] = Field(default_factory=list)
    validation_state: ValidationState = ValidationState.CONCEPT
    independent_review_state: IndependentReviewState = IndependentReviewState.NONE
    independent_evidence_refs: list[str] = Field(default_factory=list)
    claim_label: str = Field(default="Hypothesis", min_length=1)
    claim_class: int = Field(default=0, ge=0, le=9)
    external_safe_statement: str = Field(min_length=1)
    cre1aws_approval_state: ApprovalState = ApprovalState.NOT_REQUESTED
    evidence_package_refs: list[str] = Field(default_factory=list)
    audit_event_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_maturity_gates(self) -> "PhysicsVerificationRecord":
        simulation_states = {
            ValidationState.SIMULATED,
            ValidationState.INTERNAL_TEST,
            ValidationState.INDEPENDENTLY_REPLICATED,
            ValidationState.QUALIFIED,
            ValidationState.CERTIFIED,
        }
        physical_states = {
            ValidationState.INTERNAL_TEST,
            ValidationState.INDEPENDENTLY_REPLICATED,
            ValidationState.QUALIFIED,
            ValidationState.CERTIFIED,
        }
        independent_states = {
            ValidationState.INDEPENDENTLY_REPLICATED,
            ValidationState.QUALIFIED,
            ValidationState.CERTIFIED,
        }

        if self.validation_state in simulation_states:
            if not self.governing_equations:
                raise ValueError("simulation-or-higher state requires governing equations")
            if not self.boundary_conditions:
                raise ValueError("simulation-or-higher state requires boundary conditions")
            if self.simulation is None:
                raise ValueError("simulation-or-higher state requires simulation metadata")
            if not (self.uncertainty_method or self.sensitivity_method):
                raise ValueError("simulation-or-higher state requires uncertainty or sensitivity method")

        if self.validation_state in physical_states:
            if self.experiment is None:
                raise ValueError("physical-test-or-higher state requires experiment metadata")
            if not self.experiment.raw_data_digests:
                raise ValueError("physical-test-or-higher state requires raw-data digests")
            if not self.failure_modes:
                raise ValueError("physical-test-or-higher state requires failure/off-nominal review")

        if self.validation_state in independent_states:
            if self.independent_review_state != IndependentReviewState.COMPLETED:
                raise ValueError("independent-validation state requires completed independent review")
            if not self.independent_evidence_refs:
                raise ValueError("independent-validation state requires independent evidence reference")
            if self.cre1aws_approval_state != ApprovalState.APPROVED:
                raise ValueError("independent-validation state requires CRE1AWS approval")

        if self.physics_layer == PhysicsLayer.P4_BEYOND_STANDARD_MODEL:
            if "energy" not in {item.lower() for item in self.conservation_constraints}:
                raise ValueError("P4 record must explicitly account for energy conservation")
            if "momentum" not in {item.lower() for item in self.conservation_constraints}:
                raise ValueError("P4 record must explicitly account for momentum conservation")

        if self.claim_class > 3:
            if self.cre1aws_approval_state != ApprovalState.APPROVED:
                raise ValueError("claims above C3 require CRE1AWS approval")
            if not self.evidence_package_refs or not self.audit_event_ids:
                raise ValueError("claims above C3 require evidence package and audit event")

        return self


def photon_force(power_w: float) -> float:
    """Ideal one-way photon thrust in newtons for radiated power in watts."""
    if not isfinite(power_w) or power_w < 0:
        raise ValueError("power_w must be a finite non-negative value")
    return power_w / C_M_PER_S


def photon_ratio(force_n: float, power_w: float) -> float:
    """Measured-force to ideal photon-force ratio Fc/P."""
    if not isfinite(force_n):
        raise ValueError("force_n must be finite")
    if not isfinite(power_w) or power_w <= 0:
        raise ValueError("power_w must be a finite positive value")
    return force_n * C_M_PER_S / power_w


def evidence_classification(score: EvidenceScore) -> str:
    value = score.weighted_score()
    if value < 30:
        return "INSUFFICIENT"
    if value < 50:
        return "EXPLORATORY"
    if value < 65:
        return "INTERESTING"
    if value < 80:
        return "ANOMALY_CANDIDATE"
    if value < 90:
        return "STRONG_ANOMALY"
    if value < 97:
        return "REPLICATION_PRIORITY"
    return "INDEPENDENT_VALIDATION_REQUIRED"


def apply_hard_gates(
    *,
    record: PhysicsVerificationRecord,
    score: EvidenceScore,
) -> dict[str, Any]:
    """Return conservative claim/evidence status. High score never establishes new physics."""
    raw_classification = evidence_classification(score)
    blocks: list[str] = []

    if record.experiment is None:
        blocks.append("NO_PHYSICAL_EXPERIMENT")
    else:
        relevant = {
            name: state
            for name, state in record.experiment.confounders.items()
            if state != ConfounderStatus.NOT_APPLICABLE
        }
        if any(state == ConfounderStatus.NOT_TESTED for state in relevant.values()):
            blocks.append("UNTESTED_CONFOUNDERS")
        if record.experiment.replication_state != ReplicationState.R3_INDEPENDENT:
            blocks.append("NO_INDEPENDENT_REPLICATION")

    if record.physics_layer == PhysicsLayer.P4_BEYOND_STANDARD_MODEL:
        if record.validation_state != ValidationState.INDEPENDENTLY_REPLICATED:
            blocks.append("BSM_NOT_INDEPENDENTLY_REPLICATED")

    external_claim_allowed = not blocks and record.cre1aws_approval_state == ApprovalState.APPROVED
    return {
        "weighted_score": score.weighted_score(),
        "raw_classification": raw_classification,
        "hard_gate_blocks": blocks,
        "external_claim_allowed": external_claim_allowed,
        "new_physics_confirmed": False,
        "status_note": (
            "Independent replication and governance gates satisfied for bounded external wording; "
            "this result does not establish new physics."
            if external_claim_allowed
            else "Evidence remains bounded by unresolved validation or governance gates."
        ),
    }
