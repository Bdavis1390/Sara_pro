#!/usr/bin/env python3
"""Human-bound execution gate for WS-QPHONON.

This module requires a PRIME software pass plus a separately verified approval
attestation. Identity/signature verification must occur in an external trusted
identity layer; a caller-provided unverified approval is rejected.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
import uuid
from typing import Any, Iterable

HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ExecutionDecision:
    executable: bool
    disposition: str
    reasons: list[str]


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    if parsed.utcoffset().total_seconds() != 0:
        return None
    return parsed.astimezone(timezone.utc)


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and HEX64.fullmatch(value) is not None


def evaluate_execution(
    prime_decision: dict[str, Any],
    approval: dict[str, Any],
    *,
    experiment_digest: str,
    config_digest: str,
    seen_approval_ids: Iterable[str] = (),
    now: datetime | None = None,
    max_approval_lifetime_seconds: int = 900,
    max_future_skew_seconds: int = 30,
) -> ExecutionDecision:
    reasons: list[str] = []
    now = now or datetime.now(timezone.utc)

    if prime_decision.get("authorized") is not True:
        reasons.append("PRIME_SOFTWARE_GATE_NOT_PASSED")
    if prime_decision.get("disposition") != "READY_FOR_HUMAN_APPROVAL":
        reasons.append("PRIME_DISPOSITION_INVALID")

    if approval.get("approved") is not True:
        reasons.append("HUMAN_APPROVAL_MISSING")
    if approval.get("approval_attestation_verified") is not True:
        reasons.append("APPROVAL_ATTESTATION_NOT_VERIFIED")

    approval_id = approval.get("approval_id")
    try:
        parsed_id = uuid.UUID(str(approval_id))
        if parsed_id.version != 4 or str(parsed_id) != approval_id:
            reasons.append("APPROVAL_ID_NOT_CANONICAL_UUID4")
    except (ValueError, TypeError, AttributeError):
        reasons.append("APPROVAL_ID_INVALID")

    if approval_id in set(seen_approval_ids):
        reasons.append("APPROVAL_REPLAY_DETECTED")

    approver = approval.get("approver")
    if not isinstance(approver, str) or not approver.strip() or len(approver) > 256:
        reasons.append("APPROVER_INVALID")

    for field, expected, reason in (
        ("experiment_digest", experiment_digest, "EXPERIMENT_DIGEST_MISMATCH"),
        ("config_digest", config_digest, "CONFIG_DIGEST_MISMATCH"),
    ):
        value = approval.get(field)
        if not _hex64(value):
            reasons.append(f"{field.upper()}_INVALID")
        elif value != expected:
            reasons.append(reason)

    issued = _parse_utc(approval.get("issued_at_utc"))
    expires = _parse_utc(approval.get("expires_at_utc"))
    if issued is None:
        reasons.append("APPROVAL_ISSUED_TIME_INVALID")
    if expires is None:
        reasons.append("APPROVAL_EXPIRY_TIME_INVALID")
    if issued is not None and expires is not None:
        lifetime = (expires - issued).total_seconds()
        if lifetime <= 0 or lifetime > max_approval_lifetime_seconds:
            reasons.append("APPROVAL_LIFETIME_INVALID")
        if (issued - now).total_seconds() > max_future_skew_seconds:
            reasons.append("APPROVAL_ISSUED_IN_FUTURE")
        if expires <= now:
            reasons.append("APPROVAL_EXPIRED")

    executable = not reasons
    return ExecutionDecision(
        executable=executable,
        disposition="EXECUTION_ALLOWED" if executable else "EXECUTION_BLOCKED",
        reasons=reasons,
    )


def to_dict(decision: ExecutionDecision) -> dict[str, Any]:
    return asdict(decision)
