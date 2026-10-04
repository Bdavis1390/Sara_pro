from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


WS_ECONOMIC_INTENT_SCHEMA = "WS-ECONOMIC-PAYMENT-INTENT-V0.1"
WS_ECONOMIC_POLICY_SCHEMA = "WS-ECONOMIC-AUTHORIZATION-POLICY-V0.1"

EconomicProtocol = Literal[
    "X402",
    "AP2",
    "MPP",
    "MASTERCARD_AP4M",
    "VISA_TAP",
    "CUSTOM",
]
ExecutionMode = Literal["DRY_RUN", "LIVE"]
EconomicDisposition = Literal["ALLOW_DRY_RUN", "DENY"]


class EconomicAuthorizationError(ValueError):
    pass


class EconomicPaymentIntent(BaseModel):
    """Protocol-neutral payment intent presented to the Worldshepherd policy gate.

    v0.1 deliberately carries no wallet key, signing primitive, facilitator
    credential, or settlement capability. LIVE execution is fail-closed by the
    evaluator until a later gate explicitly implements and validates it.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[WS_ECONOMIC_INTENT_SCHEMA] = WS_ECONOMIC_INTENT_SCHEMA
    intent_id: str = Field(min_length=1, max_length=128)
    actor_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    protocol: EconomicProtocol
    network: str = Field(min_length=1, max_length=128)
    asset: str = Field(min_length=1, max_length=128)
    payee: str = Field(min_length=1, max_length=512)
    amount: Decimal = Field(ge=Decimal("0"))
    purpose: str = Field(min_length=1, max_length=1024)
    mode: ExecutionMode = "DRY_RUN"
    created_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    human_approval_id: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_window(self) -> "EconomicPaymentIntent":
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("created_at and expires_at must be timezone-aware")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        return self


class EconomicAuthorizationPolicy(BaseModel):
    """Explicit allowlist-and-budget policy for one bounded payment session."""

    model_config = ConfigDict(extra="forbid")

    schema: Literal[WS_ECONOMIC_POLICY_SCHEMA] = WS_ECONOMIC_POLICY_SCHEMA
    policy_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    allowed_protocols: frozenset[EconomicProtocol] = Field(min_length=1)
    allowed_networks: frozenset[str] = Field(min_length=1)
    allowed_assets: frozenset[str] = Field(min_length=1)
    allowed_payees: frozenset[str] = Field(min_length=1)
    max_per_transaction: Decimal = Field(ge=Decimal("0"))
    max_session_total: Decimal = Field(ge=Decimal("0"))
    require_human_approval: bool = True
    expires_at: datetime

    @model_validator(mode="after")
    def validate_policy(self) -> "EconomicAuthorizationPolicy":
        if self.expires_at.tzinfo is None:
            raise ValueError("policy expires_at must be timezone-aware")
        if self.max_per_transaction > self.max_session_total:
            raise ValueError("max_per_transaction cannot exceed max_session_total")
        return self


class EconomicAuthorizationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    policy_id: str
    disposition: EconomicDisposition
    reasons: tuple[str, ...]
    amount: Decimal
    spent_before: Decimal
    remaining_budget_after: Decimal
    evaluated_at: datetime
    intent_sha256: str


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_economic_intent_message(intent: EconomicPaymentIntent) -> bytes:
    """Return a deterministic representation suitable for hashing/signing later."""

    payload = {
        "schema": intent.schema,
        "intent_id": intent.intent_id,
        "actor_id": intent.actor_id,
        "session_id": intent.session_id,
        "protocol": intent.protocol,
        "network": intent.network,
        "asset": intent.asset,
        "payee": intent.payee,
        "amount": str(intent.amount),
        "purpose": intent.purpose,
        "mode": intent.mode,
        "created_at": _utc_iso(intent.created_at),
        "expires_at": _utc_iso(intent.expires_at),
        "nonce": intent.nonce,
        "human_approval_id": intent.human_approval_id,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def economic_intent_sha256(intent: EconomicPaymentIntent) -> str:
    return hashlib.sha256(canonical_economic_intent_message(intent)).hexdigest()


def evaluate_economic_intent(
    intent: EconomicPaymentIntent,
    policy: EconomicAuthorizationPolicy,
    *,
    spent_so_far: Decimal,
    now: datetime | None = None,
) -> EconomicAuthorizationDecision:
    """Evaluate one payment intent without performing payment or signing.

    This function is intentionally pure with respect to external systems. It
    does not mutate a ledger, access a wallet, call a facilitator, or settle a
    payment. v0.1 is a dry-run authorization gate only.
    """

    if spent_so_far < 0:
        raise EconomicAuthorizationError("spent_so_far cannot be negative")

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    reasons: list[str] = []

    if current >= policy.expires_at.astimezone(timezone.utc):
        reasons.append("policy_expired")
    if current >= intent.expires_at.astimezone(timezone.utc):
        reasons.append("intent_expired")
    if intent.created_at.astimezone(timezone.utc) > current:
        reasons.append("intent_created_in_future")
    if intent.session_id != policy.session_id:
        reasons.append("session_mismatch")

    if intent.mode != "DRY_RUN":
        reasons.append("live_payment_execution_not_enabled")
    if intent.protocol not in policy.allowed_protocols:
        reasons.append("protocol_not_allowed")
    if intent.network not in policy.allowed_networks:
        reasons.append("network_not_allowed")
    if intent.asset not in policy.allowed_assets:
        reasons.append("asset_not_allowed")
    if intent.payee not in policy.allowed_payees:
        reasons.append("payee_not_allowed")
    if intent.amount > policy.max_per_transaction:
        reasons.append("per_transaction_limit_exceeded")

    total_after = spent_so_far + intent.amount
    if total_after > policy.max_session_total:
        reasons.append("session_budget_exceeded")

    if policy.require_human_approval and not intent.human_approval_id:
        reasons.append("human_approval_required")

    remaining = max(Decimal("0"), policy.max_session_total - total_after)
    disposition: EconomicDisposition = "DENY" if reasons else "ALLOW_DRY_RUN"

    return EconomicAuthorizationDecision(
        intent_id=intent.intent_id,
        policy_id=policy.policy_id,
        disposition=disposition,
        reasons=tuple(reasons),
        amount=intent.amount,
        spent_before=spent_so_far,
        remaining_budget_after=remaining,
        evaluated_at=current,
        intent_sha256=economic_intent_sha256(intent),
    )
