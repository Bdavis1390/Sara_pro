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
    verified_authorization_registry_patch,
)
from worldshepherd_sara.storage import DurableStore, RegistryIntegrityError


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _verified_record(now: datetime):
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={"PS-K1": _b64url(private.public_key().public_bytes_raw())}
    )
    assertion = PrimeSentinelAuthorizationAssertion(
        key_id="PS-K1",
        authorization_id="AUTH-001",
        prime_id="PRIME-001",
        target_environment=PrimeEnvironment.SPACE,
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce="nonce-0123456789abcdef",
        signature_b64url=_b64url(b"0" * 64),
    )
    signature = private.sign(canonical_authorization_message(assertion))
    assertion = assertion.model_copy(update={"signature_b64url": _b64url(signature)})
    verified = verifier.verify(assertion, now=now)
    registry = verified_authorization_registry_patch({}, verified)
    return verifier, registry


def test_consumption_rejects_corrupted_signed_lifetime():
    now = datetime.now(timezone.utc)
    verifier, registry = _verified_record(now)
    entry = registry["PRIME_SENTINEL_AUTHORIZATIONS"]["AUTH-001"]
    entry["issued_at"] = now.isoformat()
    entry["expires_at"] = (now + timedelta(hours=1)).isoformat()

    with pytest.raises(PrimeSentinelAuthorizationError, match="signed window"):
        assert_recorded_authorization_usable(
            registry,
            authorization_id="AUTH-001",
            prime_id="PRIME-001",
            target_environment=PrimeEnvironment.SPACE,
            verifier=verifier,
            now=now,
        )


def test_consumption_rejects_passport_key_binding_mismatch():
    now = datetime.now(timezone.utc)
    verifier, registry = _verified_record(now)
    registry["PRIME_DIGITAL_PASSPORTS"] = {
        "PRIME-001": {
            "custody": {
                "requalification_release_authorization_id": "AUTH-001",
                "requalification_release_target_environment": "SPACE",
                "requalification_release_key_id": "CORRUPTED-KEY-ID",
            }
        }
    }

    with pytest.raises(PrimeSentinelAuthorizationError, match="signing key mismatch"):
        assert_recorded_authorization_usable(
            registry,
            authorization_id="AUTH-001",
            prime_id="PRIME-001",
            target_environment=PrimeEnvironment.SPACE,
            verifier=verifier,
            now=now,
        )


def test_durable_store_raises_integrity_error_for_invalid_registry_json(tmp_path):
    store = DurableStore(tmp_path)
    store.registry_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(RegistryIntegrityError, match="registry integrity validation failed"):
        store.get_registry()
