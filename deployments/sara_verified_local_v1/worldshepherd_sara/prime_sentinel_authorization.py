from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .prime_configuration_custody import PrimeEnvironment


PRIME_SENTINEL_AUTHZ_SCHEMA = "WS-PRIME-SENTINEL-AUTHZ-V1"
PRIME_SENTINEL_AUTHZ_REGISTRY_KEY = "PRIME_SENTINEL_AUTHORIZATIONS"
MAX_ASSERTION_LIFETIME = timedelta(minutes=15)
MAX_FUTURE_SKEW = timedelta(seconds=60)


class PrimeSentinelAuthorizationError(ValueError):
    pass


class PrimeSentinelAuthorizationAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[PRIME_SENTINEL_AUTHZ_SCHEMA] = PRIME_SENTINEL_AUTHZ_SCHEMA
    issuer: Literal["PRIME_SENTINEL"] = "PRIME_SENTINEL"
    key_id: str = Field(min_length=1, max_length=128)
    authorization_id: str = Field(min_length=1, max_length=128)
    prime_id: str = Field(min_length=1, max_length=128)
    action: Literal["REQUALIFICATION_RELEASE"] = "REQUALIFICATION_RELEASE"
    target_environment: PrimeEnvironment
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    signature_b64url: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_window(self) -> "PrimeSentinelAuthorizationAssertion":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.expires_at - self.issued_at > MAX_ASSERTION_LIFETIME:
            raise ValueError("authorization lifetime exceeds 15 minutes")
        return self


