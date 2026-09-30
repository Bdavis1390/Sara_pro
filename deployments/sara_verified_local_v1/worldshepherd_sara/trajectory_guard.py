from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TrajectoryDisposition(str, Enum):
    ALLOW = "ALLOW"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DENY = "DENY"
    PAUSE = "PAUSE"


class SideEffectClass(str, Enum):
    LOCAL_READ = "LOCAL_READ"
    LOCAL_WRITE = "LOCAL_WRITE"
    EXTERNAL_READ = "EXTERNAL_READ"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"
    PUBLISH = "PUBLISH"
    EXECUTE = "EXECUTE"
    CREDENTIAL_USE = "CREDENTIAL_USE"


HIGH_CONSEQUENCE_EFFECTS = {
    SideEffectClass.EXTERNAL_WRITE,
    SideEffectClass.PUBLISH,
    SideEffectClass.EXECUTE,
    SideEffectClass.CREDENTIAL_USE,
}


class TrajectoryAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1, max_length=128)
    action_type: str = Field(min_length=1, max_length=128)
    side_effect: SideEffectClass
    destination: str | None = Field(default=None, max_length=2048)
    authorization_verified: bool = False
    channel_allowlisted: bool = True
    credential_observed: bool = False
    credential_used: bool = False
    blocked_attempt: bool = False
    alternate_channel_attempt: bool = False
    policy_conflict: bool = False
    fragmented_sensitive_data: bool = False
    child_authority: int | None = Field(default=None, ge=0)
    parent_authority: int | None = Field(default=None, ge=0)


class TrajectoryDecision(BaseModel):
    disposition: TrajectoryDisposition
    reasons: list[str] = Field(default_factory=list)
    risk_delta: int = Field(ge=0)
    cumulative_risk: int = Field(ge=0)


class TrajectoryEvent(BaseModel):
    action: TrajectoryAction
    decision: TrajectoryDecision


class TrajectoryState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trajectory_id: str = Field(min_length=1, max_length=128)
    originating_human_request_hash: str = Field(min_length=1, max_length=256)
    root_authority: str = Field(min_length=1, max_length=256)
    events: list[TrajectoryEvent] = Field(default_factory=list)
    destinations_contacted: list[str] = Field(default_factory=list)
    credentials_observed: int = Field(default=0, ge=0)
    credentials_used: int = Field(default=0, ge=0)
    blocked_attempts: int = Field(default=0, ge=0)
    cumulative_risk: int = Field(default=0, ge=0)


class TrajectoryGuardPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_threshold: int = Field(default=8, ge=1)
    pause_threshold: int = Field(default=15, ge=2)
    blocked_attempt_pause_threshold: int = Field(default=3, ge=1)


def _risk_delta(action: TrajectoryAction) -> int:
    risk = 0
    if action.credential_observed:
        risk += 3
    if action.credential_used:
        risk += 8
    if action.blocked_attempt:
        risk += 2
    if action.alternate_channel_attempt:
        risk += 8
    if action.policy_conflict:
        risk += 10
    if action.fragmented_sensitive_data:
        risk += 12
    if action.side_effect in HIGH_CONSEQUENCE_EFFECTS:
        risk += 3
    if not action.channel_allowlisted:
        risk += 8
    if (
        action.child_authority is not None
        and action.parent_authority is not None
        and action.child_authority > action.parent_authority
    ):
        risk += 10
    return risk


def assess_action(
    state: TrajectoryState,
    action: TrajectoryAction,
    policy: TrajectoryGuardPolicy | None = None,
) -> tuple[TrajectoryDecision, TrajectoryState]:
    """Assess the next action against immediate controls and accumulated trajectory risk."""

    guard = policy or TrajectoryGuardPolicy()
    delta = _risk_delta(action)
    next_risk = state.cumulative_risk + delta
    next_blocked = state.blocked_attempts + int(action.blocked_attempt)
    reasons: list[str] = []
    hard_deny = False

    if action.side_effect in HIGH_CONSEQUENCE_EFFECTS and not action.authorization_verified:
        hard_deny = True
        reasons.append("high-consequence side effect lacks verified authorization")
    if not action.channel_allowlisted:
        hard_deny = True
        reasons.append("communication or destination channel is not allowlisted")
    if action.credential_used and not action.authorization_verified:
        hard_deny = True
        reasons.append("credential use is not independently authorized")
    if action.fragmented_sensitive_data:
        hard_deny = True
        reasons.append("fragmentation or reconstruction of sensitive data is treated as a bypass attempt")
    if action.alternate_channel_attempt:
        hard_deny = True
        reasons.append("alternate-channel boundary seeking is denied")
    if action.policy_conflict:
        hard_deny = True
        reasons.append("action conflicts with governing policy")
    if (
        action.child_authority is not None
        and action.parent_authority is not None
        and action.child_authority > action.parent_authority
    ):
        hard_deny = True
        reasons.append("delegated child authority exceeds parent authority")

    if next_blocked >= guard.blocked_attempt_pause_threshold:
        disposition = TrajectoryDisposition.PAUSE
        reasons.append("repeated blocked attempts require trajectory pause")
    elif next_risk >= guard.pause_threshold:
        disposition = TrajectoryDisposition.PAUSE
        reasons.append("cumulative trajectory risk reached pause threshold")
    elif hard_deny:
        disposition = TrajectoryDisposition.DENY
    elif next_risk >= guard.review_threshold:
        disposition = TrajectoryDisposition.HUMAN_REVIEW_REQUIRED
        reasons.append("cumulative trajectory risk requires human review")
    else:
        disposition = TrajectoryDisposition.ALLOW
        reasons.append("action remains within bounded trajectory policy")

    decision = TrajectoryDecision(
        disposition=disposition,
        reasons=reasons,
        risk_delta=delta,
        cumulative_risk=next_risk,
    )

    destinations = list(state.destinations_contacted)
    if action.destination and disposition == TrajectoryDisposition.ALLOW and action.destination not in destinations:
        destinations.append(action.destination)

    updated = state.model_copy(
        update={
            "events": [*state.events, TrajectoryEvent(action=action, decision=decision)],
            "destinations_contacted": destinations,
            "credentials_observed": state.credentials_observed + int(action.credential_observed),
            "credentials_used": state.credentials_used + int(action.credential_used and disposition == TrajectoryDisposition.ALLOW),
            "blocked_attempts": next_blocked,
            "cumulative_risk": next_risk,
        },
        deep=True,
    )
    return decision, updated
