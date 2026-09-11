from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.fasa import CapabilityLevel
from worldshepherd_sara.fasa_approval_lease import (
    FASAApprovalError,
    FASAApprovalLease,
    PrimeSentinelFASAApprovalVerifier,
    canonical_approval_message,
    verified_approval_registry_patch,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keys():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    verifier = PrimeSentinelFASAApprovalVerifier(
        public_keys_b64url={"prime-key-1": _b64url(public)}
    )
    return private, verifier, _b64url(public)


def _signed(private: Ed25519PrivateKey, *, now: datetime, **overrides) -> FASAApprovalLease:
    values = {
        "key_id": "prime-key-1",
        "authorization_id": "AUTH-001",
        "model_id": "model-A",
        "model_version": "1.0",
        "capability_level": CapabilityLevel.F3,
        "action_id": "ACT-001",
        "target_environment": "staging",
        "policy_id": "WS-FASA-001",
        "evaluation_id": "EVAL-001",
        "issued_at": now,
        "expires_at": now + timedelta(seconds=60),
        "nonce": "0123456789abcdef",
        "signature_b64url": "placeholder",
    }
    values.update(overrides)
    lease = FASAApprovalLease(**values)
    return lease.model_copy(
        update={"signature_b64url": _b64url(private.sign(canonical_approval_message(lease)))}
    )


def test_tampering_with_signed_field_invalidates_signature():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, verifier, _ = _keys()
    lease = _signed(private, now=now)
    tampered = lease.model_copy(update={"action_id": "ACT-TAMPERED"})
    with pytest.raises(FASAApprovalError, match="invalid PRIME SENTINEL Ed25519 signature"):
        verifier.verify(tampered, now=now + timedelta(seconds=1))


def test_unknown_signing_key_fails_closed():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, _, public_b64 = _keys()
    lease = _signed(private, now=now).model_copy(update={"key_id": "unknown-key"})
    verifier = PrimeSentinelFASAApprovalVerifier(
        public_keys_b64url={"prime-key-1": public_b64}
    )
    with pytest.raises(FASAApprovalError, match="unknown PRIME SENTINEL signing key"):
        verifier.verify(lease, now=now + timedelta(seconds=1))


def test_lease_issued_beyond_future_skew_is_rejected():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, verifier, _ = _keys()
    issued = now + timedelta(seconds=61)
    lease = _signed(
        private,
        now=issued,
        expires_at=issued + timedelta(seconds=30),
    )
    with pytest.raises(FASAApprovalError, match="issued too far in the future"):
        verifier.verify(lease, now=now)


def test_risk_level_time_ceilings_are_enforced_at_model_validation():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, _, _ = _keys()
    with pytest.raises(ValueError, match="ceiling of 120 seconds"):
        _signed(
            private,
            now=now,
            capability_level=CapabilityLevel.F3,
            expires_at=now + timedelta(seconds=121),
        )
    with pytest.raises(ValueError, match="ceiling of 60 seconds"):
        _signed(
            private,
            now=now,
            capability_level=CapabilityLevel.F4,
            expires_at=now + timedelta(seconds=61),
        )


def test_duplicate_authorization_id_and_duplicate_nonce_are_rejected():
    now = datetime(2026, 9, 11, 18, 0, tzinfo=timezone.utc)
    private, verifier, _ = _keys()
    first = verifier.verify(_signed(private, now=now), now=now + timedelta(seconds=1))
    registry = verified_approval_registry_patch({}, first)

    with pytest.raises(FASAApprovalError, match="authorization_id has already been recorded"):
        verified_approval_registry_patch(registry, first)

    second = verifier.verify(
        _signed(
            private,
            now=now,
            authorization_id="AUTH-002",
            nonce="0123456789abcdef",
        ),
        now=now + timedelta(seconds=1),
    )
    with pytest.raises(FASAApprovalError, match="nonce has already been recorded"):
        verified_approval_registry_patch(registry, second)
