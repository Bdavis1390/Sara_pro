from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.prime_configuration_custody import PrimeEnvironment
from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
    assert_recorded_authorization_usable,
    canonical_authorization_message,
    consumed_authorization_registry_patch,
    verified_authorization_registry_patch,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keys():
    private = Ed25519PrivateKey.generate()
    public_b64 = _b64url(private.public_key().public_bytes_raw())
    verifier = PrimeSentinelVerifier(public_keys_b64url={"PS-K1": public_b64})
    return private, verifier


def _signed_assertion(
    private: Ed25519PrivateKey,
    *,
    now: datetime,
    authorization_id: str = "AUTH-001",
    nonce: str = "nonce-0123456789abcdef",
    prime_id: str = "PRIME-001",
    target_environment: PrimeEnvironment = PrimeEnvironment.SPACE,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> PrimeSentinelAuthorizationAssertion:
    assertion = PrimeSentinelAuthorizationAssertion(
        key_id="PS-K1",
        authorization_id=authorization_id,
        prime_id=prime_id,
        target_environment=target_environment,
        issued_at=issued_at or now,
        expires_at=expires_at or now + timedelta(minutes=5),
        nonce=nonce,
        signature_b64url=_b64url(b"0" * 64),
    )
    signature = private.sign(canonical_authorization_message(assertion))
    return assertion.model_copy(update={"signature_b64url": _b64url(signature)})


def test_valid_ed25519_assertion_verifies_with_public_key_only():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    assertion = _signed_assertion(private, now=now)
    verified = verifier.verify(assertion, now=now)
    assert verified.authorization_id == "AUTH-001"
    assert verified.prime_id == "PRIME-001"
    assert verified.target_environment == PrimeEnvironment.SPACE
    assert verified.key_id == "PS-K1"
    assert len(verified.key_fingerprint_sha256) == 64


def test_tampered_signed_field_fails_signature_verification():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    assertion = _signed_assertion(private, now=now)
    tampered = assertion.model_copy(update={"prime_id": "PRIME-OTHER"})
    with pytest.raises(PrimeSentinelAuthorizationError, match="signature"):
        verifier.verify(tampered, now=now)


def test_unknown_and_revoked_keys_fail_closed():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    assertion = _signed_assertion(private, now=now)
    unknown = assertion.model_copy(update={"key_id": "PS-UNKNOWN"})
    with pytest.raises(PrimeSentinelAuthorizationError, match="unknown"):
        verifier.verify(unknown, now=now)

    revoked = PrimeSentinelVerifier(
        public_keys_b64url={"PS-K1": _b64url(private.public_key().public_bytes_raw())},
        revoked_key_ids={"PS-K1"},
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="revoked"):
        revoked.verify(assertion, now=now)


def test_expired_and_future_assertions_fail_closed():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    expired = _signed_assertion(
        private,
        now=now,
        issued_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(minutes=1),
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="expired"):
        verifier.verify(expired, now=now)

    future = _signed_assertion(
        private,
        now=now,
        issued_at=now + timedelta(minutes=2),
        expires_at=now + timedelta(minutes=7),
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="future"):
        verifier.verify(future, now=now)


def test_assertion_lifetime_over_15_minutes_is_rejected_by_schema():
    private, _ = _keys()
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="15 minutes"):
        _signed_assertion(
            private,
            now=now,
            issued_at=now,
            expires_at=now + timedelta(minutes=16),
        )


def test_authorization_id_and_nonce_replay_are_rejected():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    first = verifier.verify(_signed_assertion(private, now=now), now=now)
    registry = verified_authorization_registry_patch({}, first)

    replay_id = verifier.verify(
        _signed_assertion(
            private,
            now=now,
            authorization_id="AUTH-001",
            nonce="nonce-different-0123456",
        ),
        now=now,
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="authorization_id"):
        verified_authorization_registry_patch(registry, replay_id)

    replay_nonce = verifier.verify(
        _signed_assertion(
            private,
            now=now,
            authorization_id="AUTH-002",
            nonce="nonce-0123456789abcdef",
        ),
        now=now,
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="nonce"):
        verified_authorization_registry_patch(registry, replay_nonce)


def test_recorded_authorization_must_match_prime_target_not_be_revoked_and_be_unexpired():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    verified = verifier.verify(_signed_assertion(private, now=now), now=now)
    registry = verified_authorization_registry_patch({}, verified)

    entry = assert_recorded_authorization_usable(
        registry,
        authorization_id="AUTH-001",
        prime_id="PRIME-001",
        target_environment=PrimeEnvironment.SPACE,
        verifier=verifier,
        now=now,
    )
    assert entry["status"] == "VERIFIED"

    with pytest.raises(PrimeSentinelAuthorizationError, match="target environment"):
        assert_recorded_authorization_usable(
            registry,
            authorization_id="AUTH-001",
            prime_id="PRIME-001",
            target_environment=PrimeEnvironment.AERO,
            verifier=verifier,
            now=now,
        )

    with pytest.raises(PrimeSentinelAuthorizationError, match="expired"):
        assert_recorded_authorization_usable(
            registry,
            authorization_id="AUTH-001",
            prime_id="PRIME-001",
            target_environment=PrimeEnvironment.SPACE,
            verifier=verifier,
            now=now + timedelta(minutes=6),
        )