class VerifiedPrimeSentinelAuthorization(BaseModel):
    authorization_id: str
    prime_id: str
    target_environment: PrimeEnvironment
    key_id: str
    key_fingerprint_sha256: str
    nonce: str
    issued_at: datetime
    expires_at: datetime


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_authorization_message(assertion: PrimeSentinelAuthorizationAssertion) -> bytes:
    payload = {
        "schema": assertion.schema,
        "issuer": assertion.issuer,
        "key_id": assertion.key_id,
        "authorization_id": assertion.authorization_id,
        "prime_id": assertion.prime_id,
        "action": assertion.action,
        "target_environment": assertion.target_environment.value,
        "issued_at": _utc_iso(assertion.issued_at),
        "expires_at": _utc_iso(assertion.expires_at),
        "nonce": assertion.nonce,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _decode_b64url(value: str, *, expected_length: int, label: str) -> bytes:
    try:
        encoded = value.encode("ascii")
        padded = encoded + b"=" * (-len(encoded) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise PrimeSentinelAuthorizationError(f"invalid {label} encoding") from exc
    if len(decoded) != expected_length:
        raise PrimeSentinelAuthorizationError(
            f"{label} must decode to {expected_length} bytes"
        )
    return decoded


class PrimeSentinelVerifier:
    def __init__(
        self,
        *,
        public_keys_b64url: dict[str, str],
        revoked_key_ids: set[str] | None = None,
    ) -> None:
        self._public_keys: dict[str, bytes] = {}
        for key_id, encoded in public_keys_b64url.items():
            if not key_id:
                raise ValueError("PRIME SENTINEL key id cannot be empty")
            self._public_keys[key_id] = _decode_b64url(
                encoded, expected_length=32, label=f"public key {key_id}"
            )
        self.revoked_key_ids = frozenset(revoked_key_ids or set())

    @property
    def configured(self) -> bool:
        return bool(self._public_keys)

    def key_is_configured(self, key_id: str) -> bool:
        return key_id in self._public_keys

    def key_is_revoked(self, key_id: str) -> bool:
        return key_id in self.revoked_key_ids

    @classmethod
    def from_environment(cls) -> "PrimeSentinelVerifier":
        raw_keys = os.getenv("PRIME_SENTINEL_PUBLIC_KEYS_JSON", "{}").strip() or "{}"
        try:
            parsed = json.loads(raw_keys)
        except json.JSONDecodeError as exc:
            raise RuntimeError("PRIME_SENTINEL_PUBLIC_KEYS_JSON is invalid JSON") from exc
        if not isinstance(parsed, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()
        ):
            raise RuntimeError("PRIME_SENTINEL_PUBLIC_KEYS_JSON must be a string-to-string object")
        revoked = {
            item.strip()
            for item in os.getenv("PRIME_SENTINEL_REVOKED_KEY_IDS", "").split(",")
            if item.strip()
        }
        try:
            return cls(public_keys_b64url=parsed, revoked_key_ids=revoked)
        except (ValueError, PrimeSentinelAuthorizationError) as exc:
            raise RuntimeError(f"invalid PRIME SENTINEL key configuration: {exc}") from exc

    def verify(
        self,
        assertion: PrimeSentinelAuthorizationAssertion,
        *,
        now: datetime | None = None,
    ) -> VerifiedPrimeSentinelAuthorization:
        if not self.configured:
            raise PrimeSentinelAuthorizationError("no PRIME SENTINEL public keys are configured")
        if assertion.key_id in self.revoked_key_ids:
            raise PrimeSentinelAuthorizationError("PRIME SENTINEL signing key is revoked")
        key_bytes = self._public_keys.get(assertion.key_id)
        if key_bytes is None:
            raise PrimeSentinelAuthorizationError("unknown PRIME SENTINEL signing key")

        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        issued = assertion.issued_at.astimezone(timezone.utc)
        expires = assertion.expires_at.astimezone(timezone.utc)
        if issued > current + MAX_FUTURE_SKEW:
            raise PrimeSentinelAuthorizationError("authorization assertion is issued too far in the future")
        if current >= expires:
            raise PrimeSentinelAuthorizationError("authorization assertion is expired")

        signature = _decode_b64url(
            assertion.signature_b64url,
            expected_length=64,
            label="Ed25519 signature",
        )
        try:
            Ed25519PublicKey.from_public_bytes(key_bytes).verify(
                signature,
                canonical_authorization_message(assertion),
            )
        except (InvalidSignature, ValueError) as exc:
            raise PrimeSentinelAuthorizationError("invalid PRIME SENTINEL Ed25519 signature") from exc

        return VerifiedPrimeSentinelAuthorization(
            authorization_id=assertion.authorization_id,
            prime_id=assertion.prime_id,
            target_environment=assertion.target_environment,
            key_id=assertion.key_id,
            key_fingerprint_sha256=hashlib.sha256(key_bytes).hexdigest(),
            nonce=assertion.nonce,
            issued_at=issued,
            expires_at=expires,
        )


def _authorization_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(PRIME_SENTINEL_AUTHZ_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise PrimeSentinelAuthorizationError(
            f"{PRIME_SENTINEL_AUTHZ_REGISTRY_KEY} must be a JSON object"
        )
    return dict(raw)


def verified_authorization_registry_patch(
    registry: dict[str, Any],
    verified: VerifiedPrimeSentinelAuthorization,
) -> dict[str, Any]:
    records = _authorization_map(registry)
    if verified.authorization_id in records:
        raise PrimeSentinelAuthorizationError("authorization_id has already been recorded")
    for entry in records.values():
        if isinstance(entry, dict) and entry.get("nonce") == verified.nonce:
            raise PrimeSentinelAuthorizationError("authorization nonce has already been recorded")
    records[verified.authorization_id] = {
        "status": "VERIFIED",
        "prime_id": verified.prime_id,
        "target_environment": verified.target_environment.value,
        "key_id": verified.key_id,
        "key_fingerprint_sha256": verified.key_fingerprint_sha256,
        "nonce": verified.nonce,
        "issued_at": _utc_iso(verified.issued_at),
        "expires_at": _utc_iso(verified.expires_at),
    }
    return {PRIME_SENTINEL_AUTHZ_REGISTRY_KEY: records}


def assert_recorded_authorization_usable(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    prime_id: str,
    target_environment: PrimeEnvironment,
    verifier: PrimeSentinelVerifier,
    now: datetime | None = None,
) -> dict[str, Any]:
    records = _authorization_map(registry)
    entry = records.get(authorization_id)
    if not isinstance(entry, dict):
        raise PrimeSentinelAuthorizationError("authorization is not recorded")
    if entry.get("status") != "VERIFIED":
        raise PrimeSentinelAuthorizationError("authorization is not in VERIFIED state")
    if entry.get("prime_id") != prime_id:
        raise PrimeSentinelAuthorizationError("authorization PRIME identity mismatch")
    if entry.get("target_environment") != target_environment.value:
        raise PrimeSentinelAuthorizationError("authorization target environment mismatch")
    key_id = entry.get("key_id")
    if not isinstance(key_id, str) or not verifier.key_is_configured(key_id):
        raise PrimeSentinelAuthorizationError("authorization signing key is no longer configured")
    if verifier.key_is_revoked(key_id):
        raise PrimeSentinelAuthorizationError("authorization signing key is revoked")
    try:
        expires = datetime.fromisoformat(str(entry["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise PrimeSentinelAuthorizationError("authorization expiry is invalid") from exc
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current >= expires.astimezone(timezone.utc):
        raise PrimeSentinelAuthorizationError("authorization is expired")
    return entry


def consumed_authorization_registry_patch(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    transition_id: str,
    consumed_at: datetime | None = None,
) -> dict[str, Any]:
    records = _authorization_map(registry)
    entry = records.get(authorization_id)
    if not isinstance(entry, dict) or entry.get("status") != "VERIFIED":
        raise PrimeSentinelAuthorizationError("authorization cannot be consumed")
    updated = dict(entry)
    updated.update(
        {
            "status": "CONSUMED",
            "consumed_transition_id": transition_id,
            "consumed_at": _utc_iso(consumed_at or datetime.now(timezone.utc)),
        }
    )
    records[authorization_id] = updated
    return {PRIME_SENTINEL_AUTHZ_REGISTRY_KEY: records}
