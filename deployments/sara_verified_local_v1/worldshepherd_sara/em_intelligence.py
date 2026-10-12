"""Governed electromagnetic-intelligence models and read-only UC06 evidence API.

This module is intentionally non-actuating.  It exposes typed contracts for future
SARA/PRIME/ECHO/OVERWATCH integration and a bounded, read-only summary of the
currently retained UC06-P1 diagnostic evidence.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field


EM_SCHEMA_VERSION = "worldshepherd.em-intelligence.v0.1"
UC06_EVIDENCE_VERSION = "uc06-p1-d4-20260930"


class EMOperatingMode(str, Enum):
    AUDIT_CALIBRATION = "AUDIT_CALIBRATION"
    OPERATIONAL_SPARSE_TONE = "OPERATIONAL_SPARSE_TONE"
    SAFE_DEGRADED = "SAFE_DEGRADED"
    DESIGN_EXPLORATION = "DESIGN_EXPLORATION"


class EMEvidenceClass(str, Enum):
    PROVEN_INTERNALLY = "PROVEN_INTERNALLY"
    IMPLEMENTED_IN_SOFTWARE = "IMPLEMENTED_IN_SOFTWARE"
    SUPPORTED_BY_LITERATURE = "SUPPORTED_BY_LITERATURE"
    SIMULATED_ONLY = "SIMULATED_ONLY"
    HYPOTHESIS = "HYPOTHESIS"
    SPECULATIVE_EXTENSION = "SPECULATIVE_EXTENSION"
    REQUIRES_LAB_VALIDATION = "REQUIRES_LAB_VALIDATION"
    REQUIRES_PARTNER_VALIDATION = "REQUIRES_PARTNER_VALIDATION"
    REQUIRES_LEGAL_REVIEW = "REQUIRES_LEGAL_REVIEW"
    NOT_CURRENTLY_CLAIMED = "NOT_CURRENTLY_CLAIMED"


class EMIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[EM_SCHEMA_VERSION] = EM_SCHEMA_VERSION
    intent_id: str = Field(min_length=1, max_length=128)
    objective: str = Field(min_length=1, max_length=512)
    operating_mode: EMOperatingMode
    frequency_GHz: list[float] = Field(default_factory=list, max_length=161)
    polarization: Literal["TE", "TM", "BOTH"] = "BOTH"
    angle_deg: float | None = Field(default=None, ge=0.0, le=90.0)
    desired_state: str | None = Field(default=None, max_length=64)
    latency_budget_ms: float | None = Field(default=None, gt=0.0)
    power_budget_W: float | None = Field(default=None, gt=0.0)
    evidence_refs: list[str] = Field(default_factory=list, max_length=64)


class EMCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[EM_SCHEMA_VERSION] = EM_SCHEMA_VERSION
    candidate_id: str = Field(min_length=1, max_length=128)
    source_model: str = Field(min_length=1, max_length=128)
    source_version: str = Field(min_length=1, max_length=128)
    proposed_state: str | None = Field(default=None, max_length=64)
    predicted_te_latent: list[float] = Field(default_factory=list, max_length=16)
    predicted_tm_latent: list[float] = Field(default_factory=list, max_length=16)
    evidence_class: EMEvidenceClass
    convergence_status: str = Field(min_length=1, max_length=128)
    model_discrepancy_status: str = Field(min_length=1, max_length=128)
    evidence_refs: list[str] = Field(default_factory=list, max_length=64)
    hardware_action_authorized: bool = False


class EMPolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[EM_SCHEMA_VERSION] = EM_SCHEMA_VERSION
    decision_id: str = Field(min_length=1, max_length=128)
    intent_id: str = Field(min_length=1, max_length=128)
    candidate_id: str = Field(min_length=1, max_length=128)
    authorized: bool
    validated_envelope_id: str | None = Field(default=None, max_length=128)
    safe_fallback: str = Field(default="SAFE_OPEN", min_length=1, max_length=64)
    unresolved_gates: list[str] = Field(default_factory=list, max_length=64)
    rationale_codes: list[str] = Field(default_factory=list, max_length=64)


class EMObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[EM_SCHEMA_VERSION] = EM_SCHEMA_VERSION
    observation_id: str = Field(min_length=1, max_length=128)
    observed_utc: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=128)
    commanded_state: str | None = Field(default=None, max_length=64)
    frequency_GHz: list[float] = Field(default_factory=list, max_length=161)
    te_real: list[float] = Field(default_factory=list, max_length=161)
    te_imag: list[float] = Field(default_factory=list, max_length=161)
    tm_real: list[float] = Field(default_factory=list, max_length=161)
    tm_imag: list[float] = Field(default_factory=list, max_length=161)
    latent_coordinates: list[float] = Field(default_factory=list, max_length=16)
    angle_estimate_deg: float | None = Field(default=None, ge=0.0, le=90.0)
    polarization_estimate: str | None = Field(default=None, max_length=32)
    provenance_hashes: dict[str, str] = Field(default_factory=dict)


class UC06EvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_version: Literal[UC06_EVIDENCE_VERSION] = UC06_EVIDENCE_VERSION
    evidence_class: EMEvidenceClass = EMEvidenceClass.SIMULATED_ONLY
    source_prefix: Literal["A001-A026"] = "A001-A026"
    pca_source: Literal["A001-A018_COARSE_COMPLETE_FACTORIAL"] = (
        "A001-A018_COARSE_COMPLETE_FACTORIAL"
    )
    active_recovery_touched: Literal[False] = False
    scientific_gate_change: Literal[False] = False
    overall_convergence: Literal["NOT_ADJUDICATED"] = "NOT_ADJUDICATED"
    h2_promotion_authorized: Literal[False] = False
    full_campaign_authorized: Literal[False] = False
    first_two_pc_variance_fraction: float = Field(ge=0.0, le=1.0)
    first_three_pc_variance_fraction: float = Field(ge=0.0, le=1.0)
    strongest_angle_discriminability: float = Field(ge=0.0)
    strongest_angle_case: str
    strongest_modeled_median_polarization_isolation_dB: float = Field(ge=0.0)
    largest_tm_programmable_phase_span_deg: float = Field(ge=0.0, le=180.0)
    largest_tm_over_te_rms_refinement_ratio: float = Field(ge=0.0)
    strongest_tm_state_separation_rms: float = Field(ge=0.0)
    strongest_tm_state_case: str
    claims_boundary: list[str]
    evidence_refs: list[str]


def current_uc06_evidence() -> UC06EvidenceSummary:
    """Return the frozen read-only D4 diagnostic summary.

    These values summarize retained diagnostic evidence.  They do not adjudicate
    medium-to-fine convergence or authorize physical operation.
    """

    return UC06EvidenceSummary(
        first_two_pc_variance_fraction=0.974061386803,
        first_three_pc_variance_fraction=0.994613458837,
        strongest_angle_discriminability=230.238908861,
        strongest_angle_case="LOW_C_TE_0deg_vs_60deg",
        strongest_modeled_median_polarization_isolation_dB=70.0177658995,
        largest_tm_programmable_phase_span_deg=83.9532267062,
        largest_tm_over_te_rms_refinement_ratio=45.5858763919,
        strongest_tm_state_separation_rms=1.06046768125,
        strongest_tm_state_case="COARSE_TM_60deg_HIGH_C_vs_SAFE_OPEN",
        claims_boundary=[
            "DIAGNOSTIC_PREFIX_ONLY",
            "MEDIUM_FINE_GATE_PENDING",
            "ENERGY_CLOSURE_PENDING",
            "NO_HARDWARE_VALIDATION",
            "NO_H2_PROMOTION",
            "NO_FULL_CAMPAIGN_AUTHORIZATION",
            "NO_AUTOMATIC_HARDWARE_ACTION",
        ],
        evidence_refs=[
            "local:r2r-b0-d2-prefix-parser-20260929T201714Z",
            "local:r2r-b0-d3-capability-metrics-20260929T235751Z",
            "local:r2r-b0-d4-capability-attribution-20260930T001230Z",
            "github:research/uc06_p1/D4_SUMMARY.md",
            "github:research/uc06_p1/EVIDENCE_INDEX.md",
        ],
    )


router = APIRouter(prefix="/v1/em", tags=["em-intelligence"])


@router.get("/uc06/evidence", response_model=UC06EvidenceSummary)
def uc06_evidence() -> UC06EvidenceSummary:
    """Read-only UC06-P1 diagnostic evidence summary."""

    return current_uc06_evidence()


@router.get("/contract")
def em_contract() -> dict[str, object]:
    """Describe the non-actuating EM intelligence contract."""

    return {
        "schema_version": EM_SCHEMA_VERSION,
        "read_only": True,
        "hardware_actions": False,
        "candidate_models": [
            "EMIntent",
            "EMCandidate",
            "EMPolicyDecision",
            "EMObservation",
        ],
        "claims_boundary": [
            "SURROGATES_MAY_PROPOSE_NOT_VALIDATE",
            "PALACE_FULL_WAVE_REMAINS_FORWARD_VALIDATOR",
            "PRIME_REQUIRED_BEFORE_FUTURE_HARDWARE_ACTION",
            "UNKNOWN_OR_OUT_OF_MANIFOLD_FAILS_TO_SAFE_MODE",
        ],
    }
