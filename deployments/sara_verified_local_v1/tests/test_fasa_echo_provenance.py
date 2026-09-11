from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara import event_outbox as event_outbox_module
from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    SINK_ECHO,
    SINK_SARA_AUDIT,
    drain_event_outbox,
    drain_event_outbox_to_echo,
    outbox_status,
)
from worldshepherd_sara.fasa import (
    CapabilityLevel,
    CapabilityRegistryEntry,
    FrontierActionCandidate,
    FrontierDisposition,
    FrontierSafetyPolicy,
)
from worldshepherd_sara.fasa_approval_lease import (
    FASAApprovalLease,
    FASA_APPROVAL_REGISTRY_KEY,
    canonical_approval_message,
)
from worldshepherd_sara.fasa_capability_registry import capability_registry_patch
from worldshepherd_sara.fasa_runtime_gate import (
    FASA_ECHO_EVIDENCE_SCHEMA,
    FASA_EXECUTION_READINESS_REGISTRY_KEY,
    FASARuntimeGateError,
    acknowledge_echo_and_confirm_execution_readiness,
    admit_frontier_action_transactionally,
    consume_execution_readiness,
    verify_and_record_approval,
)
from worldshepherd_sara.storage import DurableStore


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _entry() -> CapabilityRegistryEntry:
    return CapabilityRegistryEntry(
        model_id="fasa-echo-model",
        model_version="1.0",
        assessed_level=CapabilityLevel.F3,
        maximum_authorized_level=CapabilityLevel.F3,
        evaluation_id="EVAL-FASA-ECHO-001",
        evaluation_current=True,
    )


def _candidate() -> FrontierActionCandidate:
    return FrontierActionCandidate(
        action_id="ACT-FASA-ECHO-001",
        model_id="fasa-echo-model",
        model_version="1.0",
        capability_level=CapabilityLevel.F3,
        reversible=True,
        provenance_enabled=True,
        overwatch_enabled=True,
    )


def _lease(private: Ed25519PrivateKey, now: datetime) -> FASAApprovalLease:
    lease = FASAApprovalLease(
        key_id="prime-key-runtime",
        authorization_id="AUTH-FASA-ECHO-001",
        model_id="fasa-echo-model",
        model_version="1.0",
        capability_level=CapabilityLevel.F3,
        action_id="ACT-FASA-ECHO-001",
        target_environment="staging",
        policy_id="WS-FASA-ECHO",
        evaluation_id="EVAL-FASA-ECHO-001",
        issued_at=now,
        expires_at=now + timedelta(seconds=60),
        nonce="fasa-echo-nonce-0001",
        signature_b64url="placeholder",
    )
    signature = private.sign(canonical_approval_message(lease))
    return lease.model_copy(update={"signature_b64url": _b64url(signature)})


def _install(store: DurableStore) -> None:
    entry = _entry()
    store.transact_registry(
        lambda snapshot: (capability_registry_patch(snapshot, entry), None)
    )


def _authorize_and_admit(
    store: DurableStore,
    private: Ed25519PrivateKey,
    *,
    now: datetime,
):
    lease = _lease(private, now)
    verify_and_record_approval(
        store,
        lease=lease,
        now=now + timedelta(seconds=1),
    )
    decision = admit_frontier_action_transactionally(
        store,
        candidate=_candidate(),
        policy=FrontierSafetyPolicy(policy_id="WS-FASA-ECHO"),
        target_environment="staging",
        transition_id="TRANSITION-FASA-ECHO-001",
        lease=lease,
        now=now + timedelta(seconds=2),
    )
    return lease, decision


