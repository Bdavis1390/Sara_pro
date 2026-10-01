"""Latent-manifold contracts for UC06-P1 diagnostic and future operational use.

D4 supports a low-dimensional diagnostic representation, but the repository does not
currently contain a qualified projection basis or a preregistered physical anomaly
threshold.  This module therefore refuses post-hoc anomaly classification.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
LATENT_CONTRACT_VERSION = "worldshepherd.uc06-p1.latent.v0.1"


class LatentAssessmentState(str, Enum):
    NOT_EVALUABLE = "NOT_EVALUABLE"
    WITHIN_VALIDATED_ENVELOPE = "WITHIN_VALIDATED_ENVELOPE"
    OUTSIDE_VALIDATED_ENVELOPE = "OUTSIDE_VALIDATED_ENVELOPE"


class LatentModelManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[LATENT_CONTRACT_VERSION] = LATENT_CONTRACT_VERSION
    model_id: str = Field(min_length=1, max_length=128)
    source_evidence: str = Field(min_length=1, max_length=512)
    component_count: int = Field(ge=1, le=16)
    explained_variance_fraction: float = Field(ge=0.0, le=1.0)
    basis_sha256: str
    centering_vector_sha256: str
    feature_definition: Literal["REAL161_PLUS_IMAG161"] = "REAL161_PLUS_IMAG161"
    coarse_ensemble_only: bool = True
    held_out_simulation_validated: bool = False
    hardware_repeatability_validated: bool = False

    @model_validator(mode="after")
    def validate_hashes(self) -> "LatentModelManifest":
        for name, value in (
            ("basis_sha256", self.basis_sha256),
            ("centering_vector_sha256", self.centering_vector_sha256),
        ):
            if not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
        return self


class LatentAnomalyPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(min_length=1, max_length=128)
    threshold_source: str = Field(min_length=1, max_length=512)
    reconstruction_error_threshold: float = Field(gt=0.0)
    threshold_preregistered_before_evaluation: bool = False
    physical_baseline_repeatability_validated: bool = False
    hardware_context_id: str | None = Field(default=None, max_length=128)
    model_context_id: str = Field(min_length=1, max_length=128)


class LatentObservationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1, max_length=128)
    model_id: str = Field(min_length=1, max_length=128)
    hardware_context_id: str | None = Field(default=None, max_length=128)
    reconstruction_error: float = Field(ge=0.0)


class LatentObservationAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: LatentAssessmentState
    evaluable: bool
    anomaly_claim_authorized: bool
    unresolved_gates: list[str]
    rationale_codes: list[str]


def assess_latent_observation(
    *,
    manifest: LatentModelManifest,
    policy: LatentAnomalyPolicy,
    observation: LatentObservationInput,
) -> LatentObservationAssessment:
    """Assess only when a preregistered physical envelope exists.

    The D4 low-dimensional result alone is insufficient to choose an anomaly
    threshold.  Missing validation gates yield NOT_EVALUABLE rather than a benign
    or anomalous label.
    """

    unresolved: list[str] = []

    if observation.model_id != manifest.model_id:
        unresolved.append("MODEL_ID_MISMATCH")
    if policy.model_context_id != manifest.model_id:
        unresolved.append("POLICY_MODEL_CONTEXT_MISMATCH")
    if manifest.coarse_ensemble_only:
        unresolved.append("COARSE_ENSEMBLE_ONLY")
    if not manifest.held_out_simulation_validated:
        unresolved.append("HELD_OUT_SIMULATION_VALIDATION")
    if not manifest.hardware_repeatability_validated:
        unresolved.append("HARDWARE_REPEATABILITY")
    if not policy.threshold_preregistered_before_evaluation:
        unresolved.append("PREREGISTERED_THRESHOLD")
    if not policy.physical_baseline_repeatability_validated:
        unresolved.append("PHYSICAL_BASELINE_REPEATABILITY")
    if not policy.hardware_context_id:
        unresolved.append("HARDWARE_CONTEXT")
    elif observation.hardware_context_id != policy.hardware_context_id:
        unresolved.append("HARDWARE_CONTEXT_MISMATCH")

    if unresolved:
        return LatentObservationAssessment(
            state=LatentAssessmentState.NOT_EVALUABLE,
            evaluable=False,
            anomaly_claim_authorized=False,
            unresolved_gates=unresolved,
            rationale_codes=["NO_POST_HOC_ANOMALY_THRESHOLD", "FAIL_CLOSED"],
        )

    outside = observation.reconstruction_error > policy.reconstruction_error_threshold
    return LatentObservationAssessment(
        state=(
            LatentAssessmentState.OUTSIDE_VALIDATED_ENVELOPE
            if outside
            else LatentAssessmentState.WITHIN_VALIDATED_ENVELOPE
        ),
        evaluable=True,
        anomaly_claim_authorized=True,
        unresolved_gates=[],
        rationale_codes=["PREREGISTERED_VALIDATED_ENVELOPE_APPLIED"],
    )


def current_d4_latent_contract() -> dict[str, object]:
    """Describe the current D4 result without pretending a basis is operational."""

    return {
        "contract_version": LATENT_CONTRACT_VERSION,
        "source": "D4_A001_A018_COARSE_COMPLETE_FACTORIAL",
        "diagnostic_component_count_95pct": 2,
        "diagnostic_component_count_99pct": 3,
        "first_two_variance_fraction": 0.974061386803,
        "first_three_variance_fraction": 0.994613458837,
        "qualified_projection_basis_available": False,
        "held_out_validation_available": False,
        "hardware_repeatability_available": False,
        "anomaly_threshold_available": False,
        "anomaly_classification_authorized": False,
        "claims_boundary": [
            "COARSE_ENSEMBLE_DIAGNOSTIC_ONLY",
            "NO_INTRINSIC_DIMENSION_CLAIM",
            "NO_POST_HOC_ANOMALY_THRESHOLD",
            "NO_HARDWARE_ANOMALY_CLAIM",
        ],
    }
