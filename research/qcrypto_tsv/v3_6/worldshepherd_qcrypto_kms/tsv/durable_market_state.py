"""Durable, tamper-evident market cursor persistence for WS-TSV-01.

The store is a local software control. It gives restart-survivable sequence continuity
and rollback/corruption detection for controlled testing. It is not a licensed market
feed, database HA guarantee, trusted timestamp, or independent attestation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional

from .market_data_adapter import FeedCursor, MarketDataMessage, AdapterResult, validate_market_message

DOMAIN = b"WS-TSV-DURABLE-CURSOR-STATE-V1\x00"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _cursor_from_dict(data: Mapping[str, Any]) -> FeedCursor:
    return FeedCursor(
        source_kind=str(data["source_kind"]),
        source_id=str(data["source_id"]),
        symbol=str(data["symbol"]),
        session_id=str(data["session_id"]),
        last_sequence=int(data["last_sequence"]),
        last_payload_sha256=str(data["last_payload_sha256"]),
        last_effective_at=datetime.fromisoformat(str(data["last_effective_at"]).replace("Z", "+00:00")),
    )


def cursor_key(source_kind: str, source_id: str, symbol: str, session_id: str) -> str:
    return "|".join((source_kind, source_id, symbol.upper(), session_id))


class DurableCursorStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class DurableStateSnapshot:
    schema: str
    revision: int
    previous_state_sha256: Optional[str]
    cursors: dict[str, dict]
    state_sha256: str
    claims_label: str = "LOCAL_DURABLE_CURSOR_STATE_ONLY_NOT_TRUSTED_EXTERNAL_ATTESTATION"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DurableApplyReceipt:
    decision: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    prior_revision: int
    new_revision: int
    prior_state_sha256: str
    new_state_sha256: str
    cursor_key: str
    adapter_result: dict
    receipt_sha256: str
    claims_label: str = "RESTART_SURVIVABLE_SEQUENCE_CONTROL_ONLY"

    def to_dict(self) -> dict:
        return asdict(self)


def _empty_snapshot() -> DurableStateSnapshot:
    material = {
        "schema": "WS-TSV-DURABLE-CURSOR-STATE-V1",
        "revision": 0,
        "previous_state_sha256": None,
        "cursors": {},
    }
    digest = hashlib.sha256(DOMAIN + _canon(material)).hexdigest()
    return DurableStateSnapshot(**material, state_sha256=digest)


def _snapshot_from_parts(revision: int, previous: Optional[str], cursors: Mapping[str, Mapping[str, Any]]) -> DurableStateSnapshot:
    material = {
        "schema": "WS-TSV-DURABLE-CURSOR-STATE-V1",
        "revision": int(revision),
        "previous_state_sha256": previous,
        "cursors": {str(k): dict(v) for k, v in sorted(cursors.items())},
    }
    digest = hashlib.sha256(DOMAIN + _canon(material)).hexdigest()
    return DurableStateSnapshot(**material, state_sha256=digest)


class DurableCursorStore:
    """Atomic JSON state store with content hashing and compare-and-swap support."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> DurableStateSnapshot:
        if not self.path.exists():
            return _empty_snapshot()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise DurableCursorStoreError(f"STATE_READ_OR_JSON_FAILED:{type(exc).__name__}") from exc
        required = {"schema", "revision", "previous_state_sha256", "cursors", "state_sha256"}
        if not required.issubset(data):
            raise DurableCursorStoreError("STATE_FIELDS_MISSING")
        if data["schema"] != "WS-TSV-DURABLE-CURSOR-STATE-V1":
            raise DurableCursorStoreError("STATE_SCHEMA_MISMATCH")
        rebuilt = _snapshot_from_parts(data["revision"], data["previous_state_sha256"], data["cursors"])
        if rebuilt.state_sha256 != data["state_sha256"]:
            raise DurableCursorStoreError("STATE_HASH_MISMATCH")
        return rebuilt

    def get_cursor(self, *, source_kind: str, source_id: str, symbol: str, session_id: str) -> Optional[FeedCursor]:
        snap = self.load()
        row = snap.cursors.get(cursor_key(source_kind, source_id, symbol, session_id))
        return _cursor_from_dict(row) if row else None

    def save_cursor(self, cursor: FeedCursor, *, expected_state_sha256: str) -> DurableStateSnapshot:
        current = self.load()
        if current.state_sha256 != expected_state_sha256:
            raise DurableCursorStoreError("STATE_COMPARE_AND_SWAP_MISMATCH")
        rows = dict(current.cursors)
        rows[cursor_key(cursor.source_kind, cursor.source_id, cursor.symbol, cursor.session_id)] = cursor.to_dict()
        nxt = _snapshot_from_parts(current.revision + 1, current.state_sha256, rows)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + f".tmp.{os.getpid()}")
        payload = json.dumps(nxt.to_dict(), sort_keys=True, indent=2) + "\n"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)
        try:
            dir_fd = os.open(str(self.path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
        return nxt


def apply_message_durably(
    store: DurableCursorStore,
    message: MarketDataMessage,
    *,
    expected_symbol: str,
    now: datetime,
    source_registry: Mapping[str, set[str] | frozenset[str]],
    max_age_seconds: int = 30,
    max_future_skew_seconds: int = 2,
    max_observation_delay_seconds: int = 10,
) -> DurableApplyReceipt:
    prior = store.load()
    key = cursor_key(message.source_kind, message.source_id, message.symbol, message.session_id)
    row = prior.cursors.get(key)
    cursor = _cursor_from_dict(row) if row else None
    result: AdapterResult = validate_market_message(
        message,
        expected_symbol=expected_symbol,
        now=now,
        source_registry=source_registry,
        max_age_seconds=max_age_seconds,
        max_future_skew_seconds=max_future_skew_seconds,
        max_observation_delay_seconds=max_observation_delay_seconds,
        cursor=cursor,
    )
    new = prior
    errors = list(result.errors)
    warnings = list(result.warnings)
    if result.decision != "DENY" and result.cursor is not None and "EXACT_DUPLICATE_IGNORED" not in result.warnings:
        try:
            new = store.save_cursor(result.cursor, expected_state_sha256=prior.state_sha256)
        except DurableCursorStoreError as exc:
            errors.append(str(exc))
    decision = "DENY" if errors else "ALLOW_WITH_WARNINGS" if warnings else "ALLOW"
    material = {
        "decision": decision,
        "errors": errors,
        "warnings": warnings,
        "prior_revision": prior.revision,
        "new_revision": new.revision,
        "prior_state_sha256": prior.state_sha256,
        "new_state_sha256": new.state_sha256,
        "cursor_key": key,
        "adapter_result": result.to_dict(),
    }
    digest = hashlib.sha256(b"WS-TSV-DURABLE-APPLY-RECEIPT-V1\x00" + _canon(material)).hexdigest()
    return DurableApplyReceipt(
        decision=decision,
        errors=tuple(errors),
        warnings=tuple(warnings),
        prior_revision=prior.revision,
        new_revision=new.revision,
        prior_state_sha256=prior.state_sha256,
        new_state_sha256=new.state_sha256,
        cursor_key=key,
        adapter_result=result.to_dict(),
        receipt_sha256=digest,
    )
