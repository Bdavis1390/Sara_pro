"""Local, single-host reservation ledger for verified scientific grants.

The ledger persists already-verified authorization ID and nonce consumption
with SQLite UNIQUE constraints and BEGIN IMMEDIATE transactions. It is not a
remote authority, signer, tamper-proof store, global distributed replay guard,
or sufficient proof of authorization by itself.
"""
from __future__ import annotations

import os
import re
import sqlite3
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LEDGER_SCHEMA = "WS-SCIENTIFIC-LOCAL-GRANT-LEDGER-V1"
IDENT = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
NONCE = re.compile(r"[A-Za-z0-9_-]{16,128}\Z")


class LocalGrantLedgerError(ValueError):
    pass


def _string(value: Any, label: str, pattern=IDENT) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise LocalGrantLedgerError(f"invalid {label}")
    return value


class LocalGrantLedger:
    """Local persistent fail-closed duplicate reservation gate.

    This protects a stable local store from ordinary concurrent claims. A
    privileged actor can restore old database backups or replay a grant on
    another machine. Do not use for real SARA operation without independent
    monotonic/event custody and an authorized execution adapter.
    """

    def __init__(self, directory: str | Path):
        requested = Path(directory)
        if not requested.is_absolute():
            raise LocalGrantLedgerError("ledger directory must be absolute")
        if requested.is_symlink():
            raise LocalGrantLedgerError("ledger directory must not be symlinked")
        requested.mkdir(parents=True, mode=0o700, exist_ok=True)
        mode = requested.lstat()
        if not stat.S_ISDIR(mode.st_mode) or stat.S_ISLNK(mode.st_mode):
            raise LocalGrantLedgerError("ledger directory must be real")
        if mode.st_uid != os.geteuid():
            raise LocalGrantLedgerError("ledger directory has wrong owner")
        if stat.S_IMODE(mode.st_mode) & 0o077:
            raise LocalGrantLedgerError("ledger directory permissions too broad")
        self.db_path = requested / "science-grants.db"
        if self.db_path.is_symlink():
            raise LocalGrantLedgerError("ledger database is symlinked")
        if self.db_path.exists():
            status = self.db_path.lstat()
            if not stat.S_ISREG(status.st_mode) or status.st_uid != os.geteuid():
                raise LocalGrantLedgerError("ledger database has invalid type or owner")
            if stat.S_IMODE(status.st_mode) & 0o077:
                raise LocalGrantLedgerError("ledger database permissions too broad")
        else:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(self.db_path, flags, 0o600)
            except OSError as exc:
                raise LocalGrantLedgerError("unable to create private ledger file") from exc
            os.close(fd)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS reservation (
                  authorization_id TEXT PRIMARY KEY,
                  nonce TEXT NOT NULL UNIQUE,
                  claim_id TEXT NOT NULL,
                  run_id TEXT NOT NULL,
                  key_fingerprint_sha256 TEXT NOT NULL,
                  reserved_at TEXT NOT NULL,
                  state TEXT NOT NULL CHECK(state IN ('RESERVED','FINISHED'))
                );
            """)
            conn.execute(
                "INSERT OR IGNORE INTO metadata(name,value) VALUES('schema',?)",
                (LEDGER_SCHEMA,),
            )
            row = conn.execute("SELECT value FROM metadata WHERE name='schema'").fetchone()
            if row is None or row[0] != LEDGER_SCHEMA:
                raise LocalGrantLedgerError("ledger schema mismatch")
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise LocalGrantLedgerError("ledger integrity check failed")
        if stat.S_IMODE(self.db_path.stat().st_mode) & 0o077:
            raise LocalGrantLedgerError("ledger database permissions too broad")

    def _connect(self) -> sqlite3.Connection:
        if self.db_path.is_symlink():
            raise LocalGrantLedgerError("ledger database is symlinked")
        conn = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("PRAGMA journal_mode = DELETE")
        return conn

    def reserve(self, verified: dict[str, Any]) -> dict[str, Any]:
        """Atomically reserve a caller-supplied verified grant result ONCE.

        The caller is responsible for obtaining 'verified' directly from a
        trusted verifier and for coupling this reservation to the execution
        controller. This function does not cryptographically authenticate a
        standalone dict.
        """
        if not isinstance(verified, dict):
            raise LocalGrantLedgerError("verified grant must be object")
        if (verified.get("schema") != "WS-PRIME-SCIENTIFIC-AUTHORIZATION-VERIFICATION-V1"
                or verified.get("status") != "PASS"
                or verified.get("prime_signature_verified") is not True
                or verified.get("authorized_run_executed") is not False):
            raise LocalGrantLedgerError("untrusted or invalid verification envelope")
        authorization_id = _string(verified.get("authorization_id"), "authorization_id")
        nonce = _string(verified.get("nonce"), "nonce", NONCE)
        claim = _string(verified.get("claim_id"), "claim_id")
        run = _string(verified.get("run_id"), "run_id")
        key = _string(verified.get("key_fingerprint_sha256"), "key fingerprint", SHA)
        instant = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO reservation(authorization_id,nonce,claim_id,run_id,key_fingerprint_sha256,reserved_at,state) VALUES(?,?,?,?,?,?,?)",
                    (authorization_id, nonce, claim, run, key, instant, "RESERVED"),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise LocalGrantLedgerError("authorization ID or nonce already reserved") from exc
            except sqlite3.Error as exc:
                conn.rollback()
                raise LocalGrantLedgerError("unable to persist reservation") from exc
        finally:
            conn.close()
        return {
            "schema": "WS-LOCAL-GRANT-RESERVATION-RECEIPT-V1",
            "authorization_id": authorization_id,
            "run_id": run,
            "state": "RESERVED",
            "single_host_reservation_recorded": True,
            "distributed_replay_protected": False,
            "rollback_protected": False,
            "execution_performed": False,
            "scientific_claim_proven": False,
        }

    def mark_finished(self, authorization_id: str) -> None:
        """Mark a reservation complete; never erase it or make it reusable."""
        authorization_id = _string(authorization_id, "authorization_id")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            result = conn.execute(
                "UPDATE reservation SET state='FINISHED' WHERE authorization_id=? AND state='RESERVED'",
                (authorization_id,),
            )
            if result.rowcount != 1:
                conn.rollback()
                raise LocalGrantLedgerError("reservation missing or already finished")
            conn.commit()
        finally:
            conn.close()

    def state(self, authorization_id: str) -> str | None:
        authorization_id = _string(authorization_id, "authorization_id")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT state FROM reservation WHERE authorization_id=?", (authorization_id,)
            ).fetchone()
            return None if row is None else row[0]
        finally:
            conn.close()
