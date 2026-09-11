from __future__ import annotations

import base64
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
    FASAAssuranceEvidence,
    FASAApprovalLease,
    PrimeSentinelFASAApprovalVerifier,
    canonical_approval_message,
    consumed_approval_registry_patch,
    evaluate_frontier_action_with_approval,
    verified_approval_registry_patch,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keypair():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    verifier = PrimeSentinelFASAApprovalVerifier(
        public_keys_b64url={"prime-key-1": _b64url(public)}
    )
    return private, verifier


def _registry() -> CapabilityRegistryEntry:
    return CapabilityRegistryEntry(
        model_id="model-A",
        model_version="1.0",
        assessed_level=CapabilityLevel.F4,
        maximum_authorized_level=CapabilityLevel.F4,
        evaluation_id="EVAL-001",
        evaluation_current=True,
    )


def _candidate(level: CapabilityLevel, **overrides) -> FrontierActionCandidate:
    values = {
        "action_id": "ACT-001",
        "model_id": "model-A",
        "model_version": "1.0",
        "capability_level": level,
        "reversible": True,
    }
    values.update(overrides)
    return FrontierActionCandidate(**values)


def _signed_lease(
    private: Ed25519PrivateKey,
    *,
    level: CapabilityLevel = CapabilityLevel.F3,
    now: datetime,
    action_id: str = "ACT-001",
    model_version: str = "1.0",
    target_environment: str = "staging",
    policy_id: str = "WS-FASA-001",
    evaluation_id: str = "EVAL-001",
    safety_case_id: str | None = None,
    independent_review_id: str | None = None,
    ttl_seconds: int = 60,
) -> FASAApprovalLease:
    lease = FASAApprovalLease(
        key_id="prime-key-1",
        authorization_id="AUTH-001",
        model_id="model-A",
        model_version=model_version,
        capability_level=level,
        action_id=action_id,
        target_environment=target_environment,
        policy_id=policy_id,
        evaluation_id=evaluation_id,
        safety_case_id=safety_case_id,
        independent_review_id=independent_review_id,
        issued_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
        nonce="0123456789abcdef",
        signature_b64url="placeholder",
    )
    signature = private.sign(canonical_approval_message(lease))
    return lease.model_copy(update={"signature_b64url": _b64url(signature)})


def test_self_asserted_human_approval_is_ignored_without_signed_lease():
    policy = FrontierSafetyPolicy(policy_id="WS-FASA-001")
    disposition, reasons, verified = evaluate_frontier_action_with_approval(
        _candidate(CapabilityLevel.F3, human_approval_present=True),
        _registry(),
        policy,
        target_environment="staging",
    )
    assert disposition == FrontierDisposition.HUMAN_REVIEW_REQUIRED
    assert verified is None
    assert any("human approval" in reason for reason in reasons)


def test_valid_prime_signed_f3_approval_can_authorize_when_other_gates_pass():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, verifier = _keypair()
    lease = _signed_lease(private, now=now)
    disposition, _, verified = evaluate_frontier_action_with_approval(
        _candidate(CapabilityLevel.F3),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
        target_environment="staging",
        lease=lease,
        verifier=verifier,
        now=now + timedelta(seconds=1),
    )
    assert disposition == FrontierDisposition.ALLOW
    assert verified is not None
    assert verified.authorization_id == "AUTH-001"


def test_signed_approval_is_bound_to_action_model_policy_evaluation_and_environment():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, verifier = _keypair()
    lease = _signed_lease(private, now=now, action_id="ACT-OTHER")
    disposition, reasons, _ = evaluate_frontier_action_with_approval(
        _candidate(CapabilityLevel.F3),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
        target_environment="staging",
        lease=lease,
        verifier=verifier,
        now=now + timedelta(seconds=1),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("action identity" in reason for reason in reasons)


def test_expired_or_revoked_approval_fails_closed():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, verifier = _keypair()
    lease = _signed_lease(private, now=now, ttl_seconds=30)
    disposition, reasons, _ = evaluate_frontier_action_with_approval(
        _candidate(CapabilityLevel.F3),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
        target_environment="staging",
        lease=lease,
        verifier=verifier,
        now=now + timedelta(seconds=31),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("expired" in reason for reason in reasons)

    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    revoked = PrimeSentinelFASAApprovalVerifier(
        public_keys_b64url={"prime-key-1": _b64url(public)},
        revoked_key_ids={"prime-key-1"},
    )
    disposition, reasons, _ = evaluate_frontier_action_with_approval(
        _candidate(CapabilityLevel.F3),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
        target_environment="staging",
        lease=lease,
        verifier=revoked,
        now=now + timedelta(seconds=1),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("revoked" in reason for reason in reasons)


def test_f4_requires_matching_current_safety_case_and_independent_review():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, verifier = _keypair()
    lease = _signed_lease(
        private,
        level=CapabilityLevel.F4,
        now=now,
        ttl_seconds=45,
        safety_case_id="SC-001",
        independent_review_id="IR-001",
    )
    assurance = FASAAssuranceEvidence(
        safety_case_id="SC-001",
        safety_case_current=True,
        independent_review_id="IR-001",
        independent_review_current=True,
    )
    disposition, _, verified = evaluate_frontier_action_with_approval(
        _candidate(CapabilityLevel.F4),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
        target_environment="staging",
        assurance=assurance,
        lease=lease,
        verifier=verifier,
        now=now + timedelta(seconds=1),
    )
    assert disposition == FrontierDisposition.ALLOW
    assert verified is not None


def test_consumed_approval_cannot_be_reused_when_registry_enforcement_is_enabled():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, verifier = _keypair()
    lease = _signed_lease(private, now=now)
    verified = verifier.verify(lease, now=now + timedelta(seconds=1))
    state = verified_approval_registry_patch({}, verified)
    consumed = consumed_approval_registry_patch(
        state,
        authorization_id=verified.authorization_id,
        transition_id="TRANSITION-001",
        consumed_at=now + timedelta(seconds=2),
    )
    disposition, reasons, _ = evaluate_frontier_action_with_approval(
        _candidate(CapabilityLevel.F3),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
        target_environment="staging",
        lease=lease,
        verifier=verifier,
        approval_registry=consumed,
        now=now + timedelta(seconds=3),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("VERIFIED state" in reason for reason in reasons)


def test_f5_leases_remain_disabled():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, _ = _keypair()
    try:
        _signed_lease(private, level=CapabilityLevel.F5, now=now, ttl_seconds=1)
    except ValueError as exc:
        assert "F5 approval leases are disabled" in str(exc)
    else:
        raise AssertionError("F5 lease construction must fail closed")