def test_approval_consumption_and_echo_obligation_commit_together(
    tmp_path, fasa_prime_signing_key
):
    now = datetime(2026, 9, 11, 20, 0, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "sara")
    _install(store)

    _lease_value, decision = _authorize_and_admit(
        store, fasa_prime_signing_key, now=now
    )

    assert decision.disposition == FrontierDisposition.ALLOW
    assert decision.approval_consumed is True
    assert decision.provenance_delivery == "PENDING_REQUIRED_SINKS"
    assert decision.provenance_event_id is not None

    registry = store.get_registry()
    approval = registry[FASA_APPROVAL_REGISTRY_KEY]["AUTH-FASA-ECHO-001"]
    event = registry[EVENT_OUTBOX_REGISTRY_KEY][decision.provenance_event_id]
    assert approval["status"] == "CONSUMED"
    assert approval["consumed_transition_id"] == "TRANSITION-FASA-ECHO-001"
    assert event["status"] == "PENDING"
    assert set(event["required_sinks"]) == {SINK_SARA_AUDIT, SINK_ECHO}
    assert event["delivered_sinks"] == []
    assert event["payload"]["schema"] == FASA_ECHO_EVIDENCE_SCHEMA
    assert event["payload"]["decision_digest_sha256"] == (
        decision.evidence.decision_digest_sha256
    )
    assert event["payload"]["evaluation_id"] == "EVAL-FASA-ECHO-001"
    assert event["payload"]["authorization_id"] == "AUTH-FASA-ECHO-001"


def test_sara_audit_delivery_does_not_complete_required_echo_sink(
    tmp_path, fasa_prime_signing_key
):
    now = datetime(2026, 9, 11, 20, 5, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "sara")
    _install(store)
    _lease_value, decision = _authorize_and_admit(
        store, fasa_prime_signing_key, now=now
    )
    event_id = decision.provenance_event_id
    assert event_id is not None

    assert drain_event_outbox(store, limit=10) == 1
    registry = store.get_registry()
    event = registry[EVENT_OUTBOX_REGISTRY_KEY][event_id]
    assert event["status"] == "PENDING"
    assert event["delivered_sinks"] == [SINK_SARA_AUDIT]
    assert outbox_status(registry)["pending"] == 1


def test_echo_delivery_and_signed_checkpoint_include_same_fasa_event(
    tmp_path, fasa_prime_signing_key, echo_checkpoint_key
):
    now = datetime(2026, 9, 11, 20, 10, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "sara")
    _install(store)
    _lease_value, decision = _authorize_and_admit(
        store, fasa_prime_signing_key, now=now
    )
    event_id = decision.provenance_event_id
    assert event_id is not None

    assert drain_event_outbox(store, limit=10) == 1
    echo_store = EchoEventStore((tmp_path / "echo").resolve())
    assert drain_event_outbox_to_echo(store, echo_store, limit=10) == 1

    registry = store.get_registry()
    event = registry[EVENT_OUTBOX_REGISTRY_KEY][event_id]
    assert event["status"] == "DELIVERED"
    assert set(event["delivered_sinks"]) == {SINK_SARA_AUDIT, SINK_ECHO}
    assert outbox_status(registry)["pending"] == 0

    stored = echo_store.get(event_id)
    assert stored is not None
    payload = stored.payload()
    assert payload["schema"] == FASA_ECHO_EVIDENCE_SCHEMA
    assert payload["decision_digest_sha256"] == decision.evidence.decision_digest_sha256
    assert payload["_outbox_event_id"] == event_id
    assert payload["_delivery_semantics"] == "AT_LEAST_ONCE"

    checkpoint_private_key, _key_path = echo_checkpoint_key
    checkpoints = EchoCheckpointManager(
        echo_store,
        private_key=checkpoint_private_key,
        key_id="ECHO-FASA-CHECKPOINT-TEST",
    )
    bundle = checkpoints.create_checkpoint()
    checkpoint_ids = {
        item["event_id"] for item in bundle["manifest"]["events"]
    }
    assert event_id in checkpoint_ids
    assert bundle["manifest"]["event_count"] == 1
    assert bundle["signature_b64url"]


