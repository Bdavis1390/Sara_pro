from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey
from pydantic import BaseModel, ConfigDict, Field, model_validator


PRIME_SENTINEL_PQ_POO_AUTHZ_SCHEMA = "WS-PRIME-SENTINEL-PQ-POO-COMMIT-AUTHZ-V1"
PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY = "PRIME_SENTINEL_PQ_POO_AUTHORIZATIONS"
PRIME_SENTINEL_PQ_POO_ACTION = "POO_TECHNICAL_STATE_COMMIT"
PRIME_SENTINEL_PQ_POO_TARGET_SERVICE = "SARA"
PRIME_SENTINEL_PQ_POO_TARGET_ENVIRONMENT = "VERIFIED_LOCAL"
PRIME_SENTINEL_PQ_ALGORITHM = "ML-DSA-65"
PRIME_SENTINEL_PQ_STANDARD = "FIPS-204"
PRIME_SENTINEL_PQ_CONTEXT_TEXT = "WS-POO-PQ-COMMIT-V1"
PRIME_SENTINEL_PQ_CONTEXT = PRIME_SENTINEL_PQ_CONTEXT_TEXT.encode("ascii")
ML_DSA_65_PUBLIC_KEY_BYTES = 1952
ML_DSA_65_SIGNATURE_BYTES = 3309
MAX_ASSERTION_LIFETIME = timedelta(minutes=15)
MAX_FUTURE_SKEW = timedelta(seconds=60)


class PrimeSentinelPqPoOAuthorizationError(ValueError):
    pass


class PrimeSentinelPqPoOAuthorizationAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[PRIME_SENTINEL_PQ_POO_AUTHZ_SCHEMA] = PRIME_SENTINEL_PQ_POO_AUTHZ_SCHEMA
    issuer: Literal["PRIME_SENTINEL_PQ"] = "PRIME_SENTINEL_PQ"
    algorithm: Literal[PRIME_SENTINEL_PQ_ALGORITHM] = PRIME_SENTINEL_PQ_ALGORITHM
    standard: Literal[PRIME_SENTINEL_PQ_STANDARD] = PRIME_SENTINEL_PQ_STANDARD
    signature_context: Literal[PRIME_SENTINEL_PQ_CONTEXT_TEXT] = PRIME_SENTINEL_PQ_CONTEXT_TEXT
    key_id: str = Field(min_length=1, max_length=128)
    authorization_id: str = Field(min_length=1, max_length=128)
    action: Literal[PRIME_SENTINEL_PQ_POO_ACTION] = PRIME_SENTINEL_PQ_POO_ACTION
    target_service: Literal[PRIME_SENTINEL_PQ_POO_TARGET_SERVICE] = PRIME_SENTINEL_PQ_POO_TARGET_SERVICE
    target_environment: Literal[PRIME_SENTINEL_PQ_POO_TARGET_ENVIRONMENT] = PRIME_SENTINEL_PQ_POO_TARGET_ENVIRONMENT
    asset_id: str = Field(min_length=1, max_length=256)
    governance_projection_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_decision_digest: str = Field(min_length=1, max_length=256)
    expected_registry_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_registry_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_state_digest: str = Field(min_length=1, max_length=256)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    signature_b64url: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_window(self) -> "PrimeSentinelPqPoOAuthorizationAssertion":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.expires_at - self.issued_at > MAX_ASSERTION_LIFETIME:
            raise ValueError("authorization lifetime exceeds 15 minutes")
        return self


class VerifiedPrimeSentinelPqPoOAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorization_id: str
    asset_id: str
    governance_projection_digest: str
    source_decision_digest: str
    expected_registry_digest: str
    candidate_registry_digest: str
    candidate_state_digest: str
    key_id: str
    algorithm: Literal[PRIME_SENTINEL_PQ_ALGORITHM] = PRIME_SENTINEL_PQ_ALGORITHM
    standard: Literal[PRIME_SENTINEL_PQ_STANDARD] = PRIME_SENTINEL_PQ_STANDARD
    key_fingerprint_sha256: str
    signed_assertion_sha256: str
    nonce: str
    issued_at: datetime
    expires_at: datetime


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_pq_poo_authorization_message(
    assertion: PrimeSentinelPqPoOAuthorizationAssertion,
) -> bytes:
    payload = {
        "schema": assertion.schema,
        "issuer": assertion.issuer,
        "algorithm": assertion.algorithm,
        "standard": assertion.standard,
        "signature_context": assertion.signature_context,
        "key_id": assertion.key_id,
        "authorization_id": assertion.authorization_id,
        "action": assertion.action,
        "target_service": assertion.target_service,
        "target_environment": assertion.target_environment,
        "asset_id": assertion.asset_id,
        "governance_projection_digest": assertion.governance_projection_digest,
        "source_decision_digest": assertion.source_decision_digest,
        "expected_registry_digest": assertion.expected_registry_digest,
        "candidate_registry_digest": assertion.candidate_registry_digest,
        "candidate_state_digest": assertion.candidate_state_digest,
        "issued_at": _utc_iso(assertion.issued_at),
        "expires_at": _utc_iso(assertion.expires_at),
        "nonce": assertion.nonce,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def signed_pq_poo_authorization_fingerprint(
    assertion: PrimeSentinelPqPoOAuthorizationAssertion,
) -> str:
    raw = json.dumps(
        assertion.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _decode_b64url(value: str, *, expected_length: int, label: str) -> bytes:
    try:
        encoded = value.encode("ascii")
        padded = encoded + b"=" * (-len(encoded) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise PrimeSentinelPqPoOAuthorizationError(f"invalid {label} encoding") from exc
    if len(decoded) != expected_length:
        raise PrimeSentinelPqPoOAuthorizationError(
            f"{label} must decode to {expected_length} bytes"
        )
    return decoded


class PrimeSentinelPqPoOVerifier:
    def __init__(
        self,
        *,
        public_keys_b64url: dict[str, str],
        revoked_key_ids: set[str] | None = None,
    ) -> None:
        self._public_keys: dict[str, bytes] = {}
        for key_id, encoded in public_keys_b64url.items():
            if not key_id:
                raise ValueError("PRIME SENTINEL PQ key id cannot be empty")
            self._public_keys[key_id] = _decode_b64url(
                encoded,
                expected_length=ML_DSA_65_PUBLIC_KEY_BYTES,
                label=f"ML-DSA-65 public key {key_id}",
            )
        self.revoked_key_ids = frozenset(revoked_key_ids or set())

    @property
    def configured(self) -> bool:
        return bool(self._public_keys)

    @classmethod
    def from_environment(cls) -> "PrimeSentinelPqPoOVerifier":
        raw_keys = os.getenv("PRIME_SENTINEL_PQ_PUBLIC_KEYS_JSON", "{}").strip() or "{}"
        try:
            parsed = json.loads(raw_keys)
        except json.JSONDecodeError as exc:
            raise RuntimeError("PRIME_SENTINEL_PQ_PUBLIC_KEYS_JSON is invalid JSON") from exc
        if not isinstance(parsed, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()
        ):
            raise RuntimeError(
                "PRIME_SENTINEL_PQ_PUBLIC_KEYS_JSON must be a string-to-string object"
            )
        revoked = {
            item.strip()
            for item in os.getenv("PRIME_SENTINEL_PQ_REVOKED_KEY_IDS", "").split(",")
            if item.strip()
        }
        try:
            return cls(public_keys_b64url=parsed, revoked_key_ids=revoked)
        except (ValueError, PrimeSentinelPqPoOAuthorizationError) as exc:
            raise RuntimeError(f"invalid PRIME SENTINEL PQ key configuration: {exc}") from exc

    def verify(
        self,
        assertion: PrimeSentinelPqPoOAuthorizationAssertion,
        *,
        now: datetime | None = None,
    ) -> VerifiedPrimeSentinelPqPoOAuthorization:
        if not self.configured:
            raise PrimeSentinelPqPoOAuthorizationError(
                "no PRIME SENTINEL PQ public keys are configured"
            )
        if assertion.key_id in self.revoked_key_ids:
            raise PrimeSentinelPqPoOAuthorizationError(
                "PRIME SENTINEL PQ signing key is revoked"
            )
        key_bytes = self._public_keys.get(assertion.key_id)
        if key_bytes is None:
            raise PrimeSentinelPqPoOAuthorizationError(
                "unknown PRIME SENTINEL PQ signing key"
            )

        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        issued = assertion.issued_at.astimezone(timezone.utc)
        expires = assertion.expires_at.astimezone(timezone.utc)
        if issued > current + MAX_FUTURE_SKEW:
            raise PrimeSentinelPqPoOAuthorizationError(
                "PQ authorization assertion is issued too far in the future"
            )
        if current >= expires:
            raise PrimeSentinelPqPoOAuthorizationError("PQ authorization assertion is expired")

        signature = _decode_b64url(
            assertion.signature_b64url,
            expected_length=ML_DSA_65_SIGNATURE_BYTES,
            label="ML-DSA-65 signature",
        )
        try:
            MLDSA65PublicKey.from_public_bytes(key_bytes).verify(
                signature,
                canonical_pq_poo_authorization_message(assertion),
                context=PRIME_SENTINEL_PQ_CONTEXT,
            )
        except (InvalidSignature, UnsupportedAlgorithm, ValueError) as exc:
            raise PrimeSentinelPqPoOAuthorizationError(
                "invalid PRIME SENTINEL PQ ML-DSA-65 signature"
            ) from exc

        return VerifiedPrimeSentinelPqPoOAuthorization(
            authorization_id=assertion.authorization_id,
            asset_id=assertion.asset_id,
            governance_projection_digest=assertion.governance_projection_digest,
            source_decision_digest=assertion.source_decision_digest,
            expected_registry_digest=assertion.expected_registry_digest,
            candidate_registry_digest=assertion.candidate_registry_digest,
            candidate_state_digest=assertion.candidate_state_digest,
            key_id=assertion.key_id,
            key_fingerprint_sha256=hashlib.sha256(key_bytes).hexdigest(),
            signed_assertion_sha256=signed_pq_poo_authorization_fingerprint(assertion),
            nonce=assertion.nonce,
            issued_at=issued,
            expires_at=expires,
        )


def _authorization_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise PrimeSentinelPqPoOAuthorizationError(
            f"{PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY} must be a JSON object"
        )
    return dict(raw)


def consumed_pq_poo_authorization_registry_patch(
    registry: dict[str, Any],
    *,
    verified: VerifiedPrimeSentinelPqPoOAuthorization,
    commit_id: str,
    consumed_at: datetime | None = None,
) -> dict[str, Any]:
    records = _authorization_map(registry)
    existing = records.get(verified.authorization_id)
    if existing is not None:
        if not isinstance(existing, dict):
            raise PrimeSentinelPqPoOAuthorizationError(
                "stored PQ PoO authorization is malformed"
            )
        same = (
            existing.get("status") == "CONSUMED"
            and existing.get("commit_id") == commit_id
            and existing.get("asset_id") == verified.asset_id
            and existing.get("governance_projection_digest") == verified.governance_projection_digest
            and existing.get("source_decision_digest") == verified.source_decision_digest
            and existing.get("expected_registry_digest") == verified.expected_registry_digest
            and existing.get("candidate_registry_digest") == verified.candidate_registry_digest
            and existing.get("candidate_state_digest") == verified.candidate_state_digest
            and existing.get("signed_assertion_sha256") == verified.signed_assertion_sha256
            and existing.get("nonce") == verified.nonce
            and existing.get("key_id") == verified.key_id
            and existing.get("algorithm") == PRIME_SENTINEL_PQ_ALGORITHM
            and existing.get("standard") == PRIME_SENTINEL_PQ_STANDARD
        )
        if same:
            return {PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY: records}
        raise PrimeSentinelPqPoOAuthorizationError(
            "PQ authorization_id is already bound to a different PoO commit"
        )

    for entry in records.values():
        if isinstance(entry, dict) and entry.get("nonce") == verified.nonce:
            raise PrimeSentinelPqPoOAuthorizationError(
                "PQ authorization nonce has already been consumed"
            )

    records[verified.authorization_id] = {
        "status": "CONSUMED",
        "algorithm": PRIME_SENTINEL_PQ_ALGORITHM,
        "standard": PRIME_SENTINEL_PQ_STANDARD,
        "signature_context": PRIME_SENTINEL_PQ_CONTEXT_TEXT,
        "action": PRIME_SENTINEL_PQ_POO_ACTION,
        "target_service": PRIME_SENTINEL_PQ_POO_TARGET_SERVICE,
        "target_environment": PRIME_SENTINEL_PQ_POO_TARGET_ENVIRONMENT,
        "commit_id": commit_id,
        "asset_id": verified.asset_id,
        "governance_projection_digest": verified.governance_projection_digest,
        "source_decision_digest": verified.source_decision_digest,
        "expected_registry_digest": verified.expected_registry_digest,
        "candidate_registry_digest": verified.candidate_registry_digest,
        "candidate_state_digest": verified.candidate_state_digest,
        "key_id": verified.key_id,
        "key_fingerprint_sha256": verified.key_fingerprint_sha256,
        "signed_assertion_sha256": verified.signed_assertion_sha256,
        "nonce": verified.nonce,
        "issued_at": _utc_iso(verified.issued_at),
        "expires_at": _utc_iso(verified.expires_at),
        "consumed_at": _utc_iso(consumed_at or datetime.now(timezone.utc)),
    }
    return {PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY: records}
