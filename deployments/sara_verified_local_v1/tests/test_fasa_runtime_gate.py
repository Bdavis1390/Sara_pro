from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
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
    PrimeSentinelFASAApprovalVerifier,
    canonical_approval_message,
)
from worldshepherd_sara.fasa_capability_registry import (
    FASA_CAPABILITY_REGISTRY_KEY,
    FASACapabilityRegistryError,
    authoritative_capability_entry,
    capability_registry_patch,
)
from worldshepherd_sara.fasa_runtime_gate import (
    admit_frontier_action_transactionally,
    record_verified_approval,
)
from worldshepherd_sara.storage import DurableStore


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keypair():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    verifier = PrimeSentinelFASAApprovalVerifier(
        public_keys_b64url={"prime-key-runtime": _b64url(public)}
    )
    return private, verifier


def _capability_entry(
    *,
    evaluation_id: str = "EVAL-RUNTIME-001",
    assessed_level: CapabilityLevel = CapabilityLevel.F4,
    maximum_authorized_level: CapabilityLevel = CapabilityLevel.F4,
) -> CapabilityRegistryEntry:
    return CapabilityRegistryEntry(
        model_id="runtime-model",
        model_version="1.0",
        assessed_level=assessed_level,
        maximum_authorized_level=maximum_authorized_level,
        evaluation_id=evaluation_id,
        evaluation_current=True,
    )


def _candidate(level: CapabilityLevel = CapabilityLevel.F3):
    return FrontierActionCandidate(
        action_id="ACT-RUNTIME-001",
        model_id="runtime-model",
        model_version="1.0",
        capability_level=level,
        reversible=True,
    )


def _signed_lease(private: Ed25519PrivateKey, *, now: datetime):
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


def _install_capability(store: DurableStore, entry: CapabilityRegistryEntry):
    def operation(snapshot):
        return capability_registry_patch(snapshot, entry), entry

    return store.transact_registry(operation)


def test_runtime_gate_denies_when_authoritative_capability_entry_is_missing(tmp_path):
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
    assert decision.approval_consumed is False
    assert any("authoritative capability registry" in reason for reason in decision.reasons)


def test_capability_registry_replacement_requires_compare_and_swap(tmp_path):
    store = DurableStore(tmp_path / "data")
    original = _install_capability(store, _capability_entry())
    assert original.evaluation_id == "EVAL-RUNTIME-001"

    changed = _capability_entry(
        evaluation_id="EVAL-RUNTIME-002",
        maximum_authorized_level=CapabilityLevel.F3,
    )

    def replace_without_expected(snapshot):
        return capability_registry_patch(snapshot, changed), None

    try:
        store.transact_registry(replace_without_expected)
    except FASACapabilityRegistryError as exc:
        assert "expected_evaluation_id" in str(exc)
    else:
        raise AssertionError("capability replacement unexpectedly bypassed compare-and-swap")

    def replace_with_expected(snapshot):
        return (
            capability_registry_patch(
                snapshot,
                changed,
                expected_evaluation_id="EVAL-RUNTIME-001",
            ),
            None,
        )

    store.transact_registry(replace_with_expected)
    resolved = authoritative_capability_entry(
        store.get_registry(), model_id="runtime-model", model_version="1.0"
    )
    assert resolved.evaluation_id == "EVAL-RUNTIME-002"
    assert resolved.maximum_authorized_level == CapabilityLevel.F3


def test_approval_gated_allow_consumes_lease_before_return(tmp_path):
    now = datetime(2026, 9, 11, 19, 30, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "data")
    _install_capability(store, _capability_entry())

    private, verifier = _keypair()
    lease = _signed_lease(private, now=now)
    verified = verifier.verify(lease, now=now + timedelta(seconds=1))
    record_verified_approval(store, verified)

    decision = admit_frontier_action_transactionally(
        store,
        candidate=_candidate(),
        policy=FrontierSafetyPolicy(policy_id="WS-FASA-RUNTIME"),
        target_environment="staging",
        transition_id="TRANSITION-001",
        lease=lease,
        verifier=verifier,
        now=now + timedelta(seconds=2),
    )
    assert decision.disposition == FrontierDisposition.ALLOW
    assert decision.approval_consumed is True
    assert decision.authorization_id == "AUTH-RUNTIME-001"
    assert decision.evidence is not None
    assert decision.evidence.authorization_id == "AUTH-RUNTIME-001"

    approval_state = store.get_registry()[FASA_APPROVAL_REGISTRY_KEY]["AUTH-RUNTIME-001"]
    assert approval_state["status"] == "CONSUMED"
    assert approval_state["consumed_transition_id"] == "TRANSITION-001"

    replay = admit_frontier_action_transactionally(
        store,
        candidate=_candidate(),
        policy=FrontierSafetyPolicy(policy_id="WS-FASA-RUNTIME"),
        target_environment="staging",
        transition_id="TRANSITION-REPLAY",
        lease=lease,
        verifier=verifier,
        now=now + timedelta(seconds=3),
    )
    assert replay.disposition == FrontierDisposition.DENIED
    assert replay.approval_consumed is False
    assert any("VERIFIED state" in reason for reason in replay.reasons)


def test_concurrent_replay_can_produce_only_one_allow(tmp_path):
    now = datetime(2026, 9, 11, 19, 35, tzinfo=timezone.utc)
    store = DurableStore(tmp_path / "data")
    _install_capability(store, _capability_entry())

    private, verifier = _keypair()
    lease = _signed_lease(private, now=now)
    verified = verifier.verify(lease, now=now + timedelta(seconds=1))
    record_verified_approval(store, verified)
    policy = FrontierSafetyPolicy(policy_id="WS-FASA-RUNTIME")

    def attempt(transition_id: str):
        return admit_frontier_action_transactionally(
            store,
            candidate=_candidate(),
            policy=policy,
            target_environment="staging",
            transition_id=transition_id,
            lease=lease,
            verifier=verifier,
            now=now + timedelta(seconds=2),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        decisions = list(executor.map(attempt, ["TRANSITION-A", "TRANSITION-B"]))

    dispositions = [decision.disposition for decision in decisions]
    assert dispositions.count(FrontierDisposition.ALLOW) == 1
    assert dispositions.count(FrontierDisposition.DENIED) == 1
    assert sum(decision.approval_consumed for decision in decisions) == 1

    registry = store.get_registry()
    assert FASA_CAPABILITY_REGISTRY_KEY in registry
    approval_state = registry[FASA_APPROVAL_REGISTRY_KEY]["AUTH-RUNTIME-001"]
    assert approval_state["status"] == "CONSUMED"
    assert approval_state["consumed_transition_id"] in {"TRANSITION-A", "TRANSITION-B"}
