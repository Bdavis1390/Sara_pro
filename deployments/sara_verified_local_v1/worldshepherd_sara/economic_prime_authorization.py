from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .economic_authorization import (
    EconomicAuthorizationPolicy,
    EconomicPaymentIntent,
    EconomicProtocol,
    economic_intent_sha256,
    economic_policy_sha256,
)
from .economic_ledger import EconomicAuthorizationLedger, EconomicLedgerConflict
from .prime_sentinel_authorization import (
    MAX_ASSERTION_LIFETIME,
    MAX_FUTURE_SKEW,
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)


WS_ECONOMIC_PRIME_AUTHZ_SCHEMA = "WS-ECONOMIC-PRIME-AUTHZ-G2-V1"


class EconomicPrimeAuthorizationError(ValueError):
    pass


class EconomicPrimeAuthorizationAssertion(BaseModel):
    """Externally signed PRIME authorization bound to one economic intent.

    This schema carries only a detached Ed25519 signature and public-verification
    metadata. It contains no private signing key or wallet credential.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[WS_ECONOMIC_PRIME_AUTHZ_SCHEMA] = WS_ECONOMIC_PRIME_AUTHZ_SCHEMA
    issuer: Literal["PRIME_SENTINEL"] = "PRIME_SENTINEL"
    key_id: str = Field(min_length=1, max_length=128)
    authorization_id: str = Field(min_length=1, max_length=128)
    authorization_nonce: str = Field(min_length=16, max_length=128)
    intent_id: str = Field(min_length=1, max_length=128)
    intent_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_id: str = Field(min_length=1, max_length=128)
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    session_id: str = Field(min_length=1, max_length=128)
    protocol: EconomicProtocol
    network: str = Field(min_length=1, max_length=128)
    asset: str = Field(min_length=1, max_length=128)
    payee: str = Field(min_length=1, max_length=512)
    authorized_amount: Decimal = Field(ge=Decimal("0"))
    human_approval_id: str | None = Field(default=None, min_length=1, max_length=128)
    issued_at: datetime
    expires_at: datetime
    signature_b64url: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_window(self) -> "EconomicPrimeAuthorizationAssertion":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.expires_at - self.issued_at > MAX_ASSERTION_LIFETIME:
            raise ValueError("economic authorization lifetime exceeds PRIME maximum")
        return self


class VerifiedEconomicPrimeAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorization_id: str
    authorization_nonce: str
    intent_id: str
    intent_sha256: str
    policy_id: str
    policy_sha256: str
    session_id: str
    protocol: EconomicProtocol
    network: str
    asset: str
    payee: str
    authorized_amount: Decimal
    human_approval_id: str | None
    key_id: str
    key_fingerprint_sha256: str
    issued_at: datetime
    expires_at: datetime
    authorization_record_sha256: str


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_economic_prime_authorization_message(
    assertion: EconomicPrimeAuthorizationAssertion,
) -> bytes:
    payload = {
        "schema": assertion.schema,
        "issuer": assertion.issuer,
        "key_id": assertion.key_id,
        "authorization_id": assertion.authorization_id,
        "authorization_nonce": assertion.authorization_nonce,
        "intent_id": assertion.intent_id,
        "intent_sha256": assertion.intent_sha256,
        "policy_id": assertion.policy_id,
        "policy_sha256": assertion.policy_sha256,
        "session_id": assertion.session_id,
        "protocol": assertion.protocol,
        "network": assertion.network,
        "asset": assertion.asset,
        "payee": assertion.payee,
        "authorized_amount": str(assertion.authorized_amount),
        "human_approval_id": assertion.human_approval_id,
        "issued_at": _utc_iso(assertion.issued_at),
        "expires_at": _utc_iso(assertion.expires_at),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def economic_prime_authorization_record_sha256(
    assertion: EconomicPrimeAuthorizationAssertion,
) -> str:
    payload = assertion.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_economic_prime_authorization(
    assertion: EconomicPrimeAuthorizationAssertion,
    *,
    verifier: PrimeSentinelVerifier,
    intent: EconomicPaymentIntent,
    policy: EconomicAuthorizationPolicy,
    now: datetime | None = None,
) -> VerifiedEconomicPrimeAuthorization:
    """Verify signature, freshness, and exact intent/policy binding.

    The verifier is public-key-only. This function cannot issue an
    authorization and cannot execute or settle a payment.
    """

    try:
        detached = verifier.verify_detached_signature(
            key_id=assertion.key_id,
            message=canonical_economic_prime_authorization_message(assertion),
            signature_b64url=assertion.signature_b64url,
        )
    except PrimeSentinelAuthorizationError as exc:
        raise EconomicPrimeAuthorizationError(str(exc)) from exc

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issued = assertion.issued_at.astimezone(timezone.utc)
    expires = assertion.expires_at.astimezone(timezone.utc)
    if issued > current + MAX_FUTURE_SKEW:
        raise EconomicPrimeAuthorizationError(
            "economic authorization assertion is issued too far in the future"
        )
    if current >= expires:
        raise EconomicPrimeAuthorizationError("economic authorization assertion is expired")

    expected_intent_digest = economic_intent_sha256(intent)
    expected_policy_digest = economic_policy_sha256(policy)
    mismatches: list[str] = []

    checks = (
        ("intent_id", assertion.intent_id, intent.intent_id),
        ("intent_sha256", assertion.intent_sha256, expected_intent_digest),
        ("policy_id", assertion.policy_id, policy.policy_id),
        ("policy_sha256", assertion.policy_sha256, expected_policy_digest),
        ("session_id", assertion.session_id, intent.session_id),
        ("policy_session_id", assertion.session_id, policy.session_id),
        ("protocol", assertion.protocol, intent.protocol),
        ("network", assertion.network, intent.network),
        ("asset", assertion.asset, intent.asset),
        ("payee", assertion.payee, intent.payee),
        ("authorized_amount", assertion.authorized_amount, intent.amount),
        ("human_approval_id", assertion.human_approval_id, intent.human_approval_id),
    )
    for label, observed, expected in checks:
        if observed != expected:
            mismatches.append(label)

    if policy.require_human_approval and not assertion.human_approval_id:
        mismatches.append("human_approval_required")

    if mismatches:
        raise EconomicPrimeAuthorizationError(
            "economic authorization binding mismatch: " + ",".join(mismatches)
        )

    return VerifiedEconomicPrimeAuthorization(
        authorization_id=assertion.authorization_id,
        authorization_nonce=assertion.authorization_nonce,
        intent_id=assertion.intent_id,
        intent_sha256=assertion.intent_sha256,
        policy_id=assertion.policy_id,
        policy_sha256=assertion.policy_sha256,
        session_id=assertion.session_id,
        protocol=assertion.protocol,
        network=assertion.network,
        asset=assertion.asset,
        payee=assertion.payee,
        authorized_amount=assertion.authorized_amount,
        human_approval_id=assertion.human_approval_id,
        key_id=detached.key_id,
        key_fingerprint_sha256=detached.key_fingerprint_sha256,
        issued_at=issued,
        expires_at=expires,
        authorization_record_sha256=economic_prime_authorization_record_sha256(assertion),
    )


def bind_verified_economic_prime_authorization(
    ledger: EconomicAuthorizationLedger,
    verified: VerifiedEconomicPrimeAuthorization,
    *,
    now: datetime | None = None,
):
    """Persist an already verified PRIME economic authorization into G1 state.

    This binding step re-checks the durable intent and policy digests before
    recording PRIME_VERIFIED, preventing a verified assertion from being
    attached to a different durable economic intent.
    """

    record = ledger.get(verified.intent_id)
    if record is None:
        raise EconomicPrimeAuthorizationError(
            "verified PRIME authorization references an unrecorded economic intent"
        )
    if record.intent_sha256 != verified.intent_sha256:
        raise EconomicPrimeAuthorizationError(
            "verified PRIME authorization intent digest does not match durable ledger"
        )
    if record.policy_id != verified.policy_id or record.policy_sha256 != verified.policy_sha256:
        raise EconomicPrimeAuthorizationError(
            "verified PRIME authorization policy binding does not match durable ledger"
        )
    if record.session_id != verified.session_id:
        raise EconomicPrimeAuthorizationError(
            "verified PRIME authorization session does not match durable ledger"
        )
    if record.decision_status != "ALLOWED":
        raise EconomicPrimeAuthorizationError(
            "verified PRIME authorization cannot bind to a non-allowed economic decision"
        )

    try:
        return ledger.record_authorization_result(
            intent_id=verified.intent_id,
            status="PRIME_VERIFIED",
            authorization_ref=verified.authorization_id,
            authorization_digest_sha256=verified.authorization_record_sha256,
            authorization_nonce=verified.authorization_nonce,
            now=now,
        )
    except EconomicLedgerConflict as exc:
        raise EconomicPrimeAuthorizationError(str(exc)) from exc
