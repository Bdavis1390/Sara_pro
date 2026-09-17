from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .authorization_envelope import (
    AuthorizationDisposition,
    AuthorizationEnvelope,
    AuthorizationRequest,
    evaluate_authorization,
)
from .autonomy_policy import (
    AutonomousActionCandidate,
    AutonomyPolicy,
    ExecutionDisposition,
    evaluate_candidate,
)
from .context_lineage import ContextArtifact, evaluate_authority_claim
from .trajectory_guard import (
    TrajectoryAction,
    TrajectoryDisposition,
    TrajectoryGuardPolicy,
    TrajectoryState,
    assess_action,
)


class Mag1Disposition(str, Enum):
    AUTO_ELIGIBLE = "AUTO_ELIGIBLE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DENIED = "DENIED"
    PAUSED = "PAUSED"


class Mag1Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: Mag1Disposition
    reasons: list[str] = Field(default_factory=list)
    authorization_disposition: AuthorizationDisposition | None = None
    trajectory_disposition: TrajectoryDisposition
    autonomy_disposition: ExecutionDisposition
    updated_trajectory: TrajectoryState


def evaluate_mag1(
    *,
    candidate: AutonomousActionCandidate,
    autonomy_policy: AutonomyPolicy,
    trajectory_state: TrajectoryState,
    trajectory_action: TrajectoryAction,
    trajectory_policy: TrajectoryGuardPolicy | None = None,
    authorization_required: bool = False,
    authorization_envelope: AuthorizationEnvelope | None = None,
    authorization_request: AuthorizationRequest | None = None,
    authority_artifact: ContextArtifact | None = None,
) -> Mag1Decision:
    """Compose context, purpose-bound authorization, trajectory, and autonomy gates.

    When purpose-bound authorization is required, the caller cannot self-assert
    ``trajectory_action.authorization_verified``. The composite gate overwrites
    that value from the authorization decision.
    """

    reasons: list[str] = []
    authorization_disposition: AuthorizationDisposition | None = None
    authorization_verified = not authorization_required

    if authorization_required:
        if authority_artifact is None:
            reasons.append("authorization requires a root or signed-policy authority artifact")
            authorization_disposition = AuthorizationDisposition.DENIED
        else:
            authority_ok, authority_reasons = evaluate_authority_claim(authority_artifact)
            reasons.extend(authority_reasons)
            if not authority_ok:
                authorization_disposition = AuthorizationDisposition.DENIED

        if authorization_request is None:
            reasons.append("authorization request is required for consequential action")
            authorization_disposition = AuthorizationDisposition.DENIED
        elif authorization_disposition != AuthorizationDisposition.DENIED:
            authorization_disposition, auth_reasons = evaluate_authorization(
                authorization_envelope,
                authorization_request,
            )
            reasons.extend(auth_reasons)
            authorization_verified = authorization_disposition == AuthorizationDisposition.AUTHORIZED

    guarded_action = trajectory_action.model_copy(
        update={"authorization_verified": authorization_verified},
        deep=True,
    )
    trajectory_decision, updated_trajectory = assess_action(
        trajectory_state,
        guarded_action,
        trajectory_policy,
    )
    autonomy_disposition, autonomy_reasons = evaluate_candidate(candidate, autonomy_policy)
    reasons.extend(trajectory_decision.reasons)
    reasons.extend(autonomy_reasons)

    if trajectory_decision.disposition == TrajectoryDisposition.PAUSE:
        disposition = Mag1Disposition.PAUSED
    elif (
        authorization_disposition == AuthorizationDisposition.DENIED
        or trajectory_decision.disposition == TrajectoryDisposition.DENY
        or autonomy_disposition == ExecutionDisposition.DENIED
    ):
        disposition = Mag1Disposition.DENIED
    elif (
        authorization_disposition == AuthorizationDisposition.HUMAN_REVIEW_REQUIRED
        or trajectory_decision.disposition == TrajectoryDisposition.HUMAN_REVIEW_REQUIRED
        or autonomy_disposition == ExecutionDisposition.HUMAN_REVIEW_REQUIRED
    ):
        disposition = Mag1Disposition.HUMAN_REVIEW_REQUIRED
    else:
        disposition = Mag1Disposition.AUTO_ELIGIBLE

    return Mag1Decision(
        disposition=disposition,
        reasons=reasons,
        authorization_disposition=authorization_disposition,
        trajectory_disposition=trajectory_decision.disposition,
        autonomy_disposition=autonomy_disposition,
        updated_trajectory=updated_trajectory,
    )
