from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .prime_configuration_custody import PrimeEnvironment


OVERWATCH_CONTAINMENT_SCHEMA = "WS-OVERWATCH-CONTAINMENT-V1"
OVERWATCH_CONTAINMENT_RECORD_SCHEMA = "WS-OVERWATCH-CONTAINMENT-RECORD-V1"
OVERWATCH_CONTAINMENT_REGISTRY_KEY = "OVERWATCH_CONTAINMENT"
MAX_DIRECTIVE_ISSUANCE_WINDOW = timedelta(minutes=15)
MAX_FUTURE_SKEW = timedelta(seconds=60)
DEFAULT_HOLD_QUORUM = 1
DEFAULT_CLEAR_QUORUM = 2


class OverwatchContainmentError(ValueError):
    pass


class OverwatchContainmentState(str, Enum):
    HOLD = "HOLD"
    CLEAR = "CLEAR"


class OverwatchDirectiveSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str = Field(min_length=1, max_length=128)
    signature_b64url: str = Field(min_length=1, max_length=256)


class OverwatchContainmentDirective(BaseModel):
    """Signed, sequence-bound OVERWATCH containment state transition.

    HOLD is fail-safe authority: by default one configured key is sufficient.
    CLEAR is recovery authority: by default two distinct configured keys must
    sign the same directive. Quorums are verifier configuration, not caller
    supplied data.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[OVERWATCH_CONTAINMENT_SCHEMA] = OVERWATCH_CONTAINMENT_SCHEMA
    issuer: Literal["OVERWATCH"] = "OVERWATCH"
    directive_id: str = Field(min_length=1, max_length=128)
    prime_id: str = Field(min_length=1, max_length=128)
    action: Literal["REQUALIFICATION_RELEASE"] = "REQUALIFICATION_RELEASE"
    target_environment: PrimeEnvironment
    state: OverwatchContainmentState
    sequence: int = Field(ge=1)
    previous_directive_sha256: str | None = Field(default=None, max_length=64)
    reason_code: str = Field(min_length=1, max_length=128, pattern=r"^[A-Z0-9_.:-]+$")
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    signatures: list[OverwatchDirectiveSignature] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def validate_window_and_chain_shape(self) -> "OverwatchContainmentDirective":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.expires_at - self.issued_at > MAX_DIRECTIVE_ISSUANCE_WINDOW:
            raise ValueError("OVERWATCH directive issuance window exceeds 15 minutes")
        if self.sequence == 1 and self.previous_directive_sha256 is not None:
            raise ValueError("first OVERWATCH directive must not name a predecessor")
        if self.sequence > 1:
            if self.previous_directive_sha256 is None:
                raise ValueError("chained OVERWATCH directive must name its predecessor")
            if len(self.previous_directive_sha256) != 64:
                raise ValueError("previous_directive_sha256 must be a SHA-256 hex digest")
            try:
                bytes.fromhex(self.previous_directive_sha256)
            except ValueError as exc:
                raise ValueError("previous_directive_sha256 must be hexadecimal") from exc
        key_ids = [signature.key_id for signature in self.signatures]
        if len(key_ids) != len(set(key_ids)):
            raise ValueError("OVERWATCH directive signatures must use distinct key IDs")
        return self


class VerifiedOverwatchDirective(BaseModel):
    model_config = ConfigDict(extra="forbid")

    directive_id: str
    prime_id: str
    action: str
    target_environment: PrimeEnvironment
    state: OverwatchContainmentState
    sequence: int
    previous_directive_sha256: str | None
    reason_code: str
    issued_at: datetime
    expires_at: datetime
    nonce: str
    signer_key_ids: list[str]
    signer_fingerprints_sha256: dict[str, str]
    directive_sha256: str


class OverwatchContainmentStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool
    prime_id: str
    action: str
    target_environment: PrimeEnvironment
    state: OverwatchContainmentState | None = None
    sequence: int = 0
    directive_id: str | None = None
    directive_sha256: str | None = None
    reason_code: str | None = None
    signer_key_ids: list[str] = Field(default_factory=list)

    @property
    def snapshot_sha256(self) -> str:
        payload = self.model_dump(mode="json")
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_overwatch_message(directive: OverwatchContainmentDirective) -> bytes:
    payload = {
        "schema": directive.schema,
        "issuer": directive.issuer,
        "directive_id": directive.directive_id,
        "prime_id": directive.prime_id,
        "action": directive.action,
        "target_environment": directive.target_environment.value,
        "state": directive.state.value,
        "sequence": directive.sequence,
        "previous_directive_sha256": directive.previous_directive_sha256,
        "reason_code": directive.reason_code,
        "issued_at": _utc_iso(directive.issued_at),
        "expires_at": _utc_iso(directive.expires_at),
        "nonce": directive.nonce,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _signed_directive_sha256(directive: OverwatchContainmentDirective) -> str:
    signatures = sorted(
        (
            {
                "key_id": signature.key_id,
                "signature_b64url": signature.signature_b64url,
            }
            for signature in directive.signatures
        ),
        key=lambda item: item["key_id"],
    )
    material = {
        "message": json.loads(canonical_overwatch_message(directive).decode("utf-8")),
        "signatures": signatures,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _decode_b64url(value: str, *, expected_length: int, label: str) -> bytes:
    try:
        encoded = value.encode("ascii")
        padded = encoded + b"=" * (-len(encoded) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise OverwatchContainmentError(f"invalid {label} encoding") from exc
    if len(decoded) != expected_length:
        raise OverwatchContainmentError(
            f"{label} must decode to {expected_length} bytes"
        )
    return decoded


def _parse_quorum(raw: str, *, env_name: str, default: int) -> int:
    value = raw.strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{env_name} must be an integer") from exc
    if parsed < 1 or parsed > 16:
        raise RuntimeError(f"{env_name} must be between 1 and 16")
    return parsed


class OverwatchContainmentVerifier:
    def __init__(
        self,
        *,
        public_keys_b64url: dict[str, str],
        revoked_key_ids: set[str] | None = None,
        hold_quorum: int = DEFAULT_HOLD_QUORUM,
        clear_quorum: int = DEFAULT_CLEAR_QUORUM,
    ) -> None:
        if hold_quorum < 1 or clear_quorum < 1:
            raise ValueError("OVERWATCH quorums must be positive")
        if hold_quorum > 16 or clear_quorum > 16:
            raise ValueError("OVERWATCH quorums must not exceed 16")

        self._public_keys: dict[str, bytes] = {}
        for key_id, encoded in public_keys_b64url.items():
            if not key_id:
                raise ValueError("OVERWATCH key id cannot be empty")
            self._public_keys[key_id] = _decode_b64url(
                encoded,
                expected_length=32,
                label=f"OVERWATCH public key {key_id}",
            )
        self.revoked_key_ids = frozenset(revoked_key_ids or set())
        self.hold_quorum = hold_quorum
        self.clear_quorum = clear_quorum

    @property
    def configured(self) -> bool:
        return bool(self._public_keys)

    @classmethod
    def from_environment(cls) -> "OverwatchContainmentVerifier":
        raw_keys = os.getenv("OVERWATCH_CONTAINMENT_PUBLIC_KEYS_JSON", "{}").strip() or "{}"
        try:
            parsed = json.loads(raw_keys)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OVERWATCH_CONTAINMENT_PUBLIC_KEYS_JSON is invalid JSON") from exc
        if not isinstance(parsed, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in parsed.items()
        ):
            raise RuntimeError(
                "OVERWATCH_CONTAINMENT_PUBLIC_KEYS_JSON must be a string-to-string object"
            )
        revoked = {
            item.strip()
            for item in os.getenv("OVERWATCH_CONTAINMENT_REVOKED_KEY_IDS", "").split(",")
            if item.strip()
        }
        try:
            return cls(
                public_keys_b64url=parsed,
                revoked_key_ids=revoked,
                hold_quorum=_parse_quorum(
                    os.getenv("OVERWATCH_CONTAINMENT_HOLD_QUORUM", ""),
                    env_name="OVERWATCH_CONTAINMENT_HOLD_QUORUM",
                    default=DEFAULT_HOLD_QUORUM,
                ),
                clear_quorum=_parse_quorum(
                    os.getenv("OVERWATCH_CONTAINMENT_CLEAR_QUORUM", ""),
                    env_name="OVERWATCH_CONTAINMENT_CLEAR_QUORUM",
                    default=DEFAULT_CLEAR_QUORUM,
                ),
            )
        except (ValueError, OverwatchContainmentError) as exc:
            raise RuntimeError(f"invalid OVERWATCH containment configuration: {exc}") from exc

    def _required_quorum(self, state: OverwatchContainmentState) -> int:
        return self.hold_quorum if state == OverwatchContainmentState.HOLD else self.clear_quorum

    def verify(
        self,
        directive: OverwatchContainmentDirective,
        *,
        now: datetime | None = None,
        enforce_issuance_window: bool = True,
    ) -> VerifiedOverwatchDirective:
        if not self.configured:
            raise OverwatchContainmentError("no OVERWATCH containment public keys are configured")

        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        issued = directive.issued_at.astimezone(timezone.utc)
        expires = directive.expires_at.astimezone(timezone.utc)
        if issued > current + MAX_FUTURE_SKEW:
            raise OverwatchContainmentError("OVERWATCH directive is issued too far in the future")
        if enforce_issuance_window and current >= expires:
            raise OverwatchContainmentError("OVERWATCH directive issuance window is expired")

        message = canonical_overwatch_message(directive)
        verified_ids: list[str] = []
        fingerprints: dict[str, str] = {}
        for signature in directive.signatures:
            if signature.key_id in self.revoked_key_ids:
                raise OverwatchContainmentError("OVERWATCH signing key is revoked")
            key_bytes = self._public_keys.get(signature.key_id)
            if key_bytes is None:
                raise OverwatchContainmentError("unknown OVERWATCH signing key")
            raw_signature = _decode_b64url(
                signature.signature_b64url,
                expected_length=64,
                label=f"OVERWATCH signature {signature.key_id}",
            )
            try:
                Ed25519PublicKey.from_public_bytes(key_bytes).verify(
                    raw_signature,
                    message,
                )
            except (InvalidSignature, ValueError) as exc:
                raise OverwatchContainmentError("invalid OVERWATCH Ed25519 signature") from exc
            verified_ids.append(signature.key_id)
            fingerprints[signature.key_id] = hashlib.sha256(key_bytes).hexdigest()

        required = self._required_quorum(directive.state)
        if len(verified_ids) < required:
            raise OverwatchContainmentError(
                f"OVERWATCH {directive.state.value} directive requires {required} distinct signatures"
            )

        return VerifiedOverwatchDirective(
            directive_id=directive.directive_id,
            prime_id=directive.prime_id,
            action=directive.action,
            target_environment=directive.target_environment,
            state=directive.state,
            sequence=directive.sequence,
            previous_directive_sha256=directive.previous_directive_sha256,
            reason_code=directive.reason_code,
            issued_at=issued,
            expires_at=expires,
            nonce=directive.nonce,
            signer_key_ids=sorted(verified_ids),
            signer_fingerprints_sha256=dict(sorted(fingerprints.items())),
            directive_sha256=_signed_directive_sha256(directive),
        )


def _containment_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(OVERWATCH_CONTAINMENT_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise OverwatchContainmentError(
            f"{OVERWATCH_CONTAINMENT_REGISTRY_KEY} must be a JSON object"
        )
    return dict(raw)


def _record_to_verified(
    *,
    prime_id: str,
    record: Any,
    verifier: OverwatchContainmentVerifier,
    now: datetime | None = None,
) -> VerifiedOverwatchDirective:
    if not isinstance(record, dict):
        raise OverwatchContainmentError("OVERWATCH containment record is malformed")
    if record.get("schema") != OVERWATCH_CONTAINMENT_RECORD_SCHEMA:
        raise OverwatchContainmentError("OVERWATCH containment record schema is invalid")
    if record.get("prime_id") != prime_id:
        raise OverwatchContainmentError("OVERWATCH containment registry identity mismatch")
    raw_assertion = record.get("directive")
    if not isinstance(raw_assertion, dict):
        raise OverwatchContainmentError("OVERWATCH containment record is missing signed directive")
    try:
        directive = OverwatchContainmentDirective.model_validate(raw_assertion)
    except ValueError as exc:
        raise OverwatchContainmentError("stored OVERWATCH directive is malformed") from exc

    verified = verifier.verify(
        directive,
        now=now,
        enforce_issuance_window=False,
    )
    expected = {
        "directive_id": verified.directive_id,
        "prime_id": verified.prime_id,
        "action": verified.action,
        "target_environment": verified.target_environment.value,
        "state": verified.state.value,
        "sequence": verified.sequence,
        "previous_directive_sha256": verified.previous_directive_sha256,
        "reason_code": verified.reason_code,
        "nonce": verified.nonce,
        "signer_key_ids": verified.signer_key_ids,
        "signer_fingerprints_sha256": verified.signer_fingerprints_sha256,
        "directive_sha256": verified.directive_sha256,
    }
    for key, expected_value in expected.items():
        if record.get(key) != expected_value:
            raise OverwatchContainmentError(
                f"stored OVERWATCH containment {key} does not match signed directive"
            )
    return verified


def verified_containment_registry_patch(
    registry: dict[str, Any],
    directive: OverwatchContainmentDirective,
    *,
    verifier: OverwatchContainmentVerifier,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply one signed HOLD/CLEAR directive to a sequence-bound PRIME record."""

    verified = verifier.verify(directive, now=now, enforce_issuance_window=True)
    records = _containment_map(registry)
    current = records.get(verified.prime_id)

    if current is None:
        if verified.sequence != 1 or verified.previous_directive_sha256 is not None:
            raise OverwatchContainmentError(
                "first OVERWATCH containment directive must start at sequence 1"
            )
    else:
        prior = _record_to_verified(
            prime_id=verified.prime_id,
            record=current,
            verifier=verifier,
            now=now,
        )
        if verified.sequence != prior.sequence + 1:
            raise OverwatchContainmentError("OVERWATCH containment sequence is not monotonic")
        if verified.previous_directive_sha256 != prior.directive_sha256:
            raise OverwatchContainmentError("OVERWATCH containment predecessor hash mismatch")
        if verified.action != prior.action:
            raise OverwatchContainmentError("OVERWATCH containment action cannot change within chain")
        if verified.target_environment != prior.target_environment:
            raise OverwatchContainmentError(
                "OVERWATCH containment target environment cannot change within chain"
            )

    records[verified.prime_id] = {
        "schema": OVERWATCH_CONTAINMENT_RECORD_SCHEMA,
        "directive_id": verified.directive_id,
        "prime_id": verified.prime_id,
        "action": verified.action,
        "target_environment": verified.target_environment.value,
        "state": verified.state.value,
        "sequence": verified.sequence,
        "previous_directive_sha256": verified.previous_directive_sha256,
        "reason_code": verified.reason_code,
        "nonce": verified.nonce,
        "signer_key_ids": verified.signer_key_ids,
        "signer_fingerprints_sha256": verified.signer_fingerprints_sha256,
        "directive_sha256": verified.directive_sha256,
        "issued_at": _utc_iso(verified.issued_at),
        "accepted_at": _utc_iso((now or datetime.now(timezone.utc)).astimezone(timezone.utc)),
        "directive": directive.model_dump(mode="json"),
    }
    return {OVERWATCH_CONTAINMENT_REGISTRY_KEY: records}


