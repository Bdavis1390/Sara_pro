from __future__ import annotations

from worldshepherd_sara.autonomy_policy import AutonomousActionCandidate, AutonomyPolicy
from worldshepherd_sara.echo_event_store import EchoEventConflict, EchoEventStore
from worldshepherd_sara.event_outbox import EVENT_OUTBOX_REGISTRY_KEY
from worldshepherd_sara.mag1_evidence import (
    MAG1_EVENT_ACTOR,
    MAG1_EVENT_NAME,
    build_mag1_evidence_payload,
    mag1_evidence_event_id,
    policy_bundle_sha256,
    queue_mag1_evidence_patch,
)
from worldshepherd_sara.mag1_gate import Mag1Disposition, evaluate_mag1
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.trajectory_guard import (
    SideEffectClass,
    TrajectoryAction,
    TrajectoryGuardPolicy,
    TrajectoryState,
)


def _policy() -> AutonomyPolicy:
    return AutonomyPolicy(
        policy_id="POL-EVIDENCE",
        allowed_auto_action_types=["refresh_cache"],
        minimum_auto_confidence=0.99,
        maximum_auto_authority=1,
    )


def _candidate() -> AutonomousActionCandidate:
    return AutonomousActionCandidate(
        action_id="C-EVIDENCE",
        action_type="refresh_cache",
        confidence=1.0,
        requested_authority=1,
        reversible=True,
        payload={"secret": "must-never-enter-evidence"},
    )


def _state() -> TrajectoryState:
    return TrajectoryState(
        trajectory_id="TRJ-EVIDENCE",
        originating_human_request_hash="sha256:request",
        root_authority="human:CRE1AWS",
    )


def _action() -> TrajectoryAction:
    return TrajectoryAction(
        action_id="ACT-EVIDENCE",
        action_type="refresh_cache",
        side_effect=SideEffectClass.LOCAL_WRITE,
    )


def _decision():
    action = _action()
    policy = _policy()
    decision = evaluate_mag1(
        candidate=_candidate(),
        autonomy_policy=policy,
        trajectory_state=_state(),
        trajectory_action=action,
    )
    assert decision.disposition == Mag1Disposition.AUTO_ELIGIBLE
    return decision, action, policy


def _audit_record(payload: dict, event_id: str) -> AuditRecord:
    delivered = dict(payload)
    delivered["_outbox_event_id"] = event_id
    delivered["_delivery_semantics"] = "AT_LEAST_ONCE"
    return AuditRecord.create(
        event=MAG1_EVENT_NAME,
        actor=MAG1_EVENT_ACTOR,
        payload=delivered,
    )


def test_policy_bundle_hash_is_deterministic_and_policy_sensitive():
    policy = _policy()
    guard = TrajectoryGuardPolicy()
    first = policy_bundle_sha256(policy, guard)
    second = policy_bundle_sha256(policy, guard)
    changed = policy_bundle_sha256(
        policy,
        TrajectoryGuardPolicy(review_threshold=7),
    )
    assert first == second
    assert len(first) == 64
    assert first != changed


def test_stable_event_id_is_bound_to_trajectory_and_action():
    first = mag1_evidence_event_id(
        trajectory_id="TRJ-1",
        action_id="ACT-1",
    )
    replay = mag1_evidence_event_id(
        trajectory_id="TRJ-1",
        action_id="ACT-1",
    )
    other = mag1_evidence_event_id(
        trajectory_id="TRJ-1",
        action_id="ACT-2",
    )
    assert first == replay
    assert first != other
    assert first.startswith("SARA-EVENT-MAG1-")


def test_evidence_payload_excludes_candidate_payload_and_raw_reasons():
    decision, action, policy = _decision()
    payload = build_mag1_evidence_payload(
        decision=decision,
        trajectory_action=action,
        autonomy_policy=policy,
    )
    serialized = repr(payload)
    assert "must-never-enter-evidence" not in serialized
    assert "candidate_payload" not in payload
    assert "reasons" not in payload
    assert payload["reason_count"] == len(decision.reasons)
    assert len(payload["reasons_sha256"]) == 64


def test_queue_uses_existing_outbox_with_deterministic_event_id():
    decision, action, policy = _decision()
    patch, event_id = queue_mag1_evidence_patch(
        {},
        decision=decision,
        trajectory_action=action,
        autonomy_policy=policy,
    )
    assert event_id in patch[EVENT_OUTBOX_REGISTRY_KEY]
    entry = patch[EVENT_OUTBOX_REGISTRY_KEY][event_id]
    assert entry["event"] == MAG1_EVENT_NAME
    assert entry["actor"] == MAG1_EVENT_ACTOR
    assert entry["status"] == "PENDING"
    assert entry["delivery_semantics"] == "AT_LEAST_ONCE"


def test_echo_deduplicates_exact_mag1_replay_and_rejects_tamper(tmp_path):
    decision, action, policy = _decision()
    payload = build_mag1_evidence_payload(
        decision=decision,
        trajectory_action=action,
        autonomy_policy=policy,
    )
    event_id = mag1_evidence_event_id(
        trajectory_id=decision.updated_trajectory.trajectory_id,
        action_id=action.action_id,
    )
    store = EchoEventStore(tmp_path)
    first = store.ingest(_audit_record(payload, event_id))
    second = store.ingest(_audit_record(payload, event_id))
    assert first.outcome == "STORED"
    assert second.outcome == "DEDUPLICATED"
    assert second.record.delivery_count == 2

    tampered = dict(payload)
    tampered["mag1_disposition"] = "DENIED"
    try:
        store.ingest(_audit_record(tampered, event_id))
    except EchoEventConflict:
        pass
    else:
        raise AssertionError("tampered MAG-1 event must conflict in ECHO")
