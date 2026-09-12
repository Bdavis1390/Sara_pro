from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .qualification import (
    CapabilityStatus,
    ResultStatus,
    ReviewStatus,
    canonical_digest,
)


class ImprovementTriggerKind(str, Enum):
    NEW_EVIDENCE = "NEW_EVIDENCE"
    TEST_RESULT = "TEST_RESULT"
    FAILURE = "FAILURE"
    ANOMALY = "ANOMALY"
    CONTRADICTION = "CONTRADICTION"
    REQUIREMENT_DELTA = "REQUIREMENT_DELTA"
    PARTNER_FEEDBACK = "PARTNER_FEEDBACK"
    RESEARCH = "RESEARCH"
    SECURITY_EVENT = "SECURITY_EVENT"
    OPPORTUNITY = "OPPORTUNITY"
    OPERATOR_FEEDBACK = "OPERATOR_FEEDBACK"


class ImprovementRisk(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ImprovementState(str, Enum):
    PROPOSED = "PROPOSED"
    VALIDATING = "VALIDATING"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"
    SUPERSEDED = "SUPERSEDED"


class ImprovementReview(BaseModel):
    status: ReviewStatus = ReviewStatus.UNREVIEWED
    reviewer: str | None = None
    reviewed_utc: str | None = None
    rationale: str | None = None
    qualification_refs: list[str] = Field(default_factory=list)
    authorization_ref: str | None = None


class ImprovementProposal(BaseModel):
    """Governed proposal to improve Worldshepherd itself or one of its lanes.

    The record is intentionally a proposal/evidence object, not an execution
    primitive. Claim promotion and consequential external execution remain
    outside this module and behind existing human/PRIME authorization.
    """

    schema: str = "ws-recursive-improvement-1"
    improvement_id: str = Field(pattern=r"^WS-IR-[0-9]{4}-[0-9]{4,}$")
    trigger_kind: ImprovementTriggerKind
    title: str = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)
    affected_lanes: list[str] = Field(min_length=1)
    baseline_artifacts: list[str] = Field(default_factory=list)
    baseline_capability_status: list[CapabilityStatus] = Field(default_factory=list)
    target_capability_status: CapabilityStatus | None = None
    proposed_change: str = Field(min_length=1)
    expected_benefit: str = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    risk_level: ImprovementRisk = ImprovementRisk.MODERATE
    required_tests: list[str] = Field(min_length=1)
    success_metrics: list[str] = Field(min_length=1)
    negative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    reversible: bool = True
    generated_by: str = Field(min_length=1)
    created_utc: str = Field(min_length=1)
    state: ImprovementState = ImprovementState.PROPOSED
    review: ImprovementReview = Field(default_factory=ImprovementReview)
    requested_claim_promotion: bool = False
    requested_external_execution: bool = False

    @model_validator(mode="after")
    def enforce_fail_closed_boundaries(self) -> "ImprovementProposal":
        if self.requested_claim_promotion:
            raise ValueError(
                "recursive improvement may not self-authorize claim promotion"
            )
        if self.requested_external_execution:
            raise ValueError(
                "recursive improvement may not self-authorize external execution"
            )
        if self.state == ImprovementState.PROMOTED:
            if self.review.status != ReviewStatus.ACCEPTED:
                raise ValueError("PROMOTED state requires accepted human review")
            if not self.review.reviewer:
                raise ValueError("PROMOTED state requires an identified reviewer")
            if not self.review.qualification_refs:
                raise ValueError("PROMOTED state requires qualification evidence")
            if not self.review.authorization_ref:
                raise ValueError("PROMOTED state requires authorization reference")
        return self


class ImprovementAssessment(BaseModel):
    schema: str = "ws-recursive-improvement-assessment-1"
    improvement_id: str
    disposition: ImprovementState
    passed_tests: list[str] = Field(default_factory=list)
    failed_tests: list[str] = Field(default_factory=list)
    inconclusive_tests: list[str] = Field(default_factory=list)
    missing_tests: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    claim_promotion_performed: bool = False
    external_execution_performed: bool = False
    assessment_digest: str = ""


def proposal_digest(proposal: ImprovementProposal) -> str:
    return canonical_digest(proposal.model_dump(mode="json"))


