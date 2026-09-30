"""Fail-closed market-data adapter controls for WS-TSV-01.

The adapter validates source identity, freshness, clock skew, sequence continuity,
duplicate/replay behavior, and cross-source status conflicts.  It does not
provide or claim a licensed SIP, exchange, or LULD connection.  Source names and
identifiers are inputs that must be bound to an operator-controlled registry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Optional, Sequence

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_KINDS = {"SIP", "PRIMARY_LISTING_EXCHANGE", "LULD_PLAN"}
_ALLOWED_STATUSES = {"TRADING", "HALTED", "PAUSED", "RESUME_ELIGIBLE"}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class MarketDataMessage:
    source_kind: str
    source_id: str
    symbol: str
    sequence: int
    status: str
    effective_at: datetime
    observed_at: datetime
    payload_sha256: str
    verified: bool = True
    session_id: str = "default"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["effective_at"] = _utc(self.effective_at).isoformat().replace("+00:00", "Z")
        data["observed_at"] = _utc(self.observed_at).isoformat().replace("+00:00", "Z")
        return data


@dataclass(frozen=True)
class FeedCursor:
    source_kind: str
    source_id: str
    symbol: str
    session_id: str
    last_sequence: int
    last_payload_sha256: str
    last_effective_at: datetime

    def to_dict(self) -> dict:
        data = asdict(self)
        data["last_effective_at"] = _utc(self.last_effective_at).isoformat().replace("+00:00", "Z")
        return data


@dataclass(frozen=True)
class AdapterResult:
    decision: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    cursor: Optional[FeedCursor]
    message_sha256: Optional[str]
    source_claim: str = "SOURCE_IDENTITY_AND_SEQUENCE_VALIDATION_ONLY"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["cursor"] = self.cursor.to_dict() if self.cursor else None
        return data


@dataclass(frozen=True)
class MarketStatusDecision:
    decision: str
    reason: str
    errors: tuple[str, ...]
    statuses: tuple[dict, ...]
    decision_sha256: str
    claims_label: str = "BOUNDED_MARKET_STATUS_SOFTWARE_DECISION_NOT_LICENSED_MARKET_DATA"

    def to_dict(self) -> dict:
        return asdict(self)


def message_sha256(message: MarketDataMessage) -> str:
    return hashlib.sha256(b"WS-TSV-MARKET-DATA-MESSAGE-V1\x00" + _canon(message.to_dict())).hexdigest()


def validate_market_message(
    message: MarketDataMessage,
    *,
    expected_symbol: str,
    now: datetime,
    source_registry: Mapping[str, set[str] | frozenset[str]],
    max_age_seconds: int = 30,
    max_future_skew_seconds: int = 2,
    max_observation_delay_seconds: int = 10,
    cursor: Optional[FeedCursor] = None,
) -> AdapterResult:
    errors: list[str] = []
    warnings: list[str] = []
    if message.source_kind not in _ALLOWED_KINDS:
        errors.append("SOURCE_KIND_NOT_ALLOWED")
    allowed_ids = source_registry.get(message.source_kind, set())
    if message.source_id not in allowed_ids:
        errors.append("SOURCE_ID_NOT_REGISTERED")
    if not message.verified:
        errors.append("SOURCE_NOT_VERIFIED")
    if message.symbol.upper() != expected_symbol.upper():
        errors.append("SYMBOL_MISMATCH")
    if message.sequence < 1:
        errors.append("SEQUENCE_INVALID")
    if message.status not in _ALLOWED_STATUSES:
        errors.append("STATUS_INVALID")
    if not message.session_id.strip():
        errors.append("SESSION_ID_EMPTY")
    if not _SHA256_RE.fullmatch(message.payload_sha256):
        errors.append("PAYLOAD_SHA256_MALFORMED")

    now_u = _utc(now)
    eff = _utc(message.effective_at)
    obs = _utc(message.observed_at)
    if (eff - now_u).total_seconds() > max_future_skew_seconds or (obs - now_u).total_seconds() > max_future_skew_seconds:
        errors.append("FUTURE_TIMESTAMP_EXCEEDS_CLOCK_SKEW")
    age = (now_u - obs).total_seconds()
    if age > max_age_seconds:
        errors.append("MESSAGE_STALE")
    if age < -max_future_skew_seconds:
        errors.append("OBSERVED_AT_TOO_FAR_IN_FUTURE")
    delay = (obs - eff).total_seconds()
    if delay < -max_future_skew_seconds:
        errors.append("EFFECTIVE_AFTER_OBSERVATION")
    if delay > max_observation_delay_seconds:
        errors.append("OBSERVATION_DELAY_EXCEEDED")

    next_cursor: Optional[FeedCursor] = None
    if cursor is not None:
        if (
            cursor.source_kind != message.source_kind
            or cursor.source_id != message.source_id
            or cursor.symbol.upper() != message.symbol.upper()
            or cursor.session_id != message.session_id
        ):
            errors.append("CURSOR_IDENTITY_MISMATCH")
        elif message.sequence < cursor.last_sequence:
            errors.append("SEQUENCE_REPLAY_OR_REORDER")
        elif message.sequence == cursor.last_sequence:
            if message.payload_sha256 == cursor.last_payload_sha256:
                warnings.append("EXACT_DUPLICATE_IGNORED")
            else:
                errors.append("SEQUENCE_EQUIVOCATION")
        elif message.sequence > cursor.last_sequence + 1:
            errors.append("SEQUENCE_GAP")
        if eff < _utc(cursor.last_effective_at):
            errors.append("EFFECTIVE_TIME_REORDER")

    if not errors and not warnings:
        next_cursor = FeedCursor(
            source_kind=message.source_kind,
            source_id=message.source_id,
            symbol=message.symbol.upper(),
            session_id=message.session_id,
            last_sequence=message.sequence,
            last_payload_sha256=message.payload_sha256,
            last_effective_at=eff,
        )
    elif not errors and warnings and cursor is not None:
        next_cursor = cursor

    decision = "DENY" if errors else "ALLOW_WITH_WARNINGS" if warnings else "ALLOW"
    return AdapterResult(decision, tuple(errors), tuple(warnings), next_cursor, message_sha256(message))


def reconcile_market_status(
    messages: Sequence[MarketDataMessage],
    *,
    expected_symbol: str,
    require_primary_exchange: bool = True,
    require_sip_for_resume: bool = True,
) -> MarketStatusDecision:
    errors: list[str] = []
    if not messages:
        errors.append("NO_MARKET_STATUS_MESSAGES")
    symbol_rows = [m for m in messages if m.symbol.upper() == expected_symbol.upper()]
    if len(symbol_rows) != len(messages):
        errors.append("CROSS_SYMBOL_INPUT")

    by_kind: dict[str, set[str]] = {}
    for m in symbol_rows:
        by_kind.setdefault(m.source_kind, set()).add(m.status)
    for kind, statuses in by_kind.items():
        if len(statuses) > 1:
            errors.append(f"SOURCE_KIND_STATUS_CONFLICT:{kind}")

    primary = by_kind.get("PRIMARY_LISTING_EXCHANGE", set())
    sip = by_kind.get("SIP", set())
    luld = by_kind.get("LULD_PLAN", set())
    if require_primary_exchange and not primary:
        errors.append("PRIMARY_EXCHANGE_STATUS_REQUIRED")

    reason = "MARKET_STATUS_CLEAR"
    if "HALTED" in primary:
        reason = "PRIMARY_EXCHANGE_HALT"
        errors.append("TRADING_STOP_REQUIRED")
    if "PAUSED" in luld:
        reason = "LULD_SUPPLEMENTAL_PAUSE"
        errors.append("SUPPLEMENTAL_PAUSE_GUARD_ACTIVE")

    # Any disagreement around a halt/pause is resolved fail-closed.  A SIP is not
    # permitted to override the primary-listing exchange, and vice versa.
    active_statuses = set().union(*by_kind.values()) if by_kind else set()
    stopping = active_statuses & {"HALTED", "PAUSED"}
    permissive = active_statuses & {"TRADING", "RESUME_ELIGIBLE"}
    if stopping and permissive:
        errors.append("CROSS_SOURCE_STATUS_CONFLICT")
        reason = "CROSS_SOURCE_STATUS_CONFLICT"

    if primary == {"RESUME_ELIGIBLE"} and require_sip_for_resume and sip != {"RESUME_ELIGIBLE"}:
        errors.append("RESUME_QUORUM_INCOMPLETE")
        reason = "RESUME_QUORUM_INCOMPLETE"

    status_rows = tuple(
        sorted(
            ({"source_kind": m.source_kind, "source_id": m.source_id, "status": m.status, "sequence": m.sequence} for m in symbol_rows),
            key=lambda r: (r["source_kind"], r["source_id"], r["sequence"]),
        )
    )
    material = {"symbol": expected_symbol.upper(), "reason": reason, "errors": sorted(errors), "statuses": status_rows}
    digest = hashlib.sha256(b"WS-TSV-MARKET-STATUS-DECISION-V1\x00" + _canon(material)).hexdigest()
    return MarketStatusDecision("DENY" if errors else "ALLOW", reason, tuple(errors), status_rows, digest)

@dataclass(frozen=True)
class MarketBatchResult:
    decision: str
    errors: tuple[str, ...]
    message_results: tuple[dict, ...]
    latest_status: dict
    batch_sha256: str
    claims_label: str = "ADVERSARIAL_STREAM_VALIDATION_ONLY_NOT_LIVE_MARKET_FEED"

    def to_dict(self) -> dict:
        return asdict(self)


def validate_market_batch(
    messages: Sequence[MarketDataMessage],
    *,
    expected_symbol: str,
    now: datetime,
    source_registry: Mapping[str, set[str] | frozenset[str]],
    max_age_seconds: int = 30,
    max_future_skew_seconds: int = 2,
    max_observation_delay_seconds: int = 10,
    require_primary_exchange: bool = True,
    require_sip_for_resume: bool = True,
) -> MarketBatchResult:
    cursors: dict[tuple[str, str, str, str], FeedCursor] = {}
    latest: dict[tuple[str, str], MarketDataMessage] = {}
    rows: list[dict] = []
    errors: list[str] = []
    for index, message in enumerate(messages):
        key = (message.source_kind, message.source_id, message.symbol.upper(), message.session_id)
        result = validate_market_message(
            message,
            expected_symbol=expected_symbol,
            now=now,
            source_registry=source_registry,
            max_age_seconds=max_age_seconds,
            max_future_skew_seconds=max_future_skew_seconds,
            max_observation_delay_seconds=max_observation_delay_seconds,
            cursor=cursors.get(key),
        )
        row = {"index": index, "message": message.to_dict(), "validation": result.to_dict()}
        rows.append(row)
        if result.decision == "DENY":
            errors.extend(f"MESSAGE_{index}:{e}" for e in result.errors)
            continue
        if result.cursor is not None:
            cursors[key] = result.cursor
        if "EXACT_DUPLICATE_IGNORED" not in result.warnings:
            latest[(message.source_kind, message.source_id)] = message

    reconciled = reconcile_market_status(
        list(latest.values()),
        expected_symbol=expected_symbol,
        require_primary_exchange=require_primary_exchange,
        require_sip_for_resume=require_sip_for_resume,
    )
    if reconciled.decision == "DENY":
        errors.extend(f"STATUS:{e}" for e in reconciled.errors)
    material = {
        "symbol": expected_symbol.upper(),
        "errors": errors,
        "message_results": rows,
        "latest_status": reconciled.to_dict(),
    }
    digest = hashlib.sha256(b"WS-TSV-MARKET-BATCH-V1\x00" + _canon(material)).hexdigest()
    return MarketBatchResult("DENY" if errors else "ALLOW", tuple(errors), tuple(rows), reconciled.to_dict(), digest)