def evaluate_overwatch_containment(
    registry: dict[str, Any],
    *,
    prime_id: str,
    action: str,
    target_environment: PrimeEnvironment,
    verifier: OverwatchContainmentVerifier | None,
    now: datetime | None = None,
) -> OverwatchContainmentStatus:
    """Resolve the current signed OVERWATCH state for one consequential action.

    Missing containment state means no OVERWATCH veto has been recorded. Once a
    containment record exists for the PRIME, however, a verifier is mandatory
    and malformed, tampered, revoked-key, or mismatched state fails closed.
    """

    records = _containment_map(registry)
    record = records.get(prime_id)
    if record is None:
        return OverwatchContainmentStatus(
            active=False,
            prime_id=prime_id,
            action=action,
            target_environment=target_environment,
        )
    if verifier is None:
        raise OverwatchContainmentError(
            "OVERWATCH containment verifier is required for persisted containment state"
        )

    verified = _record_to_verified(
        prime_id=prime_id,
        record=record,
        verifier=verifier,
        now=now,
    )
    if verified.action != action:
        raise OverwatchContainmentError("OVERWATCH containment action mismatch")
    if verified.target_environment != target_environment:
        # A containment chain is target-environment-specific. A valid directive
        # for another environment is not silently re-scoped by the caller.
        return OverwatchContainmentStatus(
            active=False,
            prime_id=prime_id,
            action=action,
            target_environment=target_environment,
            state=verified.state,
            sequence=verified.sequence,
            directive_id=verified.directive_id,
            directive_sha256=verified.directive_sha256,
            reason_code=verified.reason_code,
            signer_key_ids=verified.signer_key_ids,
        )

    return OverwatchContainmentStatus(
        active=verified.state == OverwatchContainmentState.HOLD,
        prime_id=prime_id,
        action=action,
        target_environment=target_environment,
        state=verified.state,
        sequence=verified.sequence,
        directive_id=verified.directive_id,
        directive_sha256=verified.directive_sha256,
        reason_code=verified.reason_code,
        signer_key_ids=verified.signer_key_ids,
    )
