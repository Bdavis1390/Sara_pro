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

from .fasa import (
    CapabilityLevel,
    CapabilityRegistryEntry,
    FrontierActionCandidate,
    FrontierDisposition,
    FrontierSafetyPolicy,
    evaluate_frontier_action,
)


FASA_APPROVAL_SCHEMA = "WS-FASA-APPROVAL-LEASE-V1"
FASA_APPROVAL_REGISTRY_KEY = "FASA_APPROVAL_LEASES"
MAX_FUTURE_SKEW = timedelta(seconds=60)
MAX_APPROVAL_SECONDS: dict[CapabilityLevel, int] = {
    CapabilityLevel.F0: 900,
    CapabilityLevel.F1: 900,
    CapabilityLevel.F2: 600,
    CapabilityLevel.F3: 120,
    CapabilityLevel.F4: 60,
    CapabilityLevel.F5: 0,
}


class FASAApprovalError(ValueError):
    pass


class FASAAssuranceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safety_case_id: str | None = Field(default=None, min_length=1, max_length=128)
    safety_case_current: bool = False
    independent_review_id: str | None = Field(default=None, min_length=1, max_length=128)
    independent_review_current: bool = False


class FASAApprovalLease(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema: Literal[FASA_APPROVAL_SCHEMA] = FASA_APPROVAL_SCHEMA
    issuer: Literal["PRIME_SENTINEL"] = "PRIME_SENTINEL"
    key_id: str = Field(min_length=1, max_length=128)
    authorization_id: str = Field(min_length=1, max_length=128)
    model_id: str = Field(min_length=1, max_length=128)
    model_version: str = Field(min_length=1, max_length=128)
    capability_level: CapabilityLevel
    action_id: str = Field(min_length=1, max_length=128)
    target_environment: str = Field(min_length=1, max_length=128)
    policy_id: str = Field(min_length=1, max_length=128)
    evaluation_id: str = Field(min_length=1, max_length=128)
    safety_case_id: str | None = Field(default=None, min_length=1, max_length=128)
    independent_review_id: str | None = Field(default=None, min_length=1, max_length=128)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    signature_b64url: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_window(self) -> "FASAApprovalLease":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        maximum_seconds = MAX_APPROVAL_SECONDS[self.capability_level]
        if maximum_seconds == 0:
            raise ValueError("F5 approval leases are disabled")
        if self.expires_at - self.issued_at > timedelta(seconds=maximum_seconds):
            raise ValueError(
                f"approval lease exceeds F{int(self.capability_level)} ceiling of {maximum_seconds} seconds"
            )
        return self


class VerifiedFASAApproval(BaseModel):
    authorization_id: str
    model_id: str
    model_version: str
    capability_level: CapabilityLevel
    action_id: str
    target_environment: str
    policy_id: str
    evaluation_id: str
    safety_case_id: str | None
    independent_review_id: str | None
    key_id: str
    key_fingerprint_sha256: str
    nonce: str
    issued_at: datetime
    expires_at: datetime


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_approval_message(lease: FASAApprovalLease) -> bytes:
    payload = {
        "schema": lease.schema,
        "issuer": lease.issuer,
        "key_id": lease.key_id,
        "authorization_id": lease.authorization_id,
        "model_id": lease.model_id,
        "model_version": lease.model_version,
        "capability_level": int(lease.capability_level),
        "action_id": lease.action_id,
        "target_environment": lease.target_environment,
        "policy_id": lease.policy_id,
        "evaluation_id": lease.evaluation_id,
        "safety_case_id": lease.safety_case_id,
        "independent_review_id": lease.independent_review_id,
        "issued_at": _utc_iso(lease.issued_at),
        "expires_at": _utc_iso(lease.expires_at),
        "nonce": lease.nonce,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _decode_b64url(value: str, *, expected_length: int, label: str) -> bytes:
    try:
        encoded = value.encode("ascii")
        padded = encoded + b"=" * (-len(encoded) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise FASAApprovalError(f"invalid {label} encoding") from exc
    if len(decoded) != expected_length:
        raise FASAApprovalError(f"{label} must decode to {expected_length} bytes")
    return decoded


class PrimeSentinelFASAApprovalVerifier:
    """Verify FASA approvals using the existing PRIME SENTINEL trust root."""

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

    @classmethod
    def from_environment(cls) -> "PrimeSentinelFASAApprovalVerifier":
        raw_keys = os.getenv("PRIME_SENTINEL_PUBLIC_KEYS_JSON", "{}").strip() or "{}"
        try:
            parsed = json.loads(raw_keys)
        except json.JSONDecodeError as exc:
            raise RuntimeError("PRIME_SENTINEL_PUBLIC_KEYS_JSON is invalid JSON") from exc
        if not isinstance(parsed, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in parsed.items()
        ):
            raise RuntimeError("PRIME_SENTINEL_PUBLIC_KEYS_JSON must be a string-to-string object")
        revoked = {
            item.strip()
            for item in os.getenv("PRIME_SENTINEL_REVOKED_KEY_IDS", "").split(",")
            if item.strip()
        }
        try:
            return cls(public_keys_b64url=parsed, revoked_key_ids=revoked)
        except (ValueError, FASAApprovalError) as exc:
            raise RuntimeError(f"invalid PRIME SENTINEL key configuration: {exc}") from exc

    def verify(
        self,
        lease: FASAApprovalLease,
        *,
        now: datetime | None = None,
    ) -> VerifiedFASAApproval:
        if not self._public_keys:
            raise FASAApprovalError("no PRIME SENTINEL public keys are configured")
        if lease.key_id in self.revoked_key_ids:
            raise FASAApprovalError("PRIME SENTINEL signing key is revoked")
        key_bytes = self._public_keys.get(lease.key_id)
        if key_bytes is None:
            raise FASAApprovalError("unknown PRIME SENTINEL signing key")

        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        issued = lease.issued_at.astimezone(timezone.utc)
        expires = lease.expires_at.astimezone(timezone.utc)
        if issued > current + MAX_FUTURE_SKEW:
            raise FASAApprovalError("approval lease is issued too far in the future")
        if current >= expires:
            raise FASAApprovalError("approval lease is expired")

        signature = _decode_b64url(
            lease.signature_b64url,
            expected_length=64,
            label="Ed25519 signature",
        )
        try:
            Ed25519PublicKey.from_public_bytes(key_bytes).verify(
                signature,
                canonical_approval_message(lease),
            )
        except (InvalidSignature, ValueError) as exc:
            raise FASAApprovalError("invalid PRIME SENTINEL Ed25519 signature") from exc

        return VerifiedFASAApproval(
            authorization_id=lease.authorization_id,
            model_id=lease.model_id,
            model_version=lease.model_version,
            capability_level=lease.capability_level,
            action_id=lease.action_id,
            target_environment=lease.target_environment,
            policy_id=lease.policy_id,
            evaluation_id=lease.evaluation_id,
            safety_case_id=lease.safety_case_id,
            independent_review_id=lease.independent_review_id,
            key_id=lease.key_id,
            key_fingerprint_sha256=hashlib.sha256(key_bytes).hexdigest(),
            nonce=lease.nonce,
            issued_at=issued,
            expires_at=expires,
        )


def _approval_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(FASA_APPROVAL_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise FASAApprovalError(f"{FASA_APPROVAL_REGISTRY_KEY} must be a JSON object")
    return dict(raw)


def verified_approval_registry_patch(
    registry: dict[str, Any],
    verified: VerifiedFASAApproval,
) -> dict[str, Any]:
    records = _approval_map(registry)
    if verified.authorization_id in records:
        raise FASAApprovalError("authorization_id has already been recorded")
    for entry in records.values():
        if isinstance(entry, dict) and entry.get("nonce") == verified.nonce:
            raise FASAApprovalError("approval nonce has already been recorded")
    records[verified.authorization_id] = {
        "status": "VERIFIED",
        "model_id": verified.model_id,
        "model_version": verified.model_version,
        "capability_level": int(verified.capability_level),
        "action_id": verified.action_id,
        "policy_id": verified.policy_id,
        "evaluation_id": verified.evaluation_id,
        "key_id": verified.key_id,
        "key_fingerprint_sha256": verified.key_fingerprint_sha256,
        "nonce": verified.nonce,
        "issued_at": _utc_iso(verified.issued_at),
        "expires_at": _utc_iso(verified.expires_at),
    }
    return {FASA_APPROVAL_REGISTRY_KEY: records}


def assert_recorded_approval_usable(
    registry: dict[str, Any],
    *,
    verified: VerifiedFASAApproval,
    now: datetime | None = None,
) -> dict[str, Any]:
    records = _approval_map(registry)
    entry = records.get(verified.authorization_id)
    if not isinstance(entry, dict):
        raise FASAApprovalError("approval lease is not recorded")
    if entry.get("status") != "VERIFIED":
        raise FASAApprovalError("approval lease is not in VERIFIED state")
    if entry.get("nonce") != verified.nonce:
        raise FASAApprovalError("approval lease nonce mismatch")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if current >= verified.expires_at.astimezone(timezone.utc):
        raise FASAApprovalError("approval lease is expired")
    return entry


def consumed_approval_registry_patch(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    transition_id: str,
    consumed_at: datetime | None = None,
) -> dict[str, Any]:
    records = _approval_map(registry)
    entry = records.get(authorization_id)
    if not isinstance(entry, dict) or entry.get("status") != "VERIFIED":
        raise FASAApprovalError("approval lease cannot be consumed")
    updated = dict(entry)
    updated.update(
        {
            "status": "CONSUMED",
            "consumed_transition_id": transition_id,
            "consumed_at": _utc_iso(consumed_at or datetime.now(timezone.utc)),
        }
    )
    records[authorization_id] = updated
    return {FASA_APPROVAL_REGISTRY_KEY: records}


def _approval_required(candidate: FrontierActionCandidate, policy: FrontierSafetyPolicy) -> bool:
    return bool(
        candidate.capability_level >= policy.human_review_level
        or (policy.require_human_for_irreversible and not candidate.reversible)
        or (
            policy.require_human_for_consequential_external_effect
            and candidate.consequential_external_effect
        )
        or candidate.capability_level > policy.maximum_automatic_level
    )


def evaluate_frontier_action_with_approval(
    candidate: FrontierActionCandidate,
    registry: CapabilityRegistryEntry,
    policy: FrontierSafetyPolicy,
    *,
    target_environment: str,
    assurance: FASAAssuranceEvidence | None = None,
    lease: FASAApprovalLease | None = None,
    verifier: PrimeSentinelFASAApprovalVerifier | None = None,
    approval_registry: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> tuple[FrontierDisposition, list[str], VerifiedFASAApproval | None]:
    """Execution-authoritative gate that ignores candidate-supplied approval flags."""

    assurance = assurance or FASAAssuranceEvidence()
    required = _approval_required(candidate, policy)

    if not required:
        sanitized = candidate.model_copy(
            update={
                "human_approval_present": False,
                "safety_case_current": assurance.safety_case_current,
                "independent_review_current": assurance.independent_review_current,
            }
        )
        disposition, reasons = evaluate_frontier_action(sanitized, registry, policy)
        return disposition, reasons, None

    if lease is None or verifier is None:
        sanitized = candidate.model_copy(
            update={
                "human_approval_present": False,
                "safety_case_current": False,
                "independent_review_current": False,
            }
        )
        disposition, reasons = evaluate_frontier_action(sanitized, registry, policy)
        return disposition, reasons, None

    try:
        verified = verifier.verify(lease, now=now)
    except FASAApprovalError as exc:
        return FrontierDisposition.DENIED, [str(exc)], None

    binding_failures: list[str] = []
    if verified.model_id != candidate.model_id or verified.model_version != candidate.model_version:
        binding_failures.append("approval model identity/version does not match candidate")
    if verified.capability_level != candidate.capability_level:
        binding_failures.append("approval capability level does not exactly match candidate")
    if verified.action_id != candidate.action_id:
        binding_failures.append("approval action identity does not match candidate")
    if verified.target_environment != target_environment:
        binding_failures.append("approval target environment does not match request")
    if verified.policy_id != policy.policy_id:
        binding_failures.append("approval policy identity does not match active policy")
    if verified.evaluation_id != registry.evaluation_id:
        binding_failures.append("approval evaluation identity does not match registry")

    if candidate.capability_level >= policy.safety_case_level:
        if not assurance.safety_case_current or not assurance.safety_case_id:
            binding_failures.append("current safety-case evidence is required")
        elif verified.safety_case_id != assurance.safety_case_id:
            binding_failures.append("approval safety-case identity does not match current evidence")

    if candidate.capability_level >= policy.independent_review_level:
        if not assurance.independent_review_current or not assurance.independent_review_id:
            binding_failures.append("current independent-review evidence is required")
        elif verified.independent_review_id != assurance.independent_review_id:
            binding_failures.append("approval independent-review identity does not match current evidence")

    if binding_failures:
        return FrontierDisposition.DENIED, binding_failures, None

    if approval_registry is not None:
        try:
            assert_recorded_approval_usable(approval_registry, verified=verified, now=now)
        except FASAApprovalError as exc:
            return FrontierDisposition.DENIED, [str(exc)], None

    sanitized = candidate.model_copy(
        update={
            "human_approval_present": True,
            "safety_case_current": assurance.safety_case_current,
            "independent_review_current": assurance.independent_review_current,
        }
    )
    disposition, reasons = evaluate_frontier_action(sanitized, registry, policy)
    return disposition, reasons, verified
