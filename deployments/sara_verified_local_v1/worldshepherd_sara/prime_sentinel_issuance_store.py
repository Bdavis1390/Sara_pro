from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .prime_configuration_custody import PrimeEnvironment


ISSUANCE_LEDGER_SCHEMA = "WS-PRIME-SENTINEL-ISSUANCE-LEDGER-V1"
ISSUANCE_EVENT_SCHEMA = "WS-PRIME-SENTINEL-ISSUANCE-EVENT-V1"
MAX_ISSUANCE_RECORDS = 4096
MAX_REQUEST_ID_CHARS = 128
REQUEST_ID_HEADER = "X-Prime-Sentinel-Request-Id"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
ZERO_HASH = "0" * 64


class PrimeSentinelIssuanceStoreError(RuntimeError):
    pass


class PrimeSentinelRequestConflict(PrimeSentinelIssuanceStoreError):
    pass


class PrimeSentinelLedgerFull(PrimeSentinelIssuanceStoreError):
    pass


@dataclass(frozen=True)
class IssuanceRecord:
    request_id: str
    request_digest_sha256: str
    state: str
    authorization_id: str
    prime_id: str
    target_environment: str
    lifetime_seconds: int
    key_id: str
    issued_at: str
    expires_at: str
    nonce: str
    signature_b64url: str | None
    assertion_json: str | None
    prepared_at: str
    signed_at: str | None

    def assertion_dict(self) -> dict[str, Any] | None:
        if not self.assertion_json:
            return None
        value = json.loads(self.assertion_json)
        if not isinstance(value, dict):
            raise PrimeSentinelIssuanceStoreError("stored assertion is not a JSON object")
        return value


@dataclass(frozen=True)
class ReconciliationEntry:
    authorization_id: str
    request_id: str
    classification: str
    sara_status: str | None
    reason: str | None = None


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PrimeSentinelIssuanceStoreError("stored timestamp is not timezone-aware")
    return parsed.astimezone(timezone.utc)


def validate_request_id(value: str) -> str:
    request_id = value.strip()
    if request_id != value or not _REQUEST_ID_PATTERN.fullmatch(request_id):
        raise PrimeSentinelIssuanceStoreError(
            f"{REQUEST_ID_HEADER} must be 8-{MAX_REQUEST_ID_CHARS} safe identifier characters"
        )
    return request_id