def test_outbox_capacity_failure_denies_and_leaves_approval_verified(
    tmp_path, fasa_prime_signing_key, monkeypatch
):
    now = datetime(2026, 9, 11, 20, 15, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "sara")
    _install(store)
    lease = _lease(fasa_prime_signing_key, now)
    verify_and_record_approval(
        store,
        lease=lease,
        now=now + timedelta(seconds=1),
    )

    monkeypatch.setattr(event_outbox_module, "MAX_PENDING_OUTBOX_EVENTS", 0)
    decision = admit_frontier_action_transactionally(
        store,
        candidate=_candidate(),
        policy=FrontierSafetyPolicy(policy_id="WS-FASA-ECHO"),
        target_environment="staging",
        transition_id="TRANSITION-FASA-ECHO-FAIL",
        lease=lease,
        now=now + timedelta(seconds=2),
    )

    assert decision.disposition == FrontierDisposition.DENIED
    assert decision.approval_consumed is False
    assert decision.provenance_delivery == "FAILED_CLOSED"
    assert decision.provenance_event_id is None
    assert any("provenance obligation" in reason for reason in decision.reasons)

    registry = store.get_registry()
    approval = registry[FASA_APPROVAL_REGISTRY_KEY]["AUTH-FASA-ECHO-001"]
    assert approval["status"] == "VERIFIED"
    assert EVENT_OUTBOX_REGISTRY_KEY not in registry


def test_echo_hold_requires_both_sinks_and_readiness_is_single_use(
    tmp_path, fasa_prime_signing_key
):
    now = datetime(2026, 9, 11, 20, 20, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "sara")
    _install(store)
    lease = _lease(fasa_prime_signing_key, now)
    verify_and_record_approval(store, lease=lease, now=now + timedelta(seconds=1))

    decision = admit_frontier_action_transactionally(
        store,
        candidate=_candidate(),
        policy=FrontierSafetyPolicy(
            policy_id="WS-FASA-ECHO",
            echo_ack_before_execution_level=CapabilityLevel.F3,
        ),
        target_environment="staging",
        transition_id="TRANSITION-FASA-ECHO-HOLD",
        lease=lease,
        now=now + timedelta(seconds=2),
    )
    assert decision.disposition == FrontierDisposition.ECHO_ACK_REQUIRED
    assert decision.approval_consumed is True
    assert decision.provenance_event_id is not None

    waiting = store.get_registry()[FASA_EXECUTION_READINESS_REGISTRY_KEY][
        "TRANSITION-FASA-ECHO-HOLD"
    ]
    assert waiting["status"] == "WAITING_ECHO"

    echo_store = EchoEventStore((tmp_path / "echo-held").resolve())
    readiness = acknowledge_echo_and_confirm_execution_readiness(
        store,
        echo_store,
        decision=decision,
        now=now + timedelta(seconds=3),
    )
    assert readiness.ready is True

    registry = store.get_registry()
    event = registry[EVENT_OUTBOX_REGISTRY_KEY][decision.provenance_event_id]
    assert event["status"] == "DELIVERED"
    assert set(event["delivered_sinks"]) == {SINK_SARA_AUDIT, SINK_ECHO}
    assert registry[FASA_EXECUTION_READINESS_REGISTRY_KEY][
        "TRANSITION-FASA-ECHO-HOLD"
    ]["status"] == "READY"

    consumed = consume_execution_readiness(
        store,
        readiness=readiness,
        execution_id="EXECUTION-FASA-ECHO-001",
        now=now + timedelta(seconds=4),
    )
    assert consumed.consumed is True
    assert store.get_registry()[FASA_EXECUTION_READINESS_REGISTRY_KEY][
        "TRANSITION-FASA-ECHO-HOLD"
    ]["status"] == "CONSUMED"

    with pytest.raises(FASARuntimeGateError, match="already been consumed"):
        consume_execution_readiness(
            store,
            readiness=readiness,
            execution_id="EXECUTION-FASA-ECHO-REPLAY",
            now=now + timedelta(seconds=5),
        )
