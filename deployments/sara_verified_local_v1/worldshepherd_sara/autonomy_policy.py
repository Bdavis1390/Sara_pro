from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ExecutionDisposition(str, Enum):
    AUTO_ELIGIBLE = "AUTO_ELIGIBLE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DENIED = "DENIED"


class AutonomousActionCandidate(BaseModel):
    action_id: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    requested_authority: int = Field(ge=0)
    reversible: bool
    payload: dict = Field(default_factory=dict)


class AutonomyPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    allowed_auto_action_types: list[str] = Field(default_factory=list)
    denied_action_types: list[str] = Field(default_factory=list)
    minimum_auto_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    maximum_auto_authority: int = Field(default=0, ge=0)
    require_reversible_for_auto: bool = True


def evaluate_candidate(
    candidate: AutonomousActionCandidate, policy: AutonomyPolicy
) -> tuple[ExecutionDisposition, list[str]]:
    reasons: list[str] = []

    if candidate.action_type in policy.denied_action_types:
        return ExecutionDisposition.DENIED, ["action type explicitly denied by policy"]

    if candidate.action_type not in policy.allowed_auto_action_types:
        reasons.append("action type is not in automatic-execution allowlist")
    if candidate.confidence < policy.minimum_auto_confidence:
        reasons.append("candidate confidence is below automatic-execution threshold")
    if candidate.requested_authority > policy.maximum_auto_authority:
        reasons.append("requested authority exceeds automatic-execution ceiling")
    if policy.require_reversible_for_auto and not candidate.reversible:
        reasons.append("automatic execution requires reversible action")

    if reasons:
        return ExecutionDisposition.HUMAN_REVIEW_REQUIRED, reasons
    return ExecutionDisposition.AUTO_ELIGIBLE, ["candidate satisfies all bounded automatic-execution policy gates"]
