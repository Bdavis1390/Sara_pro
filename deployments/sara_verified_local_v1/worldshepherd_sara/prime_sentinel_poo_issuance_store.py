from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .prime_sentinel_issuance_store import validate_request_id


POO_ISSUANCE_LEDGER_SCHEMA = "WS-PRIME-SENTINEL-POO-ISSUANCE-LEDGER-V1"
MAX_POO_ISSUANCE_RECORDS = 4096


class PrimeSentinelPoOIssuanceStoreError(RuntimeError):
    pass


class PrimeSentinelPoORequestConflict(PrimeSentinelPoOIssuanceStoreError):
    pass


class PrimeSentinelPoOLedgerFull(PrimeSentinelPoOIssuanceStoreError):
    pass


@dataclass(frozen=True)
class PoOIssuanceRecord:
    request_id: str
    request_digest_sha256: str
    state: str
    authorization_id: str
    asset_id: str
    governance_projection_digest: str
    source_decision_digest: str
    expected_registry_digest: str
    candidate_registry_digest: str
    candidate_state_digest: str
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
            raise PrimeSentinelPoOIssuanceStoreError("stored assertion is not a JSON object")
        return value


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PrimeSentinelPoOIssuanceStoreError("stored timestamp is not timezone-aware")
    return parsed.astimezone(timezone.utc)


