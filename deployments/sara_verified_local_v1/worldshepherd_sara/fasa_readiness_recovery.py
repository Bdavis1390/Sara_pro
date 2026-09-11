from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .fasa_runtime_gate import (
    FASA_EXECUTION_READINESS_RECORD_SCHEMA,
    FASA_EXECUTION_READINESS_REGISTRY_KEY,
    _readiness_record_valid,
)
from .storage import DurableStore


FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY = "FASA_EXECUTION_READINESS_EXPIRY"
FASA_EXECUTION_READINESS_EXPIRY_SCHEMA = "WS-FASA-EXECUTION-READINESS-EXPIRY-V1"
FASA_READINESS_RECOVERY_SCHEMA = "WS-FASA-READINESS-RECOVERY-V1"
MAX_FASA_EXECUTION_READINESS_EXPIRY_RECORDS = 32
_LIVE_STATES = frozenset({"WAITING_ECHO", "READY"})
_TERMINAL_STATES = frozenset({"CONSUMED"})


class FASAReadinessRecoveryError(ValueError):
    pass


class FASAReadinessRecoveryResult(BaseModel):
    """Result of one restart/readiness reconciliation pass.

    Recovery is intentionally non-promoting: it can preserve live state or move
    expired live state to a terminal tombstone, but it cannot create READY,
    recreate approval authority, or reverse CONSUMED state.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal[FASA_READINESS_RECOVERY_SCHEMA] = FASA_READINESS_RECOVERY_SCHEMA
    recovered_at: datetime
    live_preserved: int = Field(ge=0)
    consumed_preserved: int = Field(ge=0)
    expired_tombstoned: int = Field(ge=0)
    tombstones_retained: int = Field(ge=0)
    tombstones_evicted: int = Field(ge=0)


def _recovery_time(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise FASAReadinessRecoveryError("recovery timestamp must be timezone-aware")
    return current.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: Any, *, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise FASAReadinessRecoveryError(f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FASAReadinessRecoveryError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise FASAReadinessRecoveryError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _expiry_map(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY, {})
    if not isinstance(raw, dict):
        raise FASAReadinessRecoveryError(
            f"{FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY} must be a JSON object"
        )
    records = dict(raw)
    for transition_id, entry in records.items():
        if not isinstance(transition_id, str) or not transition_id or not isinstance(entry, dict):
            raise FASAReadinessRecoveryError("FASA readiness expiry registry is malformed")
        if entry.get("schema") != FASA_EXECUTION_READINESS_EXPIRY_SCHEMA:
            raise FASAReadinessRecoveryError("FASA readiness expiry registry is malformed")
        if entry.get("transition_id") != transition_id:
            raise FASAReadinessRecoveryError("FASA readiness expiry registry is malformed")
        if entry.get("expired_from") not in _LIVE_STATES:
            raise FASAReadinessRecoveryError("FASA readiness expiry registry is malformed")
        _parse_utc(entry.get("expired_at"), label="readiness expired_at")
        _parse_utc(entry.get("original_expires_at"), label="readiness original_expires_at")
    return records


def _tombstone(transition_id: str, entry: dict[str, Any], recovered_at: datetime) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": FASA_EXECUTION_READINESS_EXPIRY_SCHEMA,
        "transition_id": transition_id,
        "expired_from": entry["status"],
        "expired_at": _utc_iso(recovered_at),
        "original_expires_at": entry["expires_at"],
        "readiness_schema": entry.get("schema", FASA_EXECUTION_READINESS_RECORD_SCHEMA),
        "action_id": entry["action_id"],
        "authorization_id": entry["authorization_id"],
        "provenance_event_id": entry["provenance_event_id"],
        "decision_digest_sha256": entry["decision_digest_sha256"],
        "created_at": entry["created_at"],
    }
    if entry.get("echo_semantic_sha256"):
        result["echo_semantic_sha256"] = entry["echo_semantic_sha256"]
    if entry.get("echo_acknowledged_at"):
        result["echo_acknowledged_at"] = entry["echo_acknowledged_at"]
    return result


def recover_execution_readiness_after_restart(
    store: DurableStore,
    *,
    now: datetime | None = None,
) -> FASAReadinessRecoveryResult:
    """Reconcile durable FASA readiness after restart without promoting authority.

    Expired WAITING_ECHO or READY records are atomically moved to a bounded
    terminal tombstone registry. Valid live records and CONSUMED records are
    preserved exactly. Unknown or malformed readiness state fails closed.

    This function never acknowledges ECHO, drains provenance, creates READY,
    creates approval, or executes an external action. If no state transition or
    retention trim is needed, recovery is read-only and does not create empty
    protected registry namespaces.
    """

    recovered_at = _recovery_time(now)

    def operation(snapshot: dict[str, Any]):
        raw = snapshot.get(FASA_EXECUTION_READINESS_REGISTRY_KEY, {})
        if not isinstance(raw, dict):
            raise FASAReadinessRecoveryError(
                f"{FASA_EXECUTION_READINESS_REGISTRY_KEY} must be a JSON object"
            )
        readiness = dict(raw)
        tombstones = _expiry_map(snapshot)

        live_preserved = 0
        consumed_preserved = 0
        expired_tombstoned = 0

        for transition_id, entry in list(readiness.items()):
            if not _readiness_record_valid(transition_id, entry):
                raise FASAReadinessRecoveryError(
                    "FASA execution-readiness registry is malformed; recovery aborted"
                )
            assert isinstance(entry, dict)
            status = entry["status"]
            if status in _TERMINAL_STATES:
                consumed_preserved += 1
                continue
            if status not in _LIVE_STATES:
                raise FASAReadinessRecoveryError(
                    "unsupported FASA execution-readiness state; recovery aborted"
                )

            expires_at = _parse_utc(entry.get("expires_at"), label="readiness expires_at")
            if recovered_at < expires_at:
                live_preserved += 1
                continue

            if transition_id in tombstones:
                raise FASAReadinessRecoveryError(
                    "duplicate readiness expiry tombstone would overwrite evidence"
                )
            tombstones[transition_id] = _tombstone(
                transition_id,
                entry,
                recovered_at,
            )
            readiness.pop(transition_id)
            expired_tombstoned += 1

        tombstones_evicted = 0
        if len(tombstones) > MAX_FASA_EXECUTION_READINESS_EXPIRY_RECORDS:
            ordered = sorted(
                tombstones.items(),
                key=lambda item: (str(item[1].get("expired_at", "")), item[0]),
            )
            remove_count = len(tombstones) - MAX_FASA_EXECUTION_READINESS_EXPIRY_RECORDS
            for transition_id, _entry in ordered[:remove_count]:
                tombstones.pop(transition_id, None)
                tombstones_evicted += 1

        patch: dict[str, Any] | None = None
        if expired_tombstoned or tombstones_evicted:
            patch = {
                FASA_EXECUTION_READINESS_REGISTRY_KEY: readiness,
                FASA_EXECUTION_READINESS_EXPIRY_REGISTRY_KEY: tombstones,
            }
        result = FASAReadinessRecoveryResult(
            recovered_at=recovered_at,
            live_preserved=live_preserved,
            consumed_preserved=consumed_preserved,
            expired_tombstoned=expired_tombstoned,
            tombstones_retained=len(tombstones),
            tombstones_evicted=tombstones_evicted,
        )
        return patch, result

    return store.transact_registry(operation)
