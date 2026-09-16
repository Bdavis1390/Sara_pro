from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_ACTION,
    PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY,
    PrimeSentinelPoOAuthorizationAssertion,
    PrimeSentinelPoOAuthorizationError,
    PrimeSentinelPoOVerifier,
    canonical_poo_authorization_message,
    consumed_poo_authorization_registry_patch,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keys():
    private = Ed25519PrivateKey.generate()
    public_b64 = _b64url(private.public_key().public_bytes_raw())
    verifier = PrimeSentinelPoOVerifier(public_keys_b64url={"PS-K1": public_b64})
    return private, verifier


def _signed(
    private: Ed25519PrivateKey,
    *,
    now: datetime,
    authorization_id: str = "POO-AUTH-001",
    nonce: str = "poo-nonce-0123456789abcdef",
    asset_id: str = "asset:alpha",
    projection_digest: str = "sha256:" + "1" * 64,
    source_digest: str = "source:decision:001",
    expected_registry_digest: str = "2" * 64,
    candidate_registry_digest: str = "3" * 64,
    candidate_state_digest: str = "state:digest:001",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> PrimeSentinelPoOAuthorizationAssertion:
    assertion = PrimeSentinelPoOAuthorizationAssertion(
        key_id="PS-K1",
        authorization_id=authorization_id,
        asset_id=asset_id,
        governance_projection_digest=projection_digest,
        source_decision_digest=source_digest,
        expected_registry_digest=expected_registry_digest,
        candidate_registry_digest=candidate_registry_digest,
        candidate_state_digest=candidate_state_digest,
        issued_at=issued_at or now,
        expires_at=expires_at or now + timedelta(minutes=5),
        nonce=nonce,
        signature_b64url=_b64url(b"0" * 64),
    )
    signature = private.sign(canonical_poo_authorization_message(assertion))
    return assertion.model_copy(update={"signature_b64url": _b64url(signature)})


def test_valid_poo_commit_assertion_verifies_and_binds_exact_scope():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    assertion = _signed(private, now=now)
    verified = verifier.verify(assertion, now=now)
    assert assertion.action == PRIME_SENTINEL_POO_ACTION
    assert verified.authorization_id == "POO-AUTH-001"
    assert verified.asset_id == "asset:alpha"
    assert verified.governance_projection_digest == "sha256:" + "1" * 64
    assert verified.expected_registry_digest == "2" * 64
    assert verified.candidate_registry_digest == "3" * 64
    assert verified.candidate_state_digest == "state:digest:001"


def test_tampering_any_signed_scope_field_breaks_signature():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    assertion = _signed(private, now=now)
    for field, value in (
        ("asset_id", "asset:other"),
        ("governance_projection_digest", "sha256:" + "4" * 64),
        ("source_decision_digest", "source:other"),
        ("expected_registry_digest", "5" * 64),
        ("candidate_registry_digest", "6" * 64),
        ("candidate_state_digest", "state:other"),
    ):
        tampered = assertion.model_copy(update={field: value})
        with pytest.raises(PrimeSentinelPoOAuthorizationError, match="signature"):
            verifier.verify(tampered, now=now)


def test_expired_unknown_and_revoked_keys_fail_closed():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    expired = _signed(
        private,
        now=now,
        issued_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(minutes=1),
    )
    with pytest.raises(PrimeSentinelPoOAuthorizationError, match="expired"):
        verifier.verify(expired, now=now)

    valid = _signed(private, now=now)
    unknown = valid.model_copy(update={"key_id": "UNKNOWN"})
    with pytest.raises(PrimeSentinelPoOAuthorizationError, match="unknown"):
        verifier.verify(unknown, now=now)

    revoked = PrimeSentinelPoOVerifier(
        public_keys_b64url={"PS-K1": _b64url(private.public_key().public_bytes_raw())},
        revoked_key_ids={"PS-K1"},
    )
    with pytest.raises(PrimeSentinelPoOAuthorizationError, match="revoked"):
        revoked.verify(valid, now=now)


def test_assertion_schema_rejects_unknown_fields_and_wrong_action():
    private, _ = _keys()
    now = datetime.now(timezone.utc)
    payload = _signed(private, now=now).model_dump(mode="json")
    payload["authority"] = True
    with pytest.raises(ValueError):
        PrimeSentinelPoOAuthorizationAssertion.model_validate(payload)

    payload.pop("authority")
    payload["action"] = "REQUALIFICATION_RELEASE"
    with pytest.raises(ValueError):
        PrimeSentinelPoOAuthorizationAssertion.model_validate(payload)


def test_consumption_is_one_time_but_exact_same_commit_is_idempotent():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    verified = verifier.verify(_signed(private, now=now), now=now)
    patch = consumed_poo_authorization_registry_patch(
        {}, verified=verified, commit_id="POO-COMMIT-001", consumed_at=now
    )
    entry = patch[PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY]["POO-AUTH-001"]
    assert entry["status"] == "CONSUMED"
    assert entry["commit_id"] == "POO-COMMIT-001"

    retry = consumed_poo_authorization_registry_patch(
        patch, verified=verified, commit_id="POO-COMMIT-001", consumed_at=now
    )
    assert retry == patch

    with pytest.raises(PrimeSentinelPoOAuthorizationError, match="different PoO commit"):
        consumed_poo_authorization_registry_patch(
            patch, verified=verified, commit_id="POO-COMMIT-OTHER", consumed_at=now
        )


def test_nonce_cannot_be_reused_by_different_authorization():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    first = verifier.verify(_signed(private, now=now), now=now)
    registry = consumed_poo_authorization_registry_patch(
        {}, verified=first, commit_id="POO-COMMIT-001", consumed_at=now
    )
    second = verifier.verify(
        _signed(private, now=now, authorization_id="POO-AUTH-002"), now=now
    )
    with pytest.raises(PrimeSentinelPoOAuthorizationError, match="nonce"):
        consumed_poo_authorization_registry_patch(
            registry, verified=second, commit_id="POO-COMMIT-002", consumed_at=now
        )