def request_digest(
    *,
    prime_id: str,
    target_environment: PrimeEnvironment | str,
    lifetime_seconds: int,
    key_id: str,
) -> str:
    environment = (
        target_environment.value
        if isinstance(target_environment, PrimeEnvironment)
        else str(target_environment)
    )
    payload = {
        "prime_id": prime_id,
        "target_environment": environment,
        "lifetime_seconds": int(lifetime_seconds),
        "key_id": key_id,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _row_to_record(row: sqlite3.Row) -> IssuanceRecord:
    return IssuanceRecord(**{key: row[key] for key in IssuanceRecord.__dataclass_fields__})


class PrimeSentinelIssuanceStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            raise PrimeSentinelIssuanceStoreError("PRIME SENTINEL data directory must be absolute")
        self._prepare_data_dir()
        self.db_path = self.data_dir / "issuance.db"
        self._reject_database_symlink()
        self._initialize()

    @classmethod
    def from_environment(cls) -> "PrimeSentinelIssuanceStore":
        value = os.getenv("PRIME_SENTINEL_DATA_DIR", "").strip()
        if not value:
            raise PrimeSentinelIssuanceStoreError("PRIME_SENTINEL_DATA_DIR is required")
        return cls(value)

    def _prepare_data_dir(self) -> None:
        if self.data_dir.exists():
            status = self.data_dir.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                raise PrimeSentinelIssuanceStoreError(
                    "PRIME SENTINEL data directory must be a real directory"
                )
        else:
            self.data_dir.mkdir(parents=True, mode=0o700)
            status = self.data_dir.lstat()
        if status.st_uid != os.geteuid():
            raise PrimeSentinelIssuanceStoreError(
                "PRIME SENTINEL data directory must be owned by the service UID"
            )
        if stat.S_IMODE(status.st_mode) & 0o022:
            raise PrimeSentinelIssuanceStoreError(
                "PRIME SENTINEL data directory must not be group/other writable"
            )

    def _reject_database_symlink(self) -> None:
        if self.db_path.exists() or self.db_path.is_symlink():
            status = self.db_path.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise PrimeSentinelIssuanceStoreError(
                    "PRIME SENTINEL issuance database must be a regular file"
                )
            if status.st_uid != os.geteuid():
                raise PrimeSentinelIssuanceStoreError(
                    "PRIME SENTINEL issuance database must be owned by the service UID"
                )

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self.db_path,
                timeout=5.0,
                isolation_level=None,
            )
        except sqlite3.Error as exc:
            raise PrimeSentinelIssuanceStoreError("unable to open issuance database") from exc
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
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
                CREATE TABLE IF NOT EXISTS issuance (
                    request_id TEXT PRIMARY KEY,
                    request_digest_sha256 TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('PREPARED', 'SIGNED')),
                    authorization_id TEXT NOT NULL UNIQUE,
                    prime_id TEXT NOT NULL,
                    target_environment TEXT NOT NULL,
                    lifetime_seconds INTEGER NOT NULL,
                    key_id TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    nonce TEXT NOT NULL UNIQUE,
                    signature_b64url TEXT,
                    assertion_json TEXT,
                    prepared_at TEXT NOT NULL,
                    signed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS issuance_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    schema TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    request_id TEXT NOT NULL,
                    event_type TEXT NOT NULL CHECK (event_type IN ('PREPARED', 'SIGNED')),
                    event_time TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    FOREIGN KEY(request_id) REFERENCES issuance(request_id)
                );
                CREATE INDEX IF NOT EXISTS idx_issuance_authorization_id
                    ON issuance(authorization_id);
                CREATE INDEX IF NOT EXISTS idx_issuance_state
                    ON issuance(state);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(name, value) VALUES('schema', ?)",
                (ISSUANCE_LEDGER_SCHEMA,),
            )
            schema_row = connection.execute(
                "SELECT value FROM metadata WHERE name='schema'"
            ).fetchone()
            if schema_row is None or schema_row["value"] != ISSUANCE_LEDGER_SCHEMA:
                raise PrimeSentinelIssuanceStoreError("issuance database schema mismatch")
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise PrimeSentinelIssuanceStoreError("issuance database integrity check failed")
        except sqlite3.Error as exc:
            raise PrimeSentinelIssuanceStoreError("unable to initialize issuance database") from exc
        finally:
            connection.close()
        try:
            self.db_path.chmod(0o600)
        except OSError as exc:
            raise PrimeSentinelIssuanceStoreError(
                "unable to restrict issuance database permissions"
            ) from exc

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        request_id: str,
        event_type: str,
        event_time: str,
        payload: dict[str, Any],
    ) -> None:
        previous = connection.execute(
            "SELECT event_hash FROM issuance_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous is not None else ZERO_HASH
        payload_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        event_id = f"PSEVT-{uuid4()}"
        canonical_event = {
            "schema": ISSUANCE_EVENT_SCHEMA,
            "event_id": event_id,
            "request_id": request_id,
            "event_type": event_type,
            "event_time": event_time,
            "payload_sha256": payload_sha256,
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(
            json.dumps(canonical_event, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        connection.execute(
            """
            INSERT INTO issuance_events(
                schema, event_id, request_id, event_type, event_time,
                payload_sha256, previous_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ISSUANCE_EVENT_SCHEMA,
                event_id,
                request_id,
                event_type,
                event_time,
                payload_sha256,
                previous_hash,
                event_hash,
            ),
        )

    def prepare_or_get(
        self,
        *,
        request_id: str,
        prime_id: str,
        target_environment: PrimeEnvironment,
        lifetime_seconds: int,
        key_id: str,
        now: datetime | None = None,
    ) -> IssuanceRecord:
        request_id = validate_request_id(request_id)
        digest = request_digest(
            prime_id=prime_id,
            target_environment=target_environment,
            lifetime_seconds=lifetime_seconds,
            key_id=key_id,
        )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            if existing is not None:
                record = _row_to_record(existing)
                if record.request_digest_sha256 != digest:
                    raise PrimeSentinelRequestConflict(
                        "request ID is already bound to different issuance parameters"
                    )
                connection.commit()
                return record

            count = connection.execute("SELECT COUNT(*) FROM issuance").fetchone()[0]
            if count >= MAX_ISSUANCE_RECORDS:
                raise PrimeSentinelLedgerFull("issuance ledger capacity reached")

            issued = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
            expires = issued + timedelta(seconds=lifetime_seconds)
            authorization_id = f"PSAUTH-{uuid4()}"
            nonce = os.urandom(24).hex()
            prepared_at = utc_iso(datetime.now(timezone.utc))
            values = (
                request_id,
                digest,
                "PREPARED",
                authorization_id,
                prime_id,
                target_environment.value,
                lifetime_seconds,
                key_id,
                utc_iso(issued),
                utc_iso(expires),
                nonce,
                prepared_at,
            )
            connection.execute(
                """
                INSERT INTO issuance(
                    request_id, request_digest_sha256, state, authorization_id,
                    prime_id, target_environment, lifetime_seconds, key_id,
                    issued_at, expires_at, nonce, prepared_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            self._append_event(
                connection,
                request_id=request_id,
                event_type="PREPARED",
                event_time=prepared_at,
                payload={
                    "authorization_id": authorization_id,
                    "prime_id": prime_id,
                    "target_environment": target_environment.value,
                    "lifetime_seconds": lifetime_seconds,
                    "key_id": key_id,
                    "issued_at": utc_iso(issued),
                    "expires_at": utc_iso(expires),
                    "nonce": nonce,
                    "request_digest_sha256": digest,
                },
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            assert row is not None
            return _row_to_record(row)
        except (PrimeSentinelIssuanceStoreError, sqlite3.Error):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def mark_signed(
        self,
        *,
        request_id: str,
        signature_b64url: str,
        assertion: dict[str, Any],
    ) -> IssuanceRecord:
        request_id = validate_request_id(request_id)
        assertion_json = json.dumps(assertion, sort_keys=True, separators=(",", ":"))
        signed_at = utc_iso(datetime.now(timezone.utc))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            if row is None:
                raise PrimeSentinelIssuanceStoreError("issuance request is not prepared")
            record = _row_to_record(row)
            if record.state == "SIGNED":
                if record.assertion_json != assertion_json:
                    raise PrimeSentinelIssuanceStoreError(
                        "stored signed assertion differs from retry assertion"
                    )
                connection.commit()
                return record
            connection.execute(
                """
                UPDATE issuance
                SET state='SIGNED', signature_b64url=?, assertion_json=?, signed_at=?
                WHERE request_id=? AND state='PREPARED'
                """,
                (signature_b64url, assertion_json, signed_at, request_id),
            )
            self._append_event(
                connection,
                request_id=request_id,
                event_type="SIGNED",
                event_time=signed_at,
                payload={
                    "authorization_id": record.authorization_id,
                    "signature_sha256": hashlib.sha256(
                        signature_b64url.encode("ascii")
                    ).hexdigest(),
                    "assertion_sha256": hashlib.sha256(
                        assertion_json.encode("utf-8")
                    ).hexdigest(),
                },
            )
            connection.commit()
            updated = connection.execute(
                "SELECT * FROM issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            assert updated is not None
            return _row_to_record(updated)
        except (PrimeSentinelIssuanceStoreError, sqlite3.Error):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, request_id: str) -> IssuanceRecord | None:
        request_id = validate_request_id(request_id)
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            return _row_to_record(row) if row is not None else None
        finally:
            connection.close()

    def signed_records(self) -> list[IssuanceRecord]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM issuance WHERE state='SIGNED' ORDER BY prepared_at, request_id"
            ).fetchall()
            return [_row_to_record(row) for row in rows]
        finally:
            connection.close()

    def verify_event_chain(self) -> tuple[bool, int]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM issuance_events ORDER BY sequence"
            ).fetchall()
        finally:
            connection.close()
        previous_hash = ZERO_HASH
        for row in rows:
            if row["schema"] != ISSUANCE_EVENT_SCHEMA or row["previous_hash"] != previous_hash:
                return False, len(rows)
            canonical_event = {
                "schema": row["schema"],
                "event_id": row["event_id"],
                "request_id": row["request_id"],
                "event_type": row["event_type"],
                "event_time": row["event_time"],
                "payload_sha256": row["payload_sha256"],
                "previous_hash": row["previous_hash"],
            }
            expected = hashlib.sha256(
                json.dumps(canonical_event, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if row["event_hash"] != expected:
                return False, len(rows)
            previous_hash = row["event_hash"]
        return True, len(rows)

    def health(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            quick = connection.execute("PRAGMA quick_check").fetchone()
            total = connection.execute("SELECT COUNT(*) FROM issuance").fetchone()[0]
            prepared = connection.execute(
                "SELECT COUNT(*) FROM issuance WHERE state='PREPARED'"
            ).fetchone()[0]
            signed = total - prepared
        except sqlite3.Error as exc:
            raise PrimeSentinelIssuanceStoreError("issuance database health check failed") from exc
        finally:
            connection.close()
        chain_ok, event_count = self.verify_event_chain()
        return {
            "ok": bool(quick and quick[0] == "ok" and chain_ok),
            "records": total,
            "prepared": prepared,
            "signed": signed,
            "events": event_count,
            "capacity": MAX_ISSUANCE_RECORDS,
            "event_chain_ok": chain_ok,
        }


def reconcile_signed_records(
    records: list[IssuanceRecord],
    sara_registry: dict[str, Any],
) -> list[ReconciliationEntry]:
    raw = sara_registry.get("PRIME_SENTINEL_AUTHORIZATIONS", {})
    if not isinstance(raw, dict):
        raise PrimeSentinelIssuanceStoreError(
            "SARA PRIME_SENTINEL_AUTHORIZATIONS registry value is not an object"
        )
    results: list[ReconciliationEntry] = []
    for record in records:
        if record.state != "SIGNED":
            continue
        sara = raw.get(record.authorization_id)
        if sara is None:
            results.append(
                ReconciliationEntry(
                    authorization_id=record.authorization_id,
                    request_id=record.request_id,
                    classification="ISSUED_NOT_PRESENTED",
                    sara_status=None,
                )
            )
            continue
        if not isinstance(sara, dict):
            results.append(
                ReconciliationEntry(
                    authorization_id=record.authorization_id,
                    request_id=record.request_id,
                    classification="INCONSISTENT",
                    sara_status=None,
                    reason="SARA authorization record is not an object",
                )
            )
            continue
        status = sara.get("status")
        mismatches: list[str] = []
        if sara.get("prime_id") != record.prime_id:
            mismatches.append("prime_id")
        if sara.get("target_environment") != record.target_environment:
            mismatches.append("target_environment")
        if sara.get("key_id") != record.key_id:
            mismatches.append("key_id")
        if status not in {"VERIFIED", "CONSUMED", "SUPERSEDED"}:
            mismatches.append("status")
        if mismatches:
            results.append(
                ReconciliationEntry(
                    authorization_id=record.authorization_id,
                    request_id=record.request_id,
                    classification="INCONSISTENT",
                    sara_status=str(status) if status is not None else None,
                    reason="mismatch: " + ",".join(mismatches),
                )
            )
        else:
            results.append(
                ReconciliationEntry(
                    authorization_id=record.authorization_id,
                    request_id=record.request_id,
                    classification=str(status),
                    sara_status=str(status),
                )
            )
    return results
