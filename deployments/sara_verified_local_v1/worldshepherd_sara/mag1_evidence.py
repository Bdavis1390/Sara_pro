from __future__ import annotations

import hashlib
import json
from typing import Any

from .autonomy_policy import AutonomyPolicy
from .context_lineage import ContextArtifact
from .event_outbox import queue_event_outbox_patch
from .mag1_gate import Mag1Decision
from .trajectory_guard import TrajectoryAction, TrajectoryGuardPolicy


MAG1_EVIDENCE_SCHEMA = "WS-MAG1-EVIDENCE-V1"
MAG1_POLICY_BUNDLE_SCHEMA = "WS-MAG1-POLICY-BUNDLE-V1"
MAG1_EVENT_NAME = "mag1_decision"
MAG1_EVENT_ACTOR = "MAG1_GATE"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def policy_bundle_sha256(
    autonomy_policy: AutonomyPolicy,
    trajectory_policy: TrajectoryGuardPolicy | None = None,
) -> str:
    guard = trajectory_policy or TrajectoryGuardPolicy()
    document = {
        "schema": MAG1_POLICY_BUNDLE_SCHEMA,
        "autonomy_policy": autonomy_policy.model_dump(mode="json"),
        "trajectory_guard_policy": guard.model_dump(mode="json"),
        "context_lineage_schema": "WS-MAG1-CONTEXT-LINEAGE-V1",
        "authorization_schema": "WS-MAG1-AUTHORIZATION-V1",
    }
    return _sha256(document)


def mag1_evidence_event_id(*, trajectory_id: str, action_id: str) -> str:
    digest = _sha256(
        {
            "schema": MAG1_EVIDENCE_SCHEMA,
            "trajectory_id": trajectory_id,
            "action_id": action_id,
        }
    )
    return f"SARA-EVENT-MAG1-{digest}"


def build_mag1_evidence_payload(
    *,
    decision: Mag1Decision,
    trajectory_action: TrajectoryAction,
    autonomy_policy: AutonomyPolicy,
    trajectory_policy: TrajectoryGuardPolicy | None = None,
    authorization_id: str | None = None,
    authority_artifact: ContextArtifact | None = None,
) -> dict[str, Any]:
    """Build a secret-minimized evidence payload for a completed MAG-1 decision.

    The evidence intentionally stores hashes/counts rather than model text,
    candidate payloads, credentials, or raw policy-reason strings.
    """

    if not decision.updated_trajectory.events:
        raise ValueError("MAG-1 decision has no trajectory event to evidence")
    last_event = decision.updated_trajectory.events[-1]
    if last_event.action.action_id != trajectory_action.action_id:
        raise ValueError("trajectory action does not match the decision's final event")

    reasons_digest = _sha256(decision.reasons)
    return {
        "schema": MAG1_EVIDENCE_SCHEMA,
        "trajectory_id": decision.updated_trajectory.trajectory_id,
        "action_id": trajectory_action.action_id,
        "action_type": trajectory_action.action_type,
        "side_effect_class": trajectory_action.side_effect.value,
        "mag1_disposition": decision.disposition.value,
        "trajectory_disposition": decision.trajectory_disposition.value,
        "autonomy_disposition": decision.autonomy_disposition.value,
        "authorization_disposition": (
            None
            if decision.authorization_disposition is None
            else decision.authorization_disposition.value
        ),
        "cumulative_risk": last_event.decision.cumulative_risk,
        "risk_delta": last_event.decision.risk_delta,
        "blocked_attempts": decision.updated_trajectory.blocked_attempts,
        "policy_bundle_sha256": policy_bundle_sha256(
            autonomy_policy,
            trajectory_policy,
        ),
        "authorization_id": authorization_id,
        "authority_artifact_id": (
            None if authority_artifact is None else authority_artifact.artifact_id
        ),
        "authority_source_type": (
            None if authority_artifact is None else authority_artifact.source_type.value
        ),
        "authority_content_hash": (
            None if authority_artifact is None else authority_artifact.content_hash
        ),
        "reason_count": len(decision.reasons),
        "reasons_sha256": reasons_digest,
    }


def queue_mag1_evidence_patch(
    registry: dict[str, Any],
    *,
    decision: Mag1Decision,
    trajectory_action: TrajectoryAction,
    autonomy_policy: AutonomyPolicy,
    trajectory_policy: TrajectoryGuardPolicy | None = None,
    authorization_id: str | None = None,
    authority_artifact: ContextArtifact | None = None,
) -> tuple[dict[str, Any], str]:
    payload = build_mag1_evidence_payload(
        decision=decision,
        trajectory_action=trajectory_action,
        autonomy_policy=autonomy_policy,
        trajectory_policy=trajectory_policy,
        authorization_id=authorization_id,
        authority_artifact=authority_artifact,
    )
    event_id = mag1_evidence_event_id(
        trajectory_id=decision.updated_trajectory.trajectory_id,
        action_id=trajectory_action.action_id,
    )
    return queue_event_outbox_patch(
        registry,
        event=MAG1_EVENT_NAME,
        actor=MAG1_EVENT_ACTOR,
        payload=payload,
        event_id=event_id,
    )