def poo_request_digest(
    *,
    asset_id: str,
    governance_projection_digest: str,
    source_decision_digest: str,
    expected_registry_digest: str,
    candidate_registry_digest: str,
    candidate_state_digest: str,
    lifetime_seconds: int,
    key_id: str,
) -> str:
    payload = {
        "asset_id": asset_id,
        "governance_projection_digest": governance_projection_digest,
        "source_decision_digest": source_decision_digest,
        "expected_registry_digest": expected_registry_digest,
        "candidate_registry_digest": candidate_registry_digest,
        "candidate_state_digest": candidate_state_digest,
        "lifetime_seconds": int(lifetime_seconds),
        "key_id": key_id,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _row_to_record(row: sqlite3.Row) -> PoOIssuanceRecord:
    return PoOIssuanceRecord(
        **{key: row[key] for key in PoOIssuanceRecord.__dataclass_fields__}
    )


class PrimeSentinelPoOIssuanceStore:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            raise PrimeSentinelPoOIssuanceStoreError(
                "PRIME SENTINEL PoO data directory must be absolute"
            )
        self._prepare_data_dir()
        self.db_path = self.data_dir / "poo-issuance.db"
        self._reject_database_symlink()
        self._initialize()

    @classmethod
    def from_environment(cls) -> "PrimeSentinelPoOIssuanceStore":
        value = os.getenv("PRIME_SENTINEL_DATA_DIR", "").strip()
        if not value:
            raise PrimeSentinelPoOIssuanceStoreError("PRIME_SENTINEL_DATA_DIR is required")
        return cls(value)

    def _prepare_data_dir(self) -> None:
        if self.data_dir.exists():
            status = self.data_dir.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                raise PrimeSentinelPoOIssuanceStoreError(
                    "PRIME SENTINEL PoO data directory must be a real directory"
                )
        else:
            self.data_dir.mkdir(parents=True, mode=0o700)
            status = self.data_dir.lstat()
        if status.st_uid != os.geteuid():
            raise PrimeSentinelPoOIssuanceStoreError(
                "PRIME SENTINEL PoO data directory must be owned by the service UID"
            )
        if stat.S_IMODE(status.st_mode) & 0o022:
            raise PrimeSentinelPoOIssuanceStoreError(
                "PRIME SENTINEL PoO data directory must not be group/other writable"
            )

    def _reject_database_symlink(self) -> None:
        if self.db_path.exists() or self.db_path.is_symlink():
            status = self.db_path.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise PrimeSentinelPoOIssuanceStoreError(
                    "PRIME SENTINEL PoO issuance database must be a regular file"
                )
            if status.st_uid != os.geteuid():
                raise PrimeSentinelPoOIssuanceStoreError(
                    "PRIME SENTINEL PoO issuance database must be owned by the service UID"
                )

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        except sqlite3.Error as exc:
            raise PrimeSentinelPoOIssuanceStoreError(
                "unable to open PRIME SENTINEL PoO issuance database"
            ) from exc
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
                CREATE TABLE IF NOT EXISTS poo_issuance (
                    request_id TEXT PRIMARY KEY,
                    request_digest_sha256 TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('PREPARED', 'SIGNED')),
                    authorization_id TEXT NOT NULL UNIQUE,
                    asset_id TEXT NOT NULL,
                    governance_projection_digest TEXT NOT NULL,
                    source_decision_digest TEXT NOT NULL,
                    expected_registry_digest TEXT NOT NULL,
                    candidate_registry_digest TEXT NOT NULL,
                    candidate_state_digest TEXT NOT NULL,
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
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(name, value) VALUES('schema', ?)",
                (POO_ISSUANCE_LEDGER_SCHEMA,),
            )
            row = connection.execute(
                "SELECT value FROM metadata WHERE name='schema'"
            ).fetchone()
            if row is None or row["value"] != POO_ISSUANCE_LEDGER_SCHEMA:
                raise PrimeSentinelPoOIssuanceStoreError("PoO issuance database schema mismatch")
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise PrimeSentinelPoOIssuanceStoreError("PoO issuance database integrity check failed")
        except sqlite3.Error as exc:
            raise PrimeSentinelPoOIssuanceStoreError(
                "unable to initialize PRIME SENTINEL PoO issuance database"
            ) from exc
        finally:
            connection.close()
        self.db_path.chmod(0o600)

    def prepare_or_get(
        self,
        *,
        request_id: str,
        asset_id: str,
        governance_projection_digest: str,
        source_decision_digest: str,
        expected_registry_digest: str,
        candidate_registry_digest: str,
        candidate_state_digest: str,
        lifetime_seconds: int,
        key_id: str,
        now: datetime | None = None,
    ) -> PoOIssuanceRecord:
        request_id = validate_request_id(request_id)
        digest = poo_request_digest(
            asset_id=asset_id,
            governance_projection_digest=governance_projection_digest,
            source_decision_digest=source_decision_digest,
            expected_registry_digest=expected_registry_digest,
            candidate_registry_digest=candidate_registry_digest,
            candidate_state_digest=candidate_state_digest,
            lifetime_seconds=lifetime_seconds,
            key_id=key_id,
        )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM poo_issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            if existing is not None:
                record = _row_to_record(existing)
                if record.request_digest_sha256 != digest:
                    raise PrimeSentinelPoORequestConflict(
                        "request ID is already bound to different PoO authorization scope"
                    )
                connection.commit()
                return record

            count = connection.execute("SELECT COUNT(*) FROM poo_issuance").fetchone()[0]
            if count >= MAX_POO_ISSUANCE_RECORDS:
                raise PrimeSentinelPoOLedgerFull("PoO issuance ledger capacity reached")

            issued = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
            expires = issued + timedelta(seconds=lifetime_seconds)
            authorization_id = f"PSPOOAUTH-{uuid4()}"
            nonce = os.urandom(24).hex()
            prepared_at = utc_iso(datetime.now(timezone.utc))
            connection.execute(
                """
                INSERT INTO poo_issuance(
                    request_id, request_digest_sha256, state, authorization_id,
                    asset_id, governance_projection_digest, source_decision_digest,
                    expected_registry_digest, candidate_registry_digest,
                    candidate_state_digest, lifetime_seconds, key_id, issued_at,
                    expires_at, nonce, prepared_at
                ) VALUES (?, ?, 'PREPARED', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    digest,
                    authorization_id,
                    asset_id,
                    governance_projection_digest,
                    source_decision_digest,
                    expected_registry_digest,
                    candidate_registry_digest,
                    candidate_state_digest,
                    lifetime_seconds,
                    key_id,
                    utc_iso(issued),
                    utc_iso(expires),
                    nonce,
                    prepared_at,
                ),
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM poo_issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            assert row is not None
            return _row_to_record(row)
        except (PrimeSentinelPoOIssuanceStoreError, sqlite3.Error):
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
    ) -> PoOIssuanceRecord:
        request_id = validate_request_id(request_id)
        assertion_json = json.dumps(assertion, sort_keys=True, separators=(",", ":"))
        signed_at = utc_iso(datetime.now(timezone.utc))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM poo_issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            if row is None:
                raise PrimeSentinelPoOIssuanceStoreError("PoO issuance request is not prepared")
            record = _row_to_record(row)
            if record.state == "SIGNED":
                if record.assertion_json != assertion_json:
                    raise PrimeSentinelPoOIssuanceStoreError(
                        "stored signed PoO assertion differs from retry assertion"
                    )
                connection.commit()
                return record
            connection.execute(
                """
                UPDATE poo_issuance
                SET state='SIGNED', signature_b64url=?, assertion_json=?, signed_at=?
                WHERE request_id=? AND state='PREPARED'
                """,
                (signature_b64url, assertion_json, signed_at, request_id),
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM poo_issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            assert row is not None
            return _row_to_record(row)
        except (PrimeSentinelPoOIssuanceStoreError, sqlite3.Error):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, request_id: str) -> PoOIssuanceRecord | None:
        request_id = validate_request_id(request_id)
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM poo_issuance WHERE request_id = ?", (request_id,)
            ).fetchone()
            return _row_to_record(row) if row is not None else None
        finally:
            connection.close()

    def health(self) -> dict[str, object]:
        connection = self._connect()
        try:
            quick = connection.execute("PRAGMA quick_check").fetchone()
            records = int(connection.execute("SELECT COUNT(*) FROM poo_issuance").fetchone()[0])
            signed = int(
                connection.execute(
                    "SELECT COUNT(*) FROM poo_issuance WHERE state='SIGNED'"
                ).fetchone()[0]
            )
            prepared = records - signed
        finally:
            connection.close()
        ok = quick is not None and quick[0] == "ok" and records <= MAX_POO_ISSUANCE_RECORDS
        return {
            "ok": ok,
            "schema": POO_ISSUANCE_LEDGER_SCHEMA,
            "records": records,
            "signed": signed,
            "prepared": prepared,
            "capacity": MAX_POO_ISSUANCE_RECORDS,
        }
