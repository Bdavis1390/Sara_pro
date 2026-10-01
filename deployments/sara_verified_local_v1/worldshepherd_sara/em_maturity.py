"""Read-only UC06-P1 R&D maturity state for SARA/OVERWATCH.

This module centralizes scientific status so downstream code does not infer maturity
from individual metrics, CI results, or the existence of software artifacts.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict


MATURITY_SCHEMA_VERSION = "worldshepherd.uc06-p1.maturity.v0.1"


class EvidenceState(str, Enum):
    ESTABLISHED_DIAGNOSTIC = "ESTABLISHED_DIAGNOSTIC"
    PENDING = "PENDING"
    NOT_INGESTED = "NOT_INGESTED"
    NOT_ADJUDICATED = "NOT_ADJUDICATED"
    NOT_VALIDATED = "NOT_VALIDATED"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"


class UC06MaturityState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[MATURITY_SCHEMA_VERSION] = MATURITY_SCHEMA_VERSION
    evidence_scope: Literal["UC06-P1"] = "UC06-P1"
    d4_capability_attribution: Literal[EvidenceState.ESTABLISHED_DIAGNOSTIC] = (
        EvidenceState.ESTABLISHED_DIAGNOSTIC
    )
    d5_interaction_sparse_analysis: Literal[EvidenceState.PENDING] = EvidenceState.PENDING
    recovery_a027_a054_completion: Literal[EvidenceState.NOT_INGESTED] = EvidenceState.NOT_INGESTED
    medium_fine_convergence: Literal[EvidenceState.NOT_ADJUDICATED] = EvidenceState.NOT_ADJUDICATED
    energy_closure: Literal[EvidenceState.PENDING] = EvidenceState.PENDING
    physical_validation: Literal[EvidenceState.NOT_VALIDATED] = EvidenceState.NOT_VALIDATED
    repeatability_validation: Literal[EvidenceState.NOT_VALIDATED] = EvidenceState.NOT_VALIDATED
    validated_operating_envelope: Literal[EvidenceState.NOT_VALIDATED] = EvidenceState.NOT_VALIDATED
    h2_promotion: Literal[EvidenceState.NOT_AUTHORIZED] = EvidenceState.NOT_AUTHORIZED
    full_campaign: Literal[EvidenceState.NOT_AUTHORIZED] = EvidenceState.NOT_AUTHORIZED
    hardware_action: Literal[EvidenceState.NOT_AUTHORIZED] = EvidenceState.NOT_AUTHORIZED
    software_ci_is_physics_validation: Literal[False] = False
    read_only: Literal[True] = True
    next_required_evidence: list[str]
    claims_boundary: list[str]


def current_uc06_maturity() -> UC06MaturityState:
    """Return the conservative evidence state known to repository code.

    The recovery-completion field is NOT_INGESTED rather than failed: repository
    code has not received a sealed completion receipt for A027-A054.  Likewise,
    medium-to-fine convergence is NOT_ADJUDICATED, not failed.
    """

    return UC06MaturityState(
        next_required_evidence=[
            "SEALED_D5_RESULT_RECEIPT",
            "SEALED_A027_A054_RECOVERY_COMPLETION_RECEIPT",
            "FROZEN_MEDIUM_FINE_CONVERGENCE_ADJUDICATION",
            "FROZEN_ENERGY_CLOSURE_ADJUDICATION",
            "PHYSICAL_VNA_COUPON_VALIDATION",
            "REPEATABILITY_AND_UNCERTAINTY_VALIDATION",
            "VALIDATED_OPERATING_ENVELOPE",
            "EXPLICIT_PRIME_RELEASE_BEFORE_ANY_HARDWARE_ACTION",
        ],
        claims_boundary=[
            "D4_IS_DIAGNOSTIC_NOT_PHYSICAL_VALIDATION",
            "D5_PENDING_NO_RESULT_VALUES",
            "RECOVERY_COMPLETION_NOT_INGESTED_NOT_FAILED",
            "CONVERGENCE_NOT_ADJUDICATED_NOT_FAILED",
            "SOFTWARE_CI_IS_NOT_PHYSICS_VALIDATION",
            "NO_H2_PROMOTION",
            "NO_FULL_CAMPAIGN_AUTHORIZATION",
            "NO_HARDWARE_ACTION",
        ],
    )


router = APIRouter(prefix="/v1/em/uc06", tags=["em-maturity"])


@router.get("/maturity", response_model=UC06MaturityState)
def uc06_maturity() -> UC06MaturityState:
    """Return the read-only UC06-P1 evidence maturity state."""

    return current_uc06_maturity()
