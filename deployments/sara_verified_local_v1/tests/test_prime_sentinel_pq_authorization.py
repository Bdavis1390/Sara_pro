from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from worldshepherd_sara.prime_configuration_custody import PrimeEnvironment
from worldshepherd_sara.prime_sentinel_authorization import (
    PRIME_SENTINEL_MLDSA65_CONTEXT,
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
    canonical_authorization_message,
    verified_authorization_registry_patch,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _pq_key_record(private: MLDSA65PrivateKey) -> dict[str, str]:
    raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    assert len(raw) == 1952
    return {
        "algorithm": "ML-DSA-65",
        "public_key_b64url": _b64url(raw),
        "signature_context": PRIME_SENTINEL_MLDSA65_CONTEXT.decode("ascii"),
    }


def _signed_assertion(
    private: MLDSA65PrivateKey,
    *,
    now: datetime,
    authorization_id: str = "PQ-AUTH-001",
    nonce: str = "pq-nonce-0123456789abcdef",
    prime_id: str = "PRIME-PQ-001",
    target_environment: PrimeEnvironment = PrimeEnvironment.SPACE,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> PrimeSentinelAuthorizationAssertion:
    assertion = PrimeSentinelAuthorizationAssertion(
        key_id="PS-PQ-K1",
        authorization_id=authorization_id,
        prime_id=prime_id,
        target_environment=target_environment,
        issued_at=issued_at or now,
        expires_at=expires_at or now + timedelta(minutes=5),
        nonce=nonce,
        signature_b64url="UNSIGNED",
    )
    signature = private.sign(
        canonical_authorization_message(assertion),
        PRIME_SENTINEL_MLDSA65_CONTEXT,
    )
    assert len(signature) == 3309
    return assertion.model_copy(update={"signature_b64url": _b64url(signature)})


def test_valid_mldsa65_assertion_verifies_and_records_pq_algorithm():
    private = MLDSA65PrivateKey.generate()
    verifier = PrimeSentinelVerifier(public_keys={"PS-PQ-K1": _pq_key_record(private)})
    now = datetime.now(timezone.utc)
    verified = verifier.verify(_signed_assertion(private, now=now), now=now)
    assert verified.authorization_id == "PQ-AUTH-001"
    assert verified.signing_algorithm == "ML-DSA-65"
    assert verified.signature_context == PRIME_SENTINEL_MLDSA65_CONTEXT.decode("ascii")
    registry = verified_authorization_registry_patch({}, verified)
    stored = registry["PRIME_SENTINEL_AUTHORIZATIONS"]["PQ-AUTH-001"]
    assert stored["signing_algorithm"] == "ML-DSA-65"
    assert stored["signature_context"] == PRIME_SENTINEL_MLDSA65_CONTEXT.decode("ascii")


def test_mldsa65_signed_field_tamper_fails_closed():
    private = MLDSA65PrivateKey.generate()
    verifier = PrimeSentinelVerifier(public_keys={"PS-PQ-K1": _pq_key_record(private)})
    now = datetime.now(timezone.utc)
    assertion = _signed_assertion(private, now=now)
    tampered = assertion.model_copy(update={"prime_id": "PRIME-TAMPERED"})
    with pytest.raises(PrimeSentinelAuthorizationError, match="signature"):
        verifier.verify(tampered, now=now)


def test_mldsa65_wrong_context_configuration_is_rejected_before_verification():
    private = MLDSA65PrivateKey.generate()
    record = _pq_key_record(private)
    record["signature_context"] = "WRONG-CONTEXT"
    with pytest.raises(PrimeSentinelAuthorizationError, match="context mismatch"):
        PrimeSentinelVerifier(public_keys={"PS-PQ-K1": record})


def test_mldsa65_signature_length_mismatch_is_rejected():
    private = MLDSA65PrivateKey.generate()
    verifier = PrimeSentinelVerifier(public_keys={"PS-PQ-K1": _pq_key_record(private)})
    now = datetime.now(timezone.utc)
    assertion = _signed_assertion(private, now=now)
    malformed = assertion.model_copy(update={"signature_b64url": _b64url(b"x" * 64)})
    with pytest.raises(PrimeSentinelAuthorizationError, match="3309 bytes"):
        verifier.verify(malformed, now=now)


def test_structured_environment_key_configuration_supports_mldsa65(monkeypatch):
    private = MLDSA65PrivateKey.generate()
    monkeypatch.setenv(
        "PRIME_SENTINEL_PUBLIC_KEYS_JSON",
        json.dumps({"PS-PQ-K1": _pq_key_record(private)}, sort_keys=True),
    )
    verifier = PrimeSentinelVerifier.from_environment()
    assert verifier.configured is True
    assert verifier.key_algorithm("PS-PQ-K1") == "ML-DSA-65"
    now = datetime.now(timezone.utc)
    assert verifier.verify(_signed_assertion(private, now=now), now=now).signing_algorithm == "ML-DSA-65"


def test_mldsa65_expiry_and_replay_guards_are_unchanged():
    private = MLDSA65PrivateKey.generate()
    verifier = PrimeSentinelVerifier(public_keys={"PS-PQ-K1": _pq_key_record(private)})
    now = datetime.now(timezone.utc)
    expired = _signed_assertion(
        private,
        now=now,
        issued_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(minutes=1),
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="expired"):
        verifier.verify(expired, now=now)

    first = verifier.verify(_signed_assertion(private, now=now), now=now)
    registry = verified_authorization_registry_patch({}, first)
    duplicate = verifier.verify(_signed_assertion(private, now=now), now=now)
    with pytest.raises(PrimeSentinelAuthorizationError, match="authorization_id"):
        verified_authorization_registry_patch(registry, duplicate)
