from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, model_validator


PRIME_ACTION_AUTHZ_SCHEMA = "WS-PRIME-ACTION-AUTHZ-V1"
PRIME_ACTION_AUTHZ_REGISTRY_KEY = "PRIME_ACTION_AUTHORIZATIONS"
MAX_ASSERTION_LIFETIME = timedelta(minutes=15)
MAX_FUTURE_SKEW = timedelta(seconds=60)

_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
_SAFE_ID_PATTERN = r"^[A-Za-z0-9._:-]{1,128}$"

ModelIdentifier = Annotated[str, Field(min_length=1, max_length=256)]
ToolIdentifier = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
]
ResourceIdentifier = Annotated[str, Field(min_length=1, max_length=512)]


class PrimeActionAuthorizationError(ValueError):
    pass


class PrimeActionAuthorizationAssertion(BaseModel):
    """Signed authority grant for one exact AI/action request.

    V1 is intentionally separate from WS-PRIME-SENTINEL-AUTHZ-V1, whose action
    semantics are limited to REQUALIFICATION_RELEASE. This contract is for
    bounded provider/tool execution and is fail-closed by default.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal[PRIME_ACTION_AUTHZ_SCHEMA] = PRIME_ACTION_AUTHZ_SCHEMA
    issuer: Literal["PRIME_SENTINEL"] = "PRIME_SENTINEL"
    key_id: str = Field(pattern=_SAFE_ID_PATTERN)
    authorization_id: str = Field(pattern=_SAFE_ID_PATTERN)
    action_id: str = Field(pattern=_SAFE_ID_PATTERN)
    prime_id: str = Field(pattern=_SAFE_ID_PATTERN)

    provider: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9._:-]+$")
    provider_operation: str = Field(
        min_length=1, max_length=128, pattern=r"^[A-Z0-9._:-]+$"
    )
    model_allowlist: list[ModelIdentifier] = Field(min_length=1, max_length=32)
    tool_allowlist: list[ToolIdentifier] = Field(default_factory=list, max_length=64)
    resource_scope: list[ResourceIdentifier] = Field(default_factory=list, max_length=64)

    requested_authority: int = Field(ge=0, le=1_000_000)
    reversible: bool
    side_effect_class: Literal[
        "READ_ONLY", "REVERSIBLE", "CONSEQUENTIAL", "IRREVERSIBLE"
    ]

    policy_id: str = Field(min_length=1, max_length=128)
    policy_sha256: str = Field(pattern=_SHA256_PATTERN)
    policy_disposition: Literal["AUTO_ELIGIBLE", "HUMAN_REVIEW_REQUIRED"]

    request_sha256: str = Field(pattern=_SHA256_PATTERN)
    human_approval_required: bool = False
    human_decision_id: str | None = Field(default=None, max_length=128)
    human_decision_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)

    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    signature_b64url: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_contract(self) -> "PrimeActionAuthorizationAssertion":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.expires_at - self.issued_at > MAX_ASSERTION_LIFETIME:
            raise ValueError("authorization lifetime exceeds 15 minutes")
        if len(set(self.model_allowlist)) != len(self.model_allowlist):
            raise ValueError("model_allowlist must not contain duplicates")
        if len(set(self.tool_allowlist)) != len(self.tool_allowlist):
            raise ValueError("tool_allowlist must not contain duplicates")
        if len(set(self.resource_scope)) != len(self.resource_scope):
            raise ValueError("resource_scope must not contain duplicates")
        if self.side_effect_class in {"READ_ONLY", "REVERSIBLE"} and not self.reversible:
            raise ValueError(f"{self.side_effect_class} authorization must be reversible")
        if self.side_effect_class == "IRREVERSIBLE" and self.reversible:
            raise ValueError("IRREVERSIBLE authorization cannot be reversible")
        review_required = self.policy_disposition == "HUMAN_REVIEW_REQUIRED"
        if review_required != self.human_approval_required:
            raise ValueError("policy disposition and human approval requirement must agree")
        if self.side_effect_class in {"CONSEQUENTIAL", "IRREVERSIBLE"} and not review_required:
            raise ValueError("consequential or irreversible execution requires human review")
        if self.human_approval_required:
            if not self.human_decision_id or not self.human_decision_sha256:
                raise ValueError(
                    "human approval requires human_decision_id and human_decision_sha256"
                )
        elif self.human_decision_id is not None or self.human_decision_sha256 is not None:
            raise ValueError("human decision evidence is only valid when approval is required")
        return self


class VerifiedPrimeActionAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_id: str = Field(pattern=_SAFE_ID_PATTERN)
    action_id: str = Field(pattern=_SAFE_ID_PATTERN)
    prime_id: str = Field(pattern=_SAFE_ID_PATTERN)
    provider: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9._:-]+$")
    provider_operation: str = Field(
        min_length=1, max_length=128, pattern=r"^[A-Z0-9._:-]+$"
    )
    model_allowlist: list[ModelIdentifier] = Field(min_length=1, max_length=32)
    tool_allowlist: list[ToolIdentifier] = Field(default_factory=list, max_length=64)
    resource_scope: list[ResourceIdentifier] = Field(default_factory=list, max_length=64)
    requested_authority: int = Field(ge=0, le=1_000_000)
    reversible: bool
    side_effect_class: Literal[
        "READ_ONLY", "REVERSIBLE", "CONSEQUENTIAL", "IRREVERSIBLE"
    ]
    policy_id: str = Field(min_length=1, max_length=128)
    policy_sha256: str = Field(pattern=_SHA256_PATTERN)
    policy_disposition: Literal["AUTO_ELIGIBLE", "HUMAN_REVIEW_REQUIRED"]
    request_sha256: str = Field(pattern=_SHA256_PATTERN)
    human_approval_required: bool
    human_decision_id: str | None = Field(default=None, max_length=128)
    human_decision_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    key_id: str = Field(pattern=_SAFE_ID_PATTERN)
    key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    nonce: str = Field(min_length=16, max_length=128)
    issued_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_contract(self) -> "VerifiedPrimeActionAuthorization":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.expires_at - self.issued_at > MAX_ASSERTION_LIFETIME:
            raise ValueError("authorization lifetime exceeds 15 minutes")
        if len(set(self.model_allowlist)) != len(self.model_allowlist):
            raise ValueError("model_allowlist must not contain duplicates")
        if len(set(self.tool_allowlist)) != len(self.tool_allowlist):
            raise ValueError("tool_allowlist must not contain duplicates")
        if len(set(self.resource_scope)) != len(self.resource_scope):
            raise ValueError("resource_scope must not contain duplicates")
        if self.side_effect_class in {"READ_ONLY", "REVERSIBLE"} and not self.reversible:
            raise ValueError(f"{self.side_effect_class} authorization must be reversible")
        if self.side_effect_class == "IRREVERSIBLE" and self.reversible:
            raise ValueError("IRREVERSIBLE authorization cannot be reversible")
        review_required = self.policy_disposition == "HUMAN_REVIEW_REQUIRED"
        if review_required != self.human_approval_required:
            raise ValueError("policy disposition and human approval requirement must agree")
        if self.side_effect_class in {"CONSEQUENTIAL", "IRREVERSIBLE"} and not review_required:
            raise ValueError("consequential or irreversible execution requires human review")
        if self.human_approval_required:
            if not self.human_decision_id or not self.human_decision_sha256:
                raise ValueError(
                    "human approval requires human_decision_id and human_decision_sha256"
                )
        elif self.human_decision_id is not None or self.human_decision_sha256 is not None:
            raise ValueError("human decision evidence is only valid when approval is required")
        return self


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_action_authorization_message(
    assertion: PrimeActionAuthorizationAssertion,
) -> bytes:
    payload = {
        "schema": assertion.schema,
        "issuer": assertion.issuer,
        "key_id": assertion.key_id,
        "authorization_id": assertion.authorization_id,
        "action_id": assertion.action_id,
        "prime_id": assertion.prime_id,
        "provider": assertion.provider,
        "provider_operation": assertion.provider_operation,
        "model_allowlist": assertion.model_allowlist,
        "tool_allowlist": assertion.tool_allowlist,
        "resource_scope": assertion.resource_scope,
        "requested_authority": assertion.requested_authority,
        "reversible": assertion.reversible,
        "side_effect_class": assertion.side_effect_class,
        "policy_id": assertion.policy_id,
        "policy_sha256": assertion.policy_sha256,
        "policy_disposition": assertion.policy_disposition,
        "request_sha256": assertion.request_sha256,
        "human_approval_required": assertion.human_approval_required,
        "human_decision_id": assertion.human_decision_id,
        "human_decision_sha256": assertion.human_decision_sha256,
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
        raise PrimeActionAuthorizationError(f"invalid {label} encoding") from exc
    if len(decoded) != expected_length:
        raise PrimeActionAuthorizationError(
            f"{label} must decode to {expected_length} bytes"
        )
    return decoded


class PrimeActionAuthorizationVerifier:
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
    def from_environment(cls) -> "PrimeActionAuthorizationVerifier":
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
        except (ValueError, PrimeActionAuthorizationError) as exc:
            raise RuntimeError(f"invalid PRIME SENTINEL key configuration: {exc}") from exc

    def verify(
        self,
        assertion: PrimeActionAuthorizationAssertion,
        *,
        now: datetime | None = None,
    ) -> VerifiedPrimeActionAuthorization:
        if not self.configured:
            raise PrimeActionAuthorizationError("no PRIME SENTINEL public keys are configured")
        if assertion.key_id in self.revoked_key_ids:
            raise PrimeActionAuthorizationError("PRIME SENTINEL signing key is revoked")
        key_bytes = self._public_keys.get(assertion.key_id)
        if key_bytes is None:
            raise PrimeActionAuthorizationError("unknown PRIME SENTINEL signing key")

        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        issued = assertion.issued_at.astimezone(timezone.utc)
        expires = assertion.expires_at.astimezone(timezone.utc)
        if issued > current + MAX_FUTURE_SKEW:
            raise PrimeActionAuthorizationError(
                "action authorization assertion is issued too far in the future"
            )
        if current >= expires:
            raise PrimeActionAuthorizationError("action authorization assertion is expired")

        signature = _decode_b64url(
            assertion.signature_b64url,
            expected_length=64,
            label="Ed25519 signature",
        )
        try:
            Ed25519PublicKey.from_public_bytes(key_bytes).verify(
                signature,
                canonical_action_authorization_message(assertion),
            )
        except (InvalidSignature, ValueError) as exc:
            raise PrimeActionAuthorizationError(
                "invalid PRIME SENTINEL Ed25519 signature"
            ) from exc

        return VerifiedPrimeActionAuthorization(
            authorization_id=assertion.authorization_id,
            action_id=assertion.action_id,
            prime_id=assertion.prime_id,
            provider=assertion.provider,
            provider_operation=assertion.provider_operation,
            model_allowlist=list(assertion.model_allowlist),
            tool_allowlist=list(assertion.tool_allowlist),
            resource_scope=list(assertion.resource_scope),
            requested_authority=assertion.requested_authority,
            reversible=assertion.reversible,
            side_effect_class=assertion.side_effect_class,
            policy_id=assertion.policy_id,
            policy_sha256=assertion.policy_sha256,
            policy_disposition=assertion.policy_disposition,
            request_sha256=assertion.request_sha256,
            human_approval_required=assertion.human_approval_required,
            human_decision_id=assertion.human_decision_id,
            human_decision_sha256=assertion.human_decision_sha256,
            key_id=assertion.key_id,
            key_fingerprint_sha256=hashlib.sha256(key_bytes).hexdigest(),
            nonce=assertion.nonce,
            issued_at=issued,
            expires_at=expires,
        )


def _authorization_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(PRIME_ACTION_AUTHZ_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise PrimeActionAuthorizationError(
            f"{PRIME_ACTION_AUTHZ_REGISTRY_KEY} must be a JSON object"
        )
    return dict(raw)


def verified_action_authorization_registry_patch(
    registry: dict[str, Any],
    verified: VerifiedPrimeActionAuthorization,
) -> dict[str, Any]:
    records = _authorization_map(registry)
    if verified.authorization_id in records:
        raise PrimeActionAuthorizationError("authorization_id has already been recorded")
    for entry in records.values():
        if isinstance(entry, dict) and entry.get("nonce") == verified.nonce:
            raise PrimeActionAuthorizationError("authorization nonce has already been recorded")
    records[verified.authorization_id] = {
        "status": "VERIFIED",
        **verified.model_dump(mode="json"),
    }
    return {PRIME_ACTION_AUTHZ_REGISTRY_KEY: records}


def assert_recorded_action_authorization_usable(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    action_id: str,
    request_sha256: str,
    verifier: PrimeActionAuthorizationVerifier,
    now: datetime | None = None,
) -> dict[str, Any]:
    records = _authorization_map(registry)
    entry = records.get(authorization_id)
    if not isinstance(entry, dict):
        raise PrimeActionAuthorizationError("action authorization is not recorded")
    if entry.get("status") != "VERIFIED":
        raise PrimeActionAuthorizationError("action authorization is not in VERIFIED state")
    if entry.get("action_id") != action_id:
        raise PrimeActionAuthorizationError("action authorization action identity mismatch")
    if entry.get("request_sha256") != request_sha256:
        raise PrimeActionAuthorizationError("action authorization request digest mismatch")
    key_id = entry.get("key_id")
    if not isinstance(key_id, str) or not verifier.key_is_configured(key_id):
        raise PrimeActionAuthorizationError("action authorization signing key is no longer configured")
    if verifier.key_is_revoked(key_id):
        raise PrimeActionAuthorizationError("action authorization signing key is revoked")
    try:
        expires = datetime.fromisoformat(str(entry["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise PrimeActionAuthorizationError("action authorization expiry is invalid") from exc
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current >= expires.astimezone(timezone.utc):
        raise PrimeActionAuthorizationError("action authorization is expired")
    return entry


def consumed_action_authorization_registry_patch(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    execution_id: str,
    consumed_at: datetime | None = None,
) -> dict[str, Any]:
    records = _authorization_map(registry)
    entry = records.get(authorization_id)
    if not isinstance(entry, dict):
        raise PrimeActionAuthorizationError("action authorization is not recorded")
    if entry.get("status") != "VERIFIED":
        raise PrimeActionAuthorizationError("action authorization cannot be consumed")
    if not execution_id:
        raise PrimeActionAuthorizationError("execution_id must be non-empty")
    when = (consumed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    updated = dict(entry)
    updated.update(
        {
            "status": "CONSUMED",
            "consumed_execution_id": execution_id,
            "consumed_at": _utc_iso(when),
        }
    )
    records[authorization_id] = updated
    return {PRIME_ACTION_AUTHZ_REGISTRY_KEY: records}
