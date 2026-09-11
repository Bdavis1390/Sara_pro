from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AuditRecord


ECHO_STORE_SCHEMA = "WS-ECHO-PERSISTENCE-V1"
MAX_ECHO_EVENTS = 4096
MAX_EVENT_ID_CHARS = 200
_EVENT_ID_PATTERN = re.compile(r"^SARA-EVENT-[A-Za-z0-9._:-]{1,180}$")


class EchoEventStoreError(RuntimeError):
    pass


class EchoEventConflict(EchoEventStoreError):
    pass


class EchoStoreFull(EchoEventStoreError):
    pass


@dataclass(frozen=True)
class EchoStoredEvent:
    event_id: str
    semantic_sha256: str
    event: str
    actor: str
    payload_json: str
    first_audit_timestamp: str
    last_audit_timestamp: str
    first_ingested_at: str
    last_seen_at: str
    delivery_count: int

    def payload(self) -> dict[str, Any]:
        value = json.loads(self.payload_json)
        if not isinstance(value, dict):
            raise EchoEventStoreError("stored ECHO payload is not a JSON object")
        return value


@dataclass(frozen=True)
class EchoIngestResult:
    outcome: str
    record: EchoStoredEvent


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_id(record: AuditRecord) -> str:
    value = record.payload.get("_outbox_event_id")
    if not isinstance(value, str) or not _EVENT_ID_PATTERN.fullmatch(value):
        raise EchoEventStoreError(
            f"audit payload must contain a valid _outbox_event_id up to {MAX_EVENT_ID_CHARS} characters"
        )
    if record.payload.get("_delivery_semantics") != "AT_LEAST_ONCE":
        raise EchoEventStoreError("audit payload must declare AT_LEAST_ONCE delivery semantics")
    return value


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EchoEventStoreError("audit timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise EchoEventStoreError("audit timestamp must be timezone-aware")


def semantic_document(record: AuditRecord) -> dict[str, Any]:
    if not record.event or len(record.event) > 128:
        raise EchoEventStoreError("audit event must be 1-128 characters")
    if not record.actor or len(record.actor) > 128:
        raise EchoEventStoreError("audit actor must be 1-128 characters")
    _validate_timestamp(record.timestamp)
    _event_id(record)
    return {
        "event": record.event,
        "actor": record.actor,
        "payload": record.payload,
    }


def semantic_sha256(record: AuditRecord) -> str:
    data = json.dumps(
        semantic_document(record),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _row_to_record(row: sqlite3.Row) -> EchoStoredEvent:
    return EchoStoredEvent(**{key: row[key] for key in EchoStoredEvent.__dataclass_fields__})


class EchoEventStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            raise EchoEventStoreError("ECHO data directory must be absolute")
        self._prepare_data_dir()
        self.db_path = self.data_dir / "echo-events.db"
        self._reject_database_symlink()
        self._initialize()

    @classmethod
    def from_environment(cls) -> "EchoEventStore":
        value = os.getenv("ECHO_DATA_DIR", "").strip()
        if not value:
            raise EchoEventStoreError("ECHO_DATA_DIR is required")
        return cls(value)

    def _prepare_data_dir(self) -> None:
        if self.data_dir.exists():
            status = self.data_dir.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                raise EchoEventStoreError("ECHO data directory must be a real directory")
        else:
            self.data_dir.mkdir(parents=True, mode=0o700)
            status = self.data_dir.lstat()
        if status.st_uid != os.geteuid():
            raise EchoEventStoreError("ECHO data directory must be owned by the service UID")
        mode = stat.S_IMODE(status.st_mode)
        if mode != 0o700:
            try:
                self.data_dir.chmod(0o700)
            except OSError as exc:
                raise EchoEventStoreError("unable to secure ECHO data directory") from exc
            mode = stat.S_IMODE(self.data_dir.stat().st_mode)
            if mode != 0o700:
                raise EchoEventStoreError("ECHO data directory must be mode 0700")

    def _reject_database_symlink(self) -> None:
        if self.db_path.exists() or self.db_path.is_symlink():
            status = self.db_path.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise EchoEventStoreError("ECHO database must be a regular file")
            if status.st_uid != os.geteuid():
                raise EchoEventStoreError("ECHO database must be owned by the service UID")

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self.db_path,
                timeout=5.0,
                isolation_level=None,
            )
        except sqlite3.Error as exc:
            raise EchoEventStoreError("unable to open ECHO database") from exc
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    semantic_sha256 TEXT NOT NULL,
                    event TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    first_audit_timestamp TEXT NOT NULL,
                    last_audit_timestamp TEXT NOT NULL,
                    first_ingested_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    delivery_count INTEGER NOT NULL CHECK(delivery_count >= 1)
                );
                CREATE TABLE IF NOT EXISTS conflicts (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    stored_semantic_sha256 TEXT NOT NULL,
                    observed_semantic_sha256 TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_echo_event_seen
                    ON events(last_seen_at);
                CREATE INDEX IF NOT EXISTS idx_echo_conflict_event
                    ON conflicts(event_id);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(name, value) VALUES('schema', ?)",
                (ECHO_STORE_SCHEMA,),
            )
            row = connection.execute(
                "SELECT value FROM metadata WHERE name='schema'"
            ).fetchone()
            if row is None or row["value"] != ECHO_STORE_SCHEMA:
                raise EchoEventStoreError("ECHO database schema mismatch")
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise EchoEventStoreError("ECHO database integrity check failed")
        except sqlite3.Error as exc:
            raise EchoEventStoreError("unable to initialize ECHO database") from exc
        finally:
            connection.close()
        try:
            self.db_path.chmod(0o600)
        except OSError as exc:
            raise EchoEventStoreError("unable to secure ECHO database") from exc

    def ingest(self, record: AuditRecord) -> EchoIngestResult:
        event_id = _event_id(record)
        digest = semantic_sha256(record)
        payload_json = json.dumps(record.payload, sort_keys=True, separators=(",", ":"))
        now = _utc_now()
        conflict: tuple[str, str] | None = None
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM events WHERE event_id=?", (event_id,)
            ).fetchone()
            if row is not None:
                existing = _row_to_record(row)
                if existing.semantic_sha256 != digest:
                    connection.execute(
                        """
                        INSERT INTO conflicts(
                            event_id, stored_semantic_sha256,
                            observed_semantic_sha256, observed_at
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (event_id, existing.semantic_sha256, digest, now),
                    )
                    connection.commit()
                    conflict = (existing.semantic_sha256, digest)
                else:
                    connection.execute(
                        """
                        UPDATE events
                        SET last_audit_timestamp=?, last_seen_at=?,
                            delivery_count=delivery_count+1
                        WHERE event_id=?
                        """,
                        (record.timestamp, now, event_id),
                    )
                    connection.commit()
                    updated = connection.execute(
                        "SELECT * FROM events WHERE event_id=?", (event_id,)
                    ).fetchone()
                    assert updated is not None
                    return EchoIngestResult("DEDUPLICATED", _row_to_record(updated))
            else:
                count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                if count >= MAX_ECHO_EVENTS:
                    raise EchoStoreFull("ECHO event-store capacity reached")
                connection.execute(
                    """
                    INSERT INTO events(
                        event_id, semantic_sha256, event, actor, payload_json,
                        first_audit_timestamp, last_audit_timestamp,
                        first_ingested_at, last_seen_at, delivery_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        event_id,
                        digest,
                        record.event,
                        record.actor,
                        payload_json,
                        record.timestamp,
                        record.timestamp,
                        now,
                        now,
                    ),
                )
                connection.commit()
                inserted = connection.execute(
                    "SELECT * FROM events WHERE event_id=?", (event_id,)
                ).fetchone()
                assert inserted is not None
                return EchoIngestResult("STORED", _row_to_record(inserted))
        except (sqlite3.Error, EchoEventStoreError):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()
        if conflict is not None:
            raise EchoEventConflict(
                "stable event ID was replayed with different semantic content"
            )
        raise EchoEventStoreError("unexpected ECHO ingest state")

    def get(self, event_id: str) -> EchoStoredEvent | None:
        if not isinstance(event_id, str) or not _EVENT_ID_PATTERN.fullmatch(event_id):
            raise EchoEventStoreError("invalid ECHO event ID")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM events WHERE event_id=?", (event_id,)
            ).fetchone()
            return None if row is None else _row_to_record(row)
        finally:
            connection.close()

    def all_records(self) -> list[EchoStoredEvent]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM events ORDER BY first_ingested_at, event_id"
            ).fetchall()
            return [_row_to_record(row) for row in rows]
        finally:
            connection.close()

    def reconcile(self, source_records: list[AuditRecord]) -> dict[str, Any]:
        source: dict[str, tuple[str, AuditRecord]] = {}
        for record in source_records:
            event_id = _event_id(record)
            digest = semantic_sha256(record)
            prior = source.get(event_id)
            if prior is not None and prior[0] != digest:
                raise EchoEventConflict(
                    "provided SARA source window contains one event ID with conflicting content"
                )
            source[event_id] = (digest, record)

        stored = {record.event_id: record for record in self.all_records()}
        entries: list[dict[str, Any]] = []
        for event_id in sorted(source):
            digest, _record = source[event_id]
            local = stored.get(event_id)
            if local is None:
                classification = "SARA_ONLY"
            elif local.semantic_sha256 != digest:
                classification = "PAYLOAD_MISMATCH"
            else:
                classification = "MATCHED"
            entries.append({"event_id": event_id, "classification": classification})
        for event_id in sorted(set(stored) - set(source)):
            entries.append({"event_id": event_id, "classification": "ECHO_ONLY"})

        counts: dict[str, int] = {}
        for entry in entries:
            name = str(entry["classification"])
            counts[name] = counts.get(name, 0) + 1
        return {
            "schema": "WS-ECHO-SARA-RECONCILIATION-V1",
            "scope": "PROVIDED_SARA_AUDIT_WINDOW",
            "counts": counts,
            "entries": entries,
            "claims_boundary": (
                "Window-scoped software reconciliation only; bounded SARA retention and "
                "transport history do not establish globally complete or exactly-once delivery."
            ),
        }

    def health(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            quick = connection.execute("PRAGMA quick_check").fetchone()
            quick_ok = quick is not None and quick[0] == "ok"
            rows = connection.execute("SELECT * FROM events").fetchall()
            conflicts = connection.execute("SELECT COUNT(*) FROM conflicts").fetchone()[0]
        except sqlite3.Error as exc:
            raise EchoEventStoreError("unable to inspect ECHO database") from exc
        finally:
            connection.close()

        malformed = 0
        for row in rows:
            try:
                record = _row_to_record(row)
                payload = json.loads(record.payload_json)
                audit = AuditRecord(
                    timestamp=record.first_audit_timestamp,
                    event=record.event,
                    actor=record.actor,
                    payload=payload,
                )
                if _event_id(audit) != record.event_id:
                    malformed += 1
                elif semantic_sha256(audit) != record.semantic_sha256:
                    malformed += 1
                elif record.delivery_count < 1:
                    malformed += 1
            except (ValueError, TypeError, json.JSONDecodeError, EchoEventStoreError):
                malformed += 1
        return {
            "ok": quick_ok and malformed == 0 and len(rows) <= MAX_ECHO_EVENTS,
            "sqlite_quick_check": "ok" if quick_ok else "failed",
            "stored_events": len(rows),
            "capacity": MAX_ECHO_EVENTS,
            "semantic_integrity_errors": malformed,
            "rejected_conflicts": conflicts,
        }
