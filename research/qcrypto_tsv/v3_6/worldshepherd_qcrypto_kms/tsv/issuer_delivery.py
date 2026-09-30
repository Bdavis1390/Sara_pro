"""Hash-bound issuer-notice delivery evidence for WS-TSV-01.

This validates an operator-supplied delivery receipt and notice digest.  The
receipt is not treated as a qualified electronic-delivery service, legal proof,
digital signature, or independent attestation unless a future adapter provides
and validates such evidence explicitly.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from typing import Any, Optional

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class IssuerDeliveryReceipt:
    symbol: str
    issuer_id: str
    notice_sha256: str
    delivery_channel: str
    delivery_provider_id: str
    delivered_at: datetime
    provider_recorded_at: datetime
    provider_receipt_id: str
    provider_payload_sha256: str
    verified: bool
    objection_received_at: Optional[datetime] = None

    def material(self) -> dict:
        data = asdict(self)
        data["delivered_at"] = _utc(self.delivered_at).isoformat().replace("+00:00", "Z")
        data["provider_recorded_at"] = _utc(self.provider_recorded_at).isoformat().replace("+00:00", "Z")
        data["objection_received_at"] = _utc(self.objection_received_at).isoformat().replace("+00:00", "Z") if self.objection_received_at else None
        return data

    def receipt_sha256(self) -> str:
        return hashlib.sha256(b"WS-TSV-ISSUER-DELIVERY-RECEIPT-V1\x00" + _canon(self.material())).hexdigest()


@dataclass(frozen=True)
class IssuerDeliveryResult:
    decision: str
    errors: tuple[str, ...]
    receipt_sha256: Optional[str]
    claims_label: str = "HASH_BOUND_DELIVERY_EVIDENCE_ONLY_NOT_LEGAL_PROOF_OF_SERVICE"

    def to_dict(self) -> dict:
        return asdict(self)


def validate_issuer_delivery(
    receipt: Optional[IssuerDeliveryReceipt],
    *,
    expected_symbol: str,
    expected_notice_sha256: str,
    trading_start_at: datetime,
    now: datetime,
    allowed_channels: set[str] | frozenset[str] = frozenset({"REGISTERED_EMAIL", "COURIER", "ISSUER_PORTAL"}),
    max_provider_record_delay_seconds: int = 3600,
) -> IssuerDeliveryResult:
    if receipt is None:
        return IssuerDeliveryResult("DENY", ("ISSUER_DELIVERY_RECEIPT_ABSENT",), None)

    errors: list[str] = []
    if not receipt.verified:
        errors.append("ISSUER_DELIVERY_NOT_VERIFIED")
    if receipt.symbol.upper() != expected_symbol.upper():
        errors.append("ISSUER_DELIVERY_SYMBOL_MISMATCH")
    if not receipt.issuer_id.strip():
        errors.append("ISSUER_ID_EMPTY")
    if receipt.notice_sha256 != expected_notice_sha256 or not _SHA256_RE.fullmatch(receipt.notice_sha256):
        errors.append("NOTICE_DIGEST_MISMATCH")
    if receipt.delivery_channel not in allowed_channels:
        errors.append("DELIVERY_CHANNEL_NOT_ALLOWED")
    if not receipt.delivery_provider_id.strip() or not receipt.provider_receipt_id.strip():
        errors.append("DELIVERY_PROVIDER_IDENTITY_INCOMPLETE")
    if not _SHA256_RE.fullmatch(receipt.provider_payload_sha256):
        errors.append("PROVIDER_PAYLOAD_SHA256_MALFORMED")

    delivered = _utc(receipt.delivered_at)
    recorded = _utc(receipt.provider_recorded_at)
    trading = _utc(trading_start_at)
    now_u = _utc(now)
    if delivered > now_u or recorded > now_u:
        errors.append("DELIVERY_TIMESTAMP_IN_FUTURE")
    if recorded < delivered:
        errors.append("PROVIDER_RECORDED_BEFORE_DELIVERY")
    elif (recorded - delivered).total_seconds() > max_provider_record_delay_seconds:
        errors.append("PROVIDER_RECORD_DELAY_EXCEEDED")
    if trading < delivered + timedelta(days=30):
        errors.append("ISSUER_30_CALENDAR_DAY_WAIT_NOT_SATISFIED")
    if receipt.objection_received_at is not None:
        objection = _utc(receipt.objection_received_at)
        if objection > now_u:
            errors.append("ISSUER_OBJECTION_TIMESTAMP_IN_FUTURE")
        else:
            errors.append("ISSUER_OBJECTION_REQUIRES_HOLD")

    digest = receipt.receipt_sha256()
    return IssuerDeliveryResult("DENY" if errors else "ALLOW", tuple(errors), digest)
