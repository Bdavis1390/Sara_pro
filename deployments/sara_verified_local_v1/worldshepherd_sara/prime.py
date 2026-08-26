from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ActionState(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    OVERRIDDEN = "OVERRIDDEN"
    REVOKED = "REVOKED"


class ActionProposal(BaseModel):
    proposal_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    rationale: list[str] = Field(default_factory=list)
    authority_required: str = Field(min_length=1)
    state: ActionState = ActionState.PROPOSED
    reviewer: str | None = None
    decision_utc: str | None = None
    decision_reason: str | None = None

    @model_validator(mode="after")
    def decided_states_require_reviewer(self) -> "ActionProposal":
        if self.state != ActionState.PROPOSED and not self.reviewer:
            raise ValueError("decided action states require an identified reviewer")
        return self


def decide_action(
    proposal: ActionProposal,
    *,
    reviewer: str,
    state: ActionState,
    reason: str,
) -> ActionProposal:
    if proposal.state != ActionState.PROPOSED:
        raise ValueError("only PROPOSED actions may be decided")
    if state not in {ActionState.APPROVED, ActionState.DENIED, ActionState.OVERRIDDEN}:
        raise ValueError("decision must be APPROVED, DENIED, or OVERRIDDEN")
    return proposal.model_copy(
        update={
            "state": state,
            "reviewer": reviewer,
            "decision_utc": datetime.now(timezone.utc).isoformat(),
            "decision_reason": reason,
        }
    )


def revoke_action(proposal: ActionProposal, *, reviewer: str, reason: str) -> ActionProposal:
    if proposal.state not in {ActionState.APPROVED, ActionState.OVERRIDDEN}:
        raise ValueError("only approved/overridden actions may be revoked")
    return proposal.model_copy(
        update={
            "state": ActionState.REVOKED,
            "reviewer": reviewer,
            "decision_utc": datetime.now(timezone.utc).isoformat(),
            "decision_reason": reason,
        }
    )
