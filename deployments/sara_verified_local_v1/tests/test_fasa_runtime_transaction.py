from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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
from worldshepherd_sara.fasa_capability_registry import (
    FASACapabilityRegistryError,
    authoritative_capability_entry,
    capability_registry_patch,
)
from worldshepherd_sara.fasa_runtime_gate import (
    admit_frontier_action_transactionally,
    verify_and_record_approval,
)
from worldshepherd_sara.storage import DurableStore


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _entry(evaluation_id: str = "EVAL-RUNTIME-001") -> CapabilityRegistryEntry:
    return CapabilityRegistryEntry(
        model_id="runtime-model",
        model_version="1.0",
        assessed_level=CapabilityLevel.F4,
        maximum_authorized_level=CapabilityLevel.F4,
        evaluation_id=evaluation_id,
        evaluation_current=True,
    )


def _candidate(level: CapabilityLevel = CapabilityLevel.F3) -> FrontierActionCandidate:
    return FrontierActionCandidate(
        action_id="ACT-RUNTIME-001",
        model_id="runtime-model",
        model_version="1.0",
        capability_level=level,
        reversible=True,
    )


def _lease(private: Ed25519PrivateKey, now: datetime) -> FASAApprovalLease:
    lease = FASAApprovalLease(
        key_id="prime-key-runtime",
        authorization_id="AUTH-RUNTIME-001",
        model_id="runtime-model",
        model_version="1.0",
        capability_level=CapabilityLevel.F3,
        action_id="ACT-RUNTIME-001",
        target_environment="staging",
        policy_id="WS-FASA-RUNTIME",
        evaluation_id="EVAL-RUNTIME-001",
        issued_at=now,
        expires_at=now + timedelta(seconds=60),
        nonce="runtime-nonce-0001",
        signature_b64url="placeholder",
    )
    signature = private.sign(canonical_approval_message(lease))
    return lease.model_copy(update={"signature_b64url": _b64url(signature)})


def _install(store: DurableStore, entry: CapabilityRegistryEntry) -> None:
    store.transact_registry(
        lambda snapshot: (capability_registry_patch(snapshot, entry), None)
    )


def test_runtime_requires_authoritative_capability_entry(tmp_path):
    store = DurableStore(tmp_path / "data")
    decision = admit_frontier_action_transactionally(
        store,
        candidate=_candidate(CapabilityLevel.F0),
        policy=FrontierSafetyPolicy(policy_id="WS-FASA-RUNTIME"),
        target_environment="staging",
        transition_id="TRANSITION-MISSING",
    )
    assert decision.disposition == FrontierDisposition.DENIED
    assert decision.evidence is None


def test_capability_update_uses_compare_and_swap(tmp_path):
    store = DurableStore(tmp_path / "data")
    _install(store, _entry())
    replacement = _entry("EVAL-RUNTIME-002")

    with pytest.raises(FASACapabilityRegistryError):
        store.transact_registry(
            lambda snapshot: (capability_registry_patch(snapshot, replacement), None)
        )

    store.transact_registry(
        lambda snapshot: (
            capability_registry_patch(
                snapshot,
                replacement,
                expected_evaluation_id="EVAL-RUNTIME-001",
            ),
            None,
        )
    )
    resolved = authoritative_capability_entry(
        store.get_registry(), model_id="runtime-model", model_version="1.0"
    )
    assert resolved.evaluation_id == "EVAL-RUNTIME-002"


def test_approval_is_consumed_before_allow_returns(tmp_path, fasa_prime_signing_key):
    now = datetime(2026, 9, 11, 19, 30, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "data")
    _install(store, _entry())
    lease = _lease(fasa_prime_signing_key, now)

    verify_and_record_approval(
        store,
        lease=lease,
        now=now + timedelta(seconds=1),
    )
    decision = admit_frontier_action_transactionally(
        store,
        candidate=_candidate(),
        policy=FrontierSafetyPolicy(policy_id="WS-FASA-RUNTIME"),
        target_environment="staging",
        transition_id="TRANSITION-001",
        lease=lease,
        now=now + timedelta(seconds=2),
    )

    assert decision.disposition == FrontierDisposition.ALLOW
    assert decision.approval_consumed is True
    state = store.get_registry()[FASA_APPROVAL_REGISTRY_KEY]["AUTH-RUNTIME-001"]
    assert state["status"] == "CONSUMED"
    assert state["consumed_transition_id"] == "TRANSITION-001"

    second = admit_frontier_action_transactionally(
        store,
        candidate=_candidate(),
        policy=FrontierSafetyPolicy(policy_id="WS-FASA-RUNTIME"),
        target_environment="staging",
        transition_id="TRANSITION-002",
        lease=lease,
        now=now + timedelta(seconds=3),
    )
    assert second.disposition == FrontierDisposition.DENIED
    assert second.approval_consumed is False
