from __future__ import annotations

from datetime import datetime, timedelta, timezone

from worldshepherd_sara.authorization_envelope import (
    AuthorizationDisposition,
    AuthorizationEnvelope,
    AuthorizationRequest,
)
from worldshepherd_sara.autonomy_policy import AutonomousActionCandidate, AutonomyPolicy
from worldshepherd_sara.context_lineage import ContextArtifact, ContextSourceType
from worldshepherd_sara.mag1_gate import Mag1Disposition, evaluate_mag1
from worldshepherd_sara.trajectory_guard import SideEffectClass, TrajectoryAction, TrajectoryState


NOW = datetime(2026, 9, 17, 17, 0, tzinfo=timezone.utc)


def _state() -> TrajectoryState:
    return TrajectoryState(
        trajectory_id="TRJ-COMPOSITE",
        originating_human_request_hash="sha256:request",
        root_authority="human:CRE1AWS",
    )


def _candidate() -> AutonomousActionCandidate:
    return AutonomousActionCandidate(
        action_id="A-PUBLISH",
        action_type="publish_report",
        confidence=1.0,
        requested_authority=1,
        reversible=True,
    )


def _policy() -> AutonomyPolicy:
    return AutonomyPolicy(
        policy_id="POL-COMPOSITE",
        allowed_auto_action_types=["publish_report"],
        minimum_auto_confidence=0.99,
        maximum_auto_authority=1,
    )


def _root_artifact() -> ContextArtifact:
    return ContextArtifact(
        artifact_id="CTX-ROOT",
        source_type=ContextSourceType.HUMAN_ROOT_INSTRUCTION,
        source_ref="human:CRE1AWS",
        content_hash="sha256:root-instruction",
    )


def _envelope() -> AuthorizationEnvelope:
    return AuthorizationEnvelope(
        authorization_id="AUTH-PUBLISH",
        principal="human:CRE1AWS",
        workflow_id="WF-MAG1",
        action="publish_report",
        resource="report:MAG-1",
        purpose="authorized assurance publication",
        scopes=["report:publish"],
        destinations=["https://approved.example/reports"],
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=1),
        external_egress=True,
    )


def _request() -> AuthorizationRequest:
    return AuthorizationRequest(
        workflow_id="WF-MAG1",
        action="publish_report",
        resource="report:MAG-1",
        purpose="authorized assurance publication",
        required_scopes=["report:publish"],
        destination="https://approved.example/reports",
        external_egress=True,
    )


def test_high_consequence_action_implicitly_requires_authorization():
    decision = evaluate_mag1(
        candidate=_candidate(),
        autonomy_policy=_policy(),
        trajectory_state=_state(),
        trajectory_action=TrajectoryAction(
            action_id="T-PUBLISH-1",
            action_type="publish_report",
            side_effect=SideEffectClass.PUBLISH,
            authorization_verified=True,
        ),
    )
    assert decision.disposition == Mag1Disposition.DENIED
    assert decision.authorization_disposition == AuthorizationDisposition.DENIED
    assert decision.updated_trajectory.events[-1].action.authorization_verified is False


def test_valid_high_consequence_authorization_can_pass_composite_gate():
    decision = evaluate_mag1(
        candidate=_candidate(),
        autonomy_policy=_policy(),
        trajectory_state=_state(),
        trajectory_action=TrajectoryAction(
            action_id="T-PUBLISH-2",
            action_type="publish_report",
            side_effect=SideEffectClass.PUBLISH,
            destination="https://approved.example/reports",
        ),
        authorization_envelope=_envelope(),
        authorization_request=_request(),
        authority_artifact=_root_artifact(),
        authorization_now=NOW,
    )
    assert decision.disposition == Mag1Disposition.AUTO_ELIGIBLE
    assert decision.authorization_disposition == AuthorizationDisposition.AUTHORIZED
