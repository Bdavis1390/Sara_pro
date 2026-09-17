"""Fail-closed handoff at the last boundary before value-moving execution.

This module verifies a short-lived ML-DSA-65 human approval against one exact
unsigned transaction intent and one exact external signer/network identity.  It
never signs a transaction, imports or exports private keys, broadcasts a payload,
or moves value.  A successful assessment means only that an external,
human-operated signer may receive the frozen execution package.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PublicKey
from pydantic import BaseModel, ConfigDict, Field, model_validator


EXECUTION_INTENT_SCHEMA = "WS-LIVE-VALUE-EXECUTION-INTENT-V1"
HUMAN_APPROVAL_SCHEMA = "WS-LIVE-VALUE-HUMAN-APPROVAL-V1"
HUMAN_APPROVAL_CONTEXT = b"WS-LIVE-VALUE-HUMAN-APPROVAL-V1"
HANDOFF_SCHEMA = "WS-LIVE-VALUE-EXECUTION-HANDOFF-V1"
UPSTREAM_READY_STATE = "LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL"
MAX_APPROVAL_LIFETIME = timedelta(minutes=15)
MAX_FUTURE_SKEW = timedelta(seconds=60)
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_REVISION_PATTERN = r"^[0-9a-f]{40,64}$"


class LiveValueHandoffError(ValueError):
    pass


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _b64url_decode(value: str, *, expected_length: int, label: str) -> bytes:
    try:
        encoded = value.encode("ascii")
        padded = encoded + b"=" * (-len(encoded) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise LiveValueHandoffError(f"invalid {label} encoding") from exc
    if len(decoded) != expected_length:
        raise LiveValueHandoffError(f"{label} must decode to {expected_length} bytes")
    return decoded


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class LiveValueExecutionIntent(BaseModel):
    """Frozen, unsigned value-moving transaction intent.

    ``unsigned_transaction_digest_sha256`` binds the exact externally constructed
    unsigned transaction bytes without placing those bytes or any signing secret
    inside QCRYPTO.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[EXECUTION_INTENT_SCHEMA] = EXECUTION_INTENT_SCHEMA
    chain: str = Field(min_length=1, max_length=64)
    network: str = Field(min_length=1, max_length=64)
    asset: str = Field(min_length=1, max_length=64)
    amount_atomic: int = Field(gt=0)
    fee_ceiling_atomic: int = Field(ge=0)
    source_custody_ref: str = Field(min_length=1, max_length=256)
    destination_commitment_sha256: str = Field(pattern=_SHA256_PATTERN)
    unsigned_transaction_digest_sha256: str = Field(pattern=_SHA256_PATTERN)
    review_package_sha256: str = Field(pattern=_SHA256_PATTERN)
    production_revision: str = Field(pattern=_REVISION_PATTERN)
    change_ticket_id: str = Field(min_length=1, max_length=128)
    intent_nonce: str = Field(min_length=16, max_length=128)
    valid_until: datetime

    @model_validator(mode="after")
    def validate_time(self) -> "LiveValueExecutionIntent":
        if self.valid_until.tzinfo is None:
            raise ValueError("valid_until must be timezone-aware")
        return self


def canonical_execution_intent(intent: LiveValueExecutionIntent) -> dict[str, Any]:
    return {
        "schema": intent.schema,
        "chain": intent.chain,
        "network": intent.network,
        "asset": intent.asset,
        "amount_atomic": intent.amount_atomic,
        "fee_ceiling_atomic": intent.fee_ceiling_atomic,
        "source_custody_ref": intent.source_custody_ref,
        "destination_commitment_sha256": intent.destination_commitment_sha256,
        "unsigned_transaction_digest_sha256": intent.unsigned_transaction_digest_sha256,
        "review_package_sha256": intent.review_package_sha256,
        "production_revision": intent.production_revision,
        "change_ticket_id": intent.change_ticket_id,
        "intent_nonce": intent.intent_nonce,
        "valid_until": _utc_iso(intent.valid_until),
    }


def execution_intent_sha256(intent: LiveValueExecutionIntent) -> str:
    return _sha256_json(canonical_execution_intent(intent))