def assess_improvement(
    proposal: ImprovementProposal,
    test_results: dict[str, ResultStatus],
) -> ImprovementAssessment:
    """Evaluate validation completeness without performing the improvement.

    Any required test failure quarantines the proposal. Missing or
    inconclusive tests keep it in validation. Only complete PASS coverage can
    advance the record to human review; this function never promotes it.
    """

    required = list(dict.fromkeys(proposal.required_tests))
    passed: list[str] = []
    failed: list[str] = []
    inconclusive: list[str] = []
    missing: list[str] = []

    for test_id in required:
        result = test_results.get(test_id)
        if result is None:
            missing.append(test_id)
        elif result == ResultStatus.PASS:
            passed.append(test_id)
        elif result == ResultStatus.FAIL:
            failed.append(test_id)
        else:
            inconclusive.append(test_id)

    reasons: list[str] = []
    if failed:
        disposition = ImprovementState.QUARANTINED
        reasons.append("one or more required validation tests failed")
    elif missing or inconclusive:
        disposition = ImprovementState.VALIDATING
        if missing:
            reasons.append("required validation tests are missing")
        if inconclusive:
            reasons.append("one or more required validation tests are inconclusive")
    else:
        disposition = ImprovementState.HUMAN_REVIEW_REQUIRED
        reasons.append(
            "all required validation tests passed; human review and authorization remain required"
        )

    payload = {
        "schema": "ws-recursive-improvement-assessment-1",
        "improvement_id": proposal.improvement_id,
        "disposition": disposition.value,
        "passed_tests": passed,
        "failed_tests": failed,
        "inconclusive_tests": inconclusive,
        "missing_tests": missing,
        "reasons": reasons,
        "claim_promotion_performed": False,
        "external_execution_performed": False,
    }
    return ImprovementAssessment(
        improvement_id=proposal.improvement_id,
        disposition=disposition,
        passed_tests=passed,
        failed_tests=failed,
        inconclusive_tests=inconclusive,
        missing_tests=missing,
        reasons=reasons,
        claim_promotion_performed=False,
        external_execution_performed=False,
        assessment_digest=canonical_digest(payload),
    )


def apply_assessment(
    proposal: ImprovementProposal,
    assessment: ImprovementAssessment,
) -> ImprovementProposal:
    if proposal.improvement_id != assessment.improvement_id:
        raise ValueError("assessment does not belong to proposal")
    if assessment.disposition not in {
        ImprovementState.VALIDATING,
        ImprovementState.HUMAN_REVIEW_REQUIRED,
        ImprovementState.QUARANTINED,
    }:
        raise ValueError("assessment disposition is not an automated validation state")
    return proposal.model_copy(update={"state": assessment.disposition})


def record_human_decision(
    proposal: ImprovementProposal,
    *,
    accepted: bool,
    reviewer: str,
    reviewed_utc: str,
    rationale: str,
    qualification_refs: list[str],
    authorization_ref: str | None = None,
) -> ImprovementProposal:
    """Record the governance decision; this does not deploy or execute change."""

    if proposal.state != ImprovementState.HUMAN_REVIEW_REQUIRED:
        raise ValueError("proposal is not ready for human review")
    if not reviewer.strip():
        raise ValueError("identified reviewer is required")
    if not rationale.strip():
        raise ValueError("review rationale is required")

    if accepted:
        if not qualification_refs:
            raise ValueError("accepted improvement requires qualification evidence")
        if not authorization_ref:
            raise ValueError("accepted improvement requires authorization reference")
        state = ImprovementState.PROMOTED
        review_status = ReviewStatus.ACCEPTED
    else:
        state = ImprovementState.REJECTED
        review_status = ReviewStatus.REJECTED

    review = ImprovementReview(
        status=review_status,
        reviewer=reviewer,
        reviewed_utc=reviewed_utc,
        rationale=rationale,
        qualification_refs=list(dict.fromkeys(qualification_refs)),
        authorization_ref=authorization_ref,
    )
    return proposal.model_copy(update={"state": state, "review": review})


def supersede_improvement(
    proposal: ImprovementProposal,
    *,
    superseded_by: str,
) -> ImprovementProposal:
    if proposal.state != ImprovementState.PROMOTED:
        raise ValueError("only a promoted improvement may be superseded")
    if not superseded_by.strip():
        raise ValueError("superseding improvement reference is required")
    negative = list(proposal.negative_evidence)
    negative.append({"superseded_by": superseded_by})
    return proposal.model_copy(
        update={
            "state": ImprovementState.SUPERSEDED,
            "negative_evidence": negative,
        }
    )
