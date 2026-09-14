from __future__ import annotations

import base64
import binascii
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .qualification import CapabilityStatus, EvidenceScope
from .sovereign_boundary_kernel import (
    BoundaryAction,
    BoundaryDisposition,
    BoundaryKernelError,
    BoundaryPolicyDecision,
    SovereignBoundaryEnvelope,
    bind_prime_authorization_reference,
    boundary_action_digest,
    verify_boundary_envelope,
)


OPA_BOUND_DECISION_SCHEMA = "WS-OPA-BOUND-DECISION-V0.1"
PRIME_EFFECT_AUTHZ_SCHEMA = "WS-PRIME-SENTINEL-EFFECT-AUTHZ-V0.1"
MAX_EFFECT_AUTHORIZATION_LIFETIME = timedelta(minutes=15)
MAX_FUTURE_SKEW = timedelta(seconds=60)


class OpaPolicyAdapterError(ValueError):
    pass


class PrimeEffectAuthorizationError(ValueError):
    pass


class OpaPolicyRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package: str = Field(min_length=1, max_length=128)
    revision: str = Field(min_length=1, max_length=256)


class OpaRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    human_approval: bool = False
    mfa: bool = False


class OpaAuditDirective(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: str | None = Field(default=None, max_length=32)
    retain: bool = True


class OpaBoundDecision(BaseModel):
    """A PEP-facing decision envelope that binds OPA's decision to one exact action."""

    model_config = ConfigDict(extra="forbid")

    schema: Literal[OPA_BOUND_DECISION_SCHEMA] = OPA_BOUND_DECISION_SCHEMA
    decision: Literal["allow", "deny", "escalate", "audit_only"]
    reason: str = Field(min_length=1, max_length=1024)
    decision_id: str = Field(min_length=1, max_length=128)
    policy: OpaPolicyRef
    requirements: OpaRequirements = Field(default_factory=OpaRequirements)
    constraints: dict[str, Any] = Field(default_factory=dict)
    audit: OpaAuditDirective = Field(default_factory=OpaAuditDirective)
    action_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def boundary_policy_from_opa(
    decision: OpaBoundDecision,
    action: BoundaryAction,
    *,
    satisfied_requirements: set[str] | None = None,
    constraints_satisfied: bool = False,
) -> BoundaryPolicyDecision:
    """Convert a bound OPA result into the SBK policy contract.

    Human approval is intentionally *not* considered satisfied here; SBK moves
    the envelope into AWAITING_HUMAN_APPROVAL and records the later approval.
    Other external requirements must be explicitly declared satisfied by the
    PEP, and returned constraints must be enforced before the decision is used.
    """

    if decision.action_digest != boundary_action_digest(action):
        raise OpaPolicyAdapterError(
            "OPA decision action_digest does not match the proposed SBK action"
        )

    satisfied = satisfied_requirements or set()
    required_external: list[str] = []
    if decision.requirements.mfa:
        required_external.append("mfa")
    missing = sorted(item for item in required_external if item not in satisfied)
    if missing:
        raise OpaPolicyAdapterError(
            f"OPA requirements are not satisfied: {', '.join(missing)}"
        )
    if decision.constraints and not constraints_satisfied:
        raise OpaPolicyAdapterError(
            "OPA returned constraints that have not been enforced by the PEP"
        )

    disposition = {
        "allow": BoundaryDisposition.ALLOW,
        "deny": BoundaryDisposition.DENY,
        "escalate": BoundaryDisposition.ESCALATE,
        "audit_only": BoundaryDisposition.AUDIT_ONLY,
    }[decision.decision]
    human_required = decision.requirements.human_approval or decision.decision == "escalate"

    requirements: list[str] = []
    if decision.requirements.human_approval:
        requirements.append("human_approval")
    if decision.requirements.mfa:
        requirements.append("mfa")
    requirements.extend(f"constraint:{name}" for name in sorted(decision.constraints))

    return BoundaryPolicyDecision(
        disposition=disposition,
        policy_revision=decision.policy.revision,
        decided_by=f"OPA:{decision.policy.package}",
        human_approval_required=human_required,
        requirements=tuple(requirements),
        reasons=(f"decision_id={decision.decision_id}", decision.reason),
    )


class PrimeEffectAuthorizationAssertion(BaseModel):
    """Short-lived PRIME SENTINEL authorization for one sealed SBK effect."""

    model_config = ConfigDict(extra="forbid")

    schema: Literal[PRIME_EFFECT_AUTHZ_SCHEMA] = PRIME_EFFECT_AUTHZ_SCHEMA
    issuer: Literal["PRIME_SENTINEL"] = "PRIME_SENTINEL"
    key_id: str = Field(min_length=1, max_length=128)
    authorization_id: str = Field(min_length=1, max_length=128)
    envelope_id: str = Field(min_length=1, max_length=128)
    actor: str = Field(min_length=1, max_length=128)
    action_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    effect_scope: EvidenceScope
    capability_status: CapabilityStatus
    policy_revision: str = Field(min_length=1, max_length=256)
    human_approval_ref: str | None = Field(default=None, min_length=1, max_length=512)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    signature_b64url: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_window(self) -> "PrimeEffectAuthorizationAssertion":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.expires_at - self.issued_at > MAX_EFFECT_AUTHORIZATION_LIFETIME:
            raise ValueError("effect authorization lifetime exceeds 15 minutes")
        return self


class VerifiedPrimeEffectAuthorization(BaseModel):
    authorization_id: str
    envelope_id: str
    actor: str
    action_digest: str
    effect_scope: EvidenceScope
    capability_status: CapabilityStatus
    policy_revision: str
    human_approval_ref: str | None
    key_id: str
    key_fingerprint_sha256: str
    nonce: str
    issued_at: datetime
    expires_at: datetime


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_prime_effect_authorization_message(
    assertion: PrimeEffectAuthorizationAssertion,
) -> bytes:
    payload = {
        "schema": assertion.schema,
        "issuer": assertion.issuer,
        "key_id": assertion.key_id,
        "authorization_id": assertion.authorization_id,
        "envelope_id": assertion.envelope_id,
        "actor": assertion.actor,
        "action_digest": assertion.action_digest,
        "effect_scope": assertion.effect_scope.value,
        "capability_status": assertion.capability_status.value,
        "policy_revision": assertion.policy_revision,
        "human_approval_ref": assertion.human_approval_ref,
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
        raise PrimeEffectAuthorizationError(f"invalid {label} encoding") from exc
    if len(decoded) != expected_length:
        raise PrimeEffectAuthorizationError(
            f"{label} must decode to {expected_length} bytes"
        )
    return decoded


class PrimeEffectAuthorizationVerifier:
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

    def verify_for_envelope(
        self,
        assertion: PrimeEffectAuthorizationAssertion,
        envelope: SovereignBoundaryEnvelope,
        *,
        now: datetime | None = None,
    ) -> VerifiedPrimeEffectAuthorization:
        if not verify_boundary_envelope(envelope):
            raise PrimeEffectAuthorizationError("SBK envelope failed digest verification")
        if assertion.key_id in self.revoked_key_ids:
            raise PrimeEffectAuthorizationError("PRIME SENTINEL signing key is revoked")
        key_bytes = self._public_keys.get(assertion.key_id)
        if key_bytes is None:
            raise PrimeEffectAuthorizationError("unknown PRIME SENTINEL signing key")

        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        issued = assertion.issued_at.astimezone(timezone.utc)
        expires = assertion.expires_at.astimezone(timezone.utc)
        if issued > current + MAX_FUTURE_SKEW:
            raise PrimeEffectAuthorizationError("effect authorization is issued too far in the future")
        if current >= expires:
            raise PrimeEffectAuthorizationError("effect authorization is expired")

        expected = {
            "envelope_id": envelope.envelope_id,
            "actor": envelope.actor,
            "action_digest": envelope.action_digest,
            "effect_scope": envelope.action.effect_scope,
            "capability_status": envelope.action.capability_status,
            "policy_revision": envelope.policy.policy_revision,
            "human_approval_ref": envelope.human_approval_ref,
        }
        observed = {
            "envelope_id": assertion.envelope_id,
            "actor": assertion.actor,
            "action_digest": assertion.action_digest,
            "effect_scope": assertion.effect_scope,
            "capability_status": assertion.capability_status,
            "policy_revision": assertion.policy_revision,
            "human_approval_ref": assertion.human_approval_ref,
        }
        mismatches = [name for name in expected if expected[name] != observed[name]]
        if mismatches:
            raise PrimeEffectAuthorizationError(
                "PRIME effect authorization binding mismatch: " + ", ".join(sorted(mismatches))
            )

        signature = _decode_b64url(
            assertion.signature_b64url,
            expected_length=64,
            label="Ed25519 signature",
        )
        try:
            Ed25519PublicKey.from_public_bytes(key_bytes).verify(
                signature,
                canonical_prime_effect_authorization_message(assertion),
            )
        except (InvalidSignature, ValueError) as exc:
            raise PrimeEffectAuthorizationError(
                "invalid PRIME SENTINEL effect-authorization signature"
            ) from exc

        return VerifiedPrimeEffectAuthorization(
            authorization_id=assertion.authorization_id,
            envelope_id=assertion.envelope_id,
            actor=assertion.actor,
            action_digest=assertion.action_digest,
            effect_scope=assertion.effect_scope,
            capability_status=assertion.capability_status,
            policy_revision=assertion.policy_revision,
            human_approval_ref=assertion.human_approval_ref,
            key_id=assertion.key_id,
            key_fingerprint_sha256=hashlib.sha256(key_bytes).hexdigest(),
            nonce=assertion.nonce,
            issued_at=issued,
            expires_at=expires,
        )


def bind_verified_prime_authorization(
    envelope: SovereignBoundaryEnvelope,
    verified: VerifiedPrimeEffectAuthorization,
) -> SovereignBoundaryEnvelope:
    """Attach verified PRIME custody evidence to the exact authorized envelope."""

    if verified.envelope_id != envelope.envelope_id or verified.action_digest != envelope.action_digest:
        raise BoundaryKernelError("verified PRIME authorization does not bind this envelope")
    return bind_prime_authorization_reference(
        envelope,
        authorization_id=verified.authorization_id,
        key_fingerprint_sha256=verified.key_fingerprint_sha256,
    )