class HumanLiveValueApproval(BaseModel):
    """Externally produced, short-lived human approval for one frozen intent."""

    model_config = ConfigDict(extra="forbid")

    schema: Literal[HUMAN_APPROVAL_SCHEMA] = HUMAN_APPROVAL_SCHEMA
    issuer: Literal["HUMAN_CHANGE_CONTROL"] = "HUMAN_CHANGE_CONTROL"
    approver_id: str = Field(min_length=1, max_length=128)
    approval_id: str = Field(min_length=1, max_length=128)
    key_id: str = Field(min_length=1, max_length=128)
    intent_sha256: str = Field(pattern=_SHA256_PATTERN)
    review_package_sha256: str = Field(pattern=_SHA256_PATTERN)
    destination_commitment_sha256: str = Field(pattern=_SHA256_PATTERN)
    external_signer_fingerprint_sha256: str = Field(pattern=_SHA256_PATTERN)
    network_identity_sha256: str = Field(pattern=_SHA256_PATTERN)
    maximum_amount_atomic: int = Field(gt=0)
    maximum_fee_atomic: int = Field(ge=0)
    change_ticket_id: str = Field(min_length=1, max_length=128)
    production_revision: str = Field(pattern=_REVISION_PATTERN)
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    signature_b64url: str = Field(min_length=1, max_length=8192)

    @model_validator(mode="after")
    def validate_window(self) -> "HumanLiveValueApproval":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("issued_at and expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if self.expires_at - self.issued_at > MAX_APPROVAL_LIFETIME:
            raise ValueError("human approval lifetime exceeds 15 minutes")
        return self


def canonical_human_approval_message(approval: HumanLiveValueApproval) -> bytes:
    payload = {
        "schema": approval.schema,
        "issuer": approval.issuer,
        "approver_id": approval.approver_id,
        "approval_id": approval.approval_id,
        "key_id": approval.key_id,
        "intent_sha256": approval.intent_sha256,
        "review_package_sha256": approval.review_package_sha256,
        "destination_commitment_sha256": approval.destination_commitment_sha256,
        "external_signer_fingerprint_sha256": approval.external_signer_fingerprint_sha256,
        "network_identity_sha256": approval.network_identity_sha256,
        "maximum_amount_atomic": approval.maximum_amount_atomic,
        "maximum_fee_atomic": approval.maximum_fee_atomic,
        "change_ticket_id": approval.change_ticket_id,
        "production_revision": approval.production_revision,
        "issued_at": _utc_iso(approval.issued_at),
        "expires_at": _utc_iso(approval.expires_at),
        "nonce": approval.nonce,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class VerifiedHumanLiveValueApproval:
    approval_id: str
    approver_id: str
    key_id: str
    key_fingerprint_sha256: str
    intent_sha256: str
    review_package_sha256: str
    destination_commitment_sha256: str
    external_signer_fingerprint_sha256: str
    network_identity_sha256: str
    maximum_amount_atomic: int
    maximum_fee_atomic: int
    change_ticket_id: str
    production_revision: str
    issued_at: datetime
    expires_at: datetime
    nonce: str


class HumanLiveValueApprovalVerifier:
    """Verify ML-DSA-65 human approvals against a trusted external key map."""

    def __init__(self, *, public_keys_b64url: dict[str, str]) -> None:
        if not public_keys_b64url:
            raise ValueError("at least one human-approval public key is required")
        self._keys: dict[str, bytes] = {}
        for key_id, encoded in public_keys_b64url.items():
            if not key_id:
                raise ValueError("human-approval key ID cannot be empty")
            self._keys[key_id] = _b64url_decode(
                encoded,
                expected_length=1952,
                label=f"ML-DSA-65 human-approval public key {key_id}",
            )

    def verify(
        self,
        approval: HumanLiveValueApproval,
        intent: LiveValueExecutionIntent,
        *,
        now: datetime | None = None,
    ) -> VerifiedHumanLiveValueApproval:
        key = self._keys.get(approval.key_id)
        if key is None:
            raise LiveValueHandoffError("unknown human-approval signing key")

        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        issued = approval.issued_at.astimezone(timezone.utc)
        expires = approval.expires_at.astimezone(timezone.utc)
        if issued > current + MAX_FUTURE_SKEW:
            raise LiveValueHandoffError("human approval is issued too far in the future")
        if current >= expires:
            raise LiveValueHandoffError("human approval is expired")
        if current >= intent.valid_until.astimezone(timezone.utc):
            raise LiveValueHandoffError("execution intent is expired")

        expected_intent = execution_intent_sha256(intent)
        exact_bindings = {
            "intent_sha256": expected_intent,
            "review_package_sha256": intent.review_package_sha256,
            "destination_commitment_sha256": intent.destination_commitment_sha256,
            "change_ticket_id": intent.change_ticket_id,
            "production_revision": intent.production_revision,
        }
        for field, expected in exact_bindings.items():
            if getattr(approval, field) != expected:
                raise LiveValueHandoffError(f"human approval {field} does not match execution intent")
        if intent.amount_atomic > approval.maximum_amount_atomic:
            raise LiveValueHandoffError("execution amount exceeds human-approved maximum")
        if intent.fee_ceiling_atomic > approval.maximum_fee_atomic:
            raise LiveValueHandoffError("execution fee ceiling exceeds human-approved maximum")

        signature = _b64url_decode(
            approval.signature_b64url,
            expected_length=3309,
            label="ML-DSA-65 human-approval signature",
        )
        try:
            MLDSA65PublicKey.from_public_bytes(key).verify(
                signature,
                canonical_human_approval_message(approval),
                HUMAN_APPROVAL_CONTEXT,
            )
        except (InvalidSignature, ValueError) as exc:
            raise LiveValueHandoffError("invalid human live-value approval signature") from exc

        return VerifiedHumanLiveValueApproval(
            approval_id=approval.approval_id,
            approver_id=approval.approver_id,
            key_id=approval.key_id,
            key_fingerprint_sha256=hashlib.sha256(key).hexdigest(),
            intent_sha256=approval.intent_sha256,
            review_package_sha256=approval.review_package_sha256,
            destination_commitment_sha256=approval.destination_commitment_sha256,
            external_signer_fingerprint_sha256=approval.external_signer_fingerprint_sha256,
            network_identity_sha256=approval.network_identity_sha256,
            maximum_amount_atomic=approval.maximum_amount_atomic,
            maximum_fee_atomic=approval.maximum_fee_atomic,
            change_ticket_id=approval.change_ticket_id,
            production_revision=approval.production_revision,
            issued_at=issued,
            expires_at=expires,
            nonce=approval.nonce,
        )


@dataclass(frozen=True)
class ExternalExecutionPreflight:
    intent_sha256: str
    approval_id: str
    external_signer_fingerprint_sha256: str
    network_identity_sha256: str
    destination_commitment_sha256: str
    observed_fee_atomic: int
    destination_allowlist_match: bool
    balance_or_utxo_sufficient: bool
    nonce_or_outpoint_reserved: bool
    simulation_or_policy_check_passed: bool
    monitoring_ready: bool
    pause_ready: bool
    rollback_ready: bool
    approval_consumed: bool = False
    signed_payload_present: bool = False
    private_key_material_present: bool = False
    broadcast_requested: bool = False


@dataclass(frozen=True)
class LiveValueExecutionHandoffAssessment:
    schema: str
    state: str
    handoff_package_sha256: str | None
    intent_sha256: str
    approval_id: str | None
    approver_id: str | None
    human_live_value_approval_verified: bool
    external_signer_handoff_ready: bool
    point_of_value_moving_execution_reached: bool
    qcrypto_execution_authority: bool
    qcrypto_live_value_authorized: bool
    qcrypto_private_key_operations_permitted: bool
    qcrypto_broadcast_permitted: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_live_value_execution_handoff(
    *,
    upstream_readiness_state: str,
    intent: LiveValueExecutionIntent,
    verified_approval: VerifiedHumanLiveValueApproval,
    preflight: ExternalExecutionPreflight,
) -> LiveValueExecutionHandoffAssessment:
    """Stop at the exact boundary before external signing/broadcast."""

    blockers: list[str] = []
    warnings: list[str] = []
    intent_digest = execution_intent_sha256(intent)

    if upstream_readiness_state != UPSTREAM_READY_STATE:
        blockers.append("Upstream live-value canary controls are not at the explicit-human-approval boundary.")
    if verified_approval.intent_sha256 != intent_digest:
        blockers.append("Verified human approval is not bound to the supplied execution intent.")
    if verified_approval.review_package_sha256 != intent.review_package_sha256:
        blockers.append("Verified human approval is not bound to the supplied review package.")
    if verified_approval.destination_commitment_sha256 != intent.destination_commitment_sha256:
        blockers.append("Verified human approval destination commitment mismatch.")
    if verified_approval.change_ticket_id != intent.change_ticket_id:
        blockers.append("Verified human approval change-ticket mismatch.")
    if verified_approval.production_revision != intent.production_revision:
        blockers.append("Verified human approval production revision mismatch.")
    if intent.amount_atomic > verified_approval.maximum_amount_atomic:
        blockers.append("Execution amount exceeds the verified human approval cap.")
    if intent.fee_ceiling_atomic > verified_approval.maximum_fee_atomic:
        blockers.append("Execution fee ceiling exceeds the verified human approval cap.")

    if preflight.intent_sha256 != intent_digest:
        blockers.append("External preflight is not bound to the exact execution intent.")
    if preflight.approval_id != verified_approval.approval_id:
        blockers.append("External preflight approval identity mismatch.")
    if preflight.external_signer_fingerprint_sha256 != verified_approval.external_signer_fingerprint_sha256:
        blockers.append("External signer fingerprint is not the human-approved signer.")
    if preflight.network_identity_sha256 != verified_approval.network_identity_sha256:
        blockers.append("Observed network identity is not the human-approved network identity.")
    if preflight.destination_commitment_sha256 != intent.destination_commitment_sha256:
        blockers.append("External preflight destination commitment mismatch.")
    if preflight.observed_fee_atomic > intent.fee_ceiling_atomic:
        blockers.append("Observed transaction fee exceeds the frozen intent ceiling.")

    required_controls = {
        "destination allowlist": preflight.destination_allowlist_match,
        "balance/UTXO sufficiency": preflight.balance_or_utxo_sufficient,
        "nonce/outpoint reservation": preflight.nonce_or_outpoint_reserved,
        "simulation/policy check": preflight.simulation_or_policy_check_passed,
        "monitoring": preflight.monitoring_ready,
        "pause control": preflight.pause_ready,
        "rollback control": preflight.rollback_ready,
    }
    for label, passed in required_controls.items():
        if not passed:
            blockers.append(f"External execution preflight failed: {label}.")

    if preflight.approval_consumed:
        blockers.append("Human approval has already been consumed and cannot be replayed.")
    if preflight.signed_payload_present:
        blockers.append("Signed payload must not enter QCRYPTO before external-signer handoff.")
    if preflight.private_key_material_present:
        blockers.append("Private key material must never enter the QCRYPTO handoff package.")
    if preflight.broadcast_requested:
        blockers.append("Broadcast request crosses the QCRYPTO authority boundary and is not permitted here.")

    handoff_digest: str | None = None
    if not blockers:
        binding = {
            "schema": HANDOFF_SCHEMA,
            "intent_sha256": intent_digest,
            "approval_id": verified_approval.approval_id,
            "approver_id": verified_approval.approver_id,
            "approval_key_fingerprint_sha256": verified_approval.key_fingerprint_sha256,
            "external_signer_fingerprint_sha256": verified_approval.external_signer_fingerprint_sha256,
            "network_identity_sha256": verified_approval.network_identity_sha256,
            "destination_commitment_sha256": intent.destination_commitment_sha256,
            "unsigned_transaction_digest_sha256": intent.unsigned_transaction_digest_sha256,
            "review_package_sha256": intent.review_package_sha256,
            "production_revision": intent.production_revision,
            "change_ticket_id": intent.change_ticket_id,
            "amount_atomic": intent.amount_atomic,
            "fee_ceiling_atomic": intent.fee_ceiling_atomic,
            "observed_fee_atomic": preflight.observed_fee_atomic,
            "qcrypto_execution_authority": False,
            "qcrypto_broadcast_permitted": False,
        }
        handoff_digest = _sha256_json(binding)
        warnings.append(
            "The handoff package is ready only for the separately controlled external signer; QCRYPTO remains unable to sign or broadcast."
        )

    ready = not blockers
    return LiveValueExecutionHandoffAssessment(
        schema=HANDOFF_SCHEMA,
        state=(
            "READY_FOR_EXTERNAL_SIGNER_VALUE_EXECUTION_HANDOFF"
            if ready
            else "VALUE_EXECUTION_HANDOFF_BLOCKED"
        ),
        handoff_package_sha256=handoff_digest,
        intent_sha256=intent_digest,
        approval_id=verified_approval.approval_id if verified_approval else None,
        approver_id=verified_approval.approver_id if verified_approval else None,
        human_live_value_approval_verified=True,
        external_signer_handoff_ready=ready,
        point_of_value_moving_execution_reached=ready,
        qcrypto_execution_authority=False,
        qcrypto_live_value_authorized=False,
        qcrypto_private_key_operations_permitted=False,
        qcrypto_broadcast_permitted=False,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        next_action=(
            "EXTERNAL_HUMAN_OPERATED_SIGNER_MAY_SIGN_AND_BROADCAST_ONLY_WITHIN_THE_BOUND_INTENT"
            if ready
            else "RESOLVE_HANDOFF_BLOCKERS_WITHOUT_SIGNING_OR_BROADCASTING"
        ),
    )
