"""Evidence-bound staging for electromagnetic design candidates.

This module separates simulation-validation eligibility from hardware authorization.
A candidate may be admitted to Palace validation while remaining categorically
ineligible for hardware action.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .em_intelligence import EMCandidate, EMIntent, UC06EvidenceSummary, current_uc06_evidence


class EMValidationStage(str, Enum):
    REJECTED = "REJECTED"
    PALACE_VALIDATION_CANDIDATE = "PALACE_VALIDATION_CANDIDATE"


class EMValidationAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str = Field(min_length=1, max_length=128)
    candidate_id: str = Field(min_length=1, max_length=128)
    stage: EMValidationStage
    may_enter_palace_validation: bool
    hardware_action_authorized: bool = False
    blockers: list[str] = Field(default_factory=list, max_length=64)
    advisories: list[str] = Field(default_factory=list, max_length=64)
    candidate_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def canonical_model_digest(model: BaseModel) -> str:
    payload = model.model_dump(mode="json")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def assess_candidate_for_palace(
    intent: EMIntent,
    candidate: EMCandidate,
    evidence: UC06EvidenceSummary | None = None,
) -> EMValidationAssessment:
    """Determine whether a proposal may proceed to full-wave simulation validation.

    This function never authorizes hardware.  It only admits or rejects a design
    candidate for Palace validation under the current evidence boundary.
    """

    evidence = evidence or current_uc06_evidence()
    blockers: list[str] = []
    advisories: list[str] = []

    if candidate.hardware_action_authorized:
        blockers.append("HARDWARE_ACTION_FLAG_MUST_BE_FALSE_AT_SIMULATION_STAGE")

    if not candidate.evidence_refs:
        blockers.append("CANDIDATE_EVIDENCE_REFS_REQUIRED")

    normalized_convergence = candidate.convergence_status.strip().upper()
    if normalized_convergence in {"FAILED", "REJECTED", "INVALID"}:
        blockers.append("CANDIDATE_CONVERGENCE_STATUS_REJECTS_VALIDATION")

    normalized_discrepancy = candidate.model_discrepancy_status.strip().upper()
    if normalized_discrepancy in {"UNBOUNDED", "INVALID", "REJECTED"}:
        blockers.append("MODEL_DISCREPANCY_STATUS_REJECTS_VALIDATION")

    if evidence.overall_convergence != "NOT_ADJUDICATED":
        advisories.append(f"UC06_OVERALL_CONVERGENCE={evidence.overall_convergence}")
    else:
        advisories.append("UC06_OVERALL_CONVERGENCE_NOT_ADJUDICATED")

    if not evidence.full_campaign_authorized:
        advisories.append("FULL_CAMPAIGN_NOT_AUTHORIZED")

    if not evidence.h2_promotion_authorized:
        advisories.append("H2_NOT_PROMOTED")

    allowed = not blockers
    stage = (
        EMValidationStage.PALACE_VALIDATION_CANDIDATE
        if allowed
        else EMValidationStage.REJECTED
    )

    return EMValidationAssessment(
        intent_id=intent.intent_id,
        candidate_id=candidate.candidate_id,
        stage=stage,
        may_enter_palace_validation=allowed,
        hardware_action_authorized=False,
        blockers=sorted(set(blockers)),
        advisories=sorted(set(advisories)),
        candidate_digest=canonical_model_digest(candidate),
        evidence_digest=canonical_model_digest(evidence),
    )