def test_authorization_is_one_time_consumable():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    verified = verifier.verify(_signed_assertion(private, now=now), now=now)
    registry = verified_authorization_registry_patch({}, verified)
    consumed = consumed_authorization_registry_patch(
        registry,
        authorization_id="AUTH-001",
        transition_id="PRIME-CUSTODY-123",
        consumed_at=now,
    )
    entry = consumed["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-001"]
    assert entry["status"] == "CONSUMED"
    assert entry["consumed_transition_id"] == "PRIME-CUSTODY-123"
    with pytest.raises(PrimeSentinelAuthorizationError, match="cannot be consumed"):
        consumed_authorization_registry_patch(
            consumed,
            authorization_id="AUTH-001",
            transition_id="PRIME-CUSTODY-456",
            consumed_at=now,
        )


def test_expired_consumed_outcome_is_retained_for_reconciliation():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    active = verifier.verify(
        _signed_assertion(private, now=now, authorization_id="AUTH-ACTIVE"),
        now=now,
    )
    registry = verified_authorization_registry_patch({}, active)
    consumed = consumed_authorization_registry_patch(
        registry,
        authorization_id="AUTH-ACTIVE",
        transition_id="PRIME-CUSTODY-ACTIVE",
        consumed_at=now,
    )
    consumed_entry = dict(consumed["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-ACTIVE"])
    consumed_entry["expires_at"] = (now - timedelta(seconds=1)).isoformat()
    expired_consumed = {"PRIME_SENTINEL_AUTHORIZATIONS": {"AUTH-ACTIVE": consumed_entry}}

    replacement = verifier.verify(
        _signed_assertion(
            private,
            now=now,
            authorization_id="AUTH-NEW",
            nonce="nonce-new-0123456789abcdef",
        ),
        now=now,
    )
    retained = verified_authorization_registry_patch(expired_consumed, replacement)
    assert retained["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-ACTIVE"]["status"] == "CONSUMED"
    assert "AUTH-NEW" in retained["PRIME_SENTINEL_AUTHORIZATIONS"]


def test_active_window_capacity_exhaustion_fails_closed():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    records = {}
    for index in range(64):
        verified = verifier.verify(
            _signed_assertion(
                private,
                now=now,
                authorization_id=f"AUTH-{index:03d}",
                nonce=f"nonce-{index:03d}-0123456789abcdef",
            ),
            now=now,
        )
        records = verified_authorization_registry_patch(records, verified)

    overflow = verifier.verify(
        _signed_assertion(
            private,
            now=now,
            authorization_id="AUTH-OVERFLOW",
            nonce="nonce-overflow-0123456789",
        ),
        now=now,
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="capacity exhausted"):
        verified_authorization_registry_patch(records, overflow)


def test_terminal_history_capacity_fails_closed_instead_of_erasing_outcomes():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    terminal = {
        "PRIME_SENTINEL_AUTHORIZATIONS": {
            f"TERMINAL-{index:03d}": {
                "status": "CONSUMED",
                "prime_id": "PRIME-001",
                "target_environment": "SPACE",
                "key_id": "PS-K1",
                "key_fingerprint_sha256": "0" * 64,
                "nonce": f"terminal-nonce-{index:03d}",
                "issued_at": (now - timedelta(minutes=6)).isoformat(),
                "expires_at": (now - timedelta(minutes=1)).isoformat(),
                "consumed_transition_id": f"TRANSITION-{index:03d}",
                "consumed_at": (now - timedelta(minutes=2)).isoformat(),
            }
            for index in range(64)
        }
    }
    fresh = verifier.verify(
        _signed_assertion(
            private,
            now=now,
            authorization_id="AUTH-FRESH",
            nonce="nonce-fresh-0123456789abcdef",
        ),
        now=now,
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="capacity exhausted"):
        verified_authorization_registry_patch(terminal, fresh)
    assert len(terminal["PRIME_SENTINEL_AUTHORIZATIONS"]) == 64


def test_expired_verified_authorizations_are_pruned_before_capacity():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    records = {"PRIME_SENTINEL_AUTHORIZATIONS": {
        f"EXPIRED-{i}": {
            "status": "VERIFIED",
            "nonce": f"old-nonce-{i}",
            "expires_at": (now - timedelta(seconds=1)).isoformat(),
        } for i in range(64)
    }}
    fresh = verifier.verify(
        _signed_assertion(
            private,
            now=now,
            authorization_id="AUTH-FRESH",
            nonce="nonce-fresh-0123456789abcdef",
        ),
        now=now,
    )
    patch = verified_authorization_registry_patch(records, fresh)
    assert list(patch["PRIME_SENTINEL_AUTHORIZATIONS"]) == ["AUTH-FRESH"]
