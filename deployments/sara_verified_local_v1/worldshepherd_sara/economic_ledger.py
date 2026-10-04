from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from .economic_authorization import (
    EconomicAuthorizationDecision,
    EconomicAuthorizationPolicy,
    EconomicPaymentIntent,
    economic_intent_sha256,
    economic_policy_sha256,
    evaluate_economic_intent,
)


ECONOMIC_LEDGER_SCHEMA = "WS-ECONOMIC-AUTHORIZATION-LEDGER-G1-V1"
ECONOMIC_EVENT_SCHEMA = "WS-ECONOMIC-AUTHORIZATION-EVENT-G1-V1"
MAX_ECONOMIC_INTENTS = 4096
ZERO_HASH = "0" * 64

AuthorizationStatus = Literal["NOT_BOUND", "PRIME_VERIFIED", "REJECTED"]


class EconomicLedgerError(RuntimeError):
    pass


class EconomicLedgerConflict(EconomicLedgerError):
    pass


class EconomicReplayDetected(EconomicLedgerError):
    pass


class EconomicLedgerFull(EconomicLedgerError):
    pass


class EconomicInvalidTransition(EconomicLedgerError):
    pass


@dataclass(frozen=True)
class EconomicLedgerRecord:
    intent_id: str
    nonce: str
    intent_sha256: str
    policy_id: str
    policy_sha256: str
    session_id: str
    protocol: str
    network: str
    asset: str
    payee: str
    amount: str
    mode: str
    decision_status: str
    decision_json: str | None
    authorization_status: str
    authorization_ref: str | None
    authorization_digest_sha256: str | None
    authorization_nonce: str | None
    consumption_status: str
    failure_code: str | None
    adapter_receipt_ref: str | None
    recorded_at: str
    decision_at: str | None
    authorization_at: str | None
    consumed_at: str | None
    failed_at: str | None

    def decision(self) -> EconomicAuthorizationDecision | None:
        if self.decision_json is None:
            return None
        return EconomicAuthorizationDecision.model_validate(json.loads(self.decision_json))


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _row_to_record(row: sqlite3.Row) -> EconomicLedgerRecord:
    return EconomicLedgerRecord(
        **{key: row[key] for key in EconomicLedgerRecord.__dataclass_fields__}
    )


class EconomicAuthorizationLedger:
    """Durable replay and budget-reservation ledger for dry-run economic intents.

    The G1 ledger performs no payment, wallet access, signing, facilitator call,
    or settlement. BEGIN IMMEDIATE serializes decision writes so cumulative
    policy budgets cannot be oversubscribed by concurrent decision attempts.
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            raise EconomicLedgerError("economic ledger data directory must be absolute")
        self._prepare_data_dir()
        self.db_path = self.data_dir / "economic_authorization.db"
        self._reject_database_symlink()
        self._initialize()

    @classmethod
    def from_environment(cls) -> "EconomicAuthorizationLedger":
        value = os.getenv("WS_ECONOMIC_LEDGER_DATA_DIR", "").strip()
        if not value:
            raise EconomicLedgerError("WS_ECONOMIC_LEDGER_DATA_DIR is required")
        return cls(value)

    def _prepare_data_dir(self) -> None:
        if self.data_dir.exists():
            status = self.data_dir.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                raise EconomicLedgerError("economic ledger data directory must be a real directory")
        else:
            self.data_dir.mkdir(parents=True, mode=0o700)
            status = self.data_dir.lstat()
        if status.st_uid != os.geteuid():
            raise EconomicLedgerError("economic ledger data directory must be owned by the service UID")
        if stat.S_IMODE(status.st_mode) & 0o022:
            raise EconomicLedgerError(
                "economic ledger data directory must not be group/other writable"
            )

    def _reject_database_symlink(self) -> None:
        if self.db_path.exists() or self.db_path.is_symlink():
            status = self.db_path.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise EconomicLedgerError("economic ledger database must be a regular file")
            if status.st_uid != os.geteuid():
                raise EconomicLedgerError("economic ledger database must be owned by the service UID")

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        except sqlite3.Error as exc:
            raise EconomicLedgerError("unable to open economic ledger database") from exc
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
                CREATE TABLE IF NOT EXISTS economic_intents (
                    intent_id TEXT PRIMARY KEY,
                    nonce TEXT NOT NULL UNIQUE,
                    intent_sha256 TEXT NOT NULL UNIQUE,
                    policy_id TEXT NOT NULL,
                    policy_sha256 TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    protocol TEXT NOT NULL,
                    network TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    payee TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    mode TEXT NOT NULL CHECK (mode IN ('DRY_RUN', 'LIVE')),
                    decision_status TEXT NOT NULL
                        CHECK (decision_status IN ('PENDING', 'ALLOWED', 'DENIED')),
                    decision_json TEXT,
                    authorization_status TEXT NOT NULL
                        CHECK (authorization_status IN ('NOT_BOUND', 'PRIME_VERIFIED', 'REJECTED')),
                    authorization_ref TEXT UNIQUE,
                    authorization_digest_sha256 TEXT UNIQUE,
                    authorization_nonce TEXT UNIQUE,
                    consumption_status TEXT NOT NULL
                        CHECK (consumption_status IN ('UNCONSUMED', 'DRY_RUN_CONSUMED')),
                    failure_code TEXT,
                    adapter_receipt_ref TEXT,
                    recorded_at TEXT NOT NULL,
                    decision_at TEXT,
                    authorization_at TEXT,
                    consumed_at TEXT,
                    failed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS economic_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    schema TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    intent_id TEXT NOT NULL,
                    event_type TEXT NOT NULL
                        CHECK (event_type IN (
                            'INTENT_RECORDED',
                            'DECISION_RECORDED',
                            'AUTHORIZATION_RECORDED',
                            'DRY_RUN_CONSUMED',
                            'FAILED'
                        )),
                    event_time TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    FOREIGN KEY(intent_id) REFERENCES economic_intents(intent_id)
                );
                CREATE INDEX IF NOT EXISTS idx_economic_session_policy
                    ON economic_intents(session_id, policy_id);
                CREATE INDEX IF NOT EXISTS idx_economic_decision
                    ON economic_intents(decision_status);
                CREATE INDEX IF NOT EXISTS idx_economic_consumption
                    ON economic_intents(consumption_status);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(name, value) VALUES('schema', ?)",
                (ECONOMIC_LEDGER_SCHEMA,),
            )
            schema_row = connection.execute(
                "SELECT value FROM metadata WHERE name='schema'"
            ).fetchone()
            if schema_row is None or schema_row["value"] != ECONOMIC_LEDGER_SCHEMA:
                raise EconomicLedgerError("economic ledger schema mismatch")
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise EconomicLedgerError("economic ledger integrity check failed")
        except sqlite3.Error as exc:
            raise EconomicLedgerError("unable to initialize economic ledger database") from exc
        finally:
            connection.close()
        try:
            self.db_path.chmod(0o600)
        except OSError as exc:
            raise EconomicLedgerError("unable to restrict economic ledger permissions") from exc

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        intent_id: str,
        event_type: str,
        event_time: str,
        payload: dict[str, Any],
    ) -> None:
        previous = connection.execute(
            "SELECT event_hash FROM economic_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous is not None else ZERO_HASH
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload_sha256 = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        event_id = f"WSECON-{uuid4()}"
        canonical = {
            "schema": ECONOMIC_EVENT_SCHEMA,
            "event_id": event_id,
            "intent_id": intent_id,
            "event_type": event_type,
            "event_time": event_time,
            "payload_sha256": payload_sha256,
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        connection.execute(
            """
            INSERT INTO economic_events(
                schema, event_id, intent_id, event_type, event_time,
                payload_json, payload_sha256, previous_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ECONOMIC_EVENT_SCHEMA,
                event_id,
                intent_id,
                event_type,
                event_time,
                payload_json,
                payload_sha256,
                previous_hash,
                event_hash,
            ),
        )

    def record_intent(
        self,
        intent: EconomicPaymentIntent,
        policy: EconomicAuthorizationPolicy,
        *,
        now: datetime | None = None,
    ) -> EconomicLedgerRecord:
        intent_digest = economic_intent_sha256(intent)
        policy_digest = economic_policy_sha256(policy)
        if intent.session_id != policy.session_id:
            raise EconomicLedgerConflict("intent and policy session IDs do not match")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent.intent_id,)
            ).fetchone()
            if existing is not None:
                record = _row_to_record(existing)
                if record.consumption_status != "UNCONSUMED":
                    raise EconomicReplayDetected("consumed economic intent cannot be replayed")
                if (
                    record.intent_sha256 != intent_digest
                    or record.policy_sha256 != policy_digest
                    or record.nonce != intent.nonce
                ):
                    raise EconomicLedgerConflict(
                        "intent ID is already bound to different intent or policy content"
                    )
                connection.commit()
                return record

            replay = connection.execute(
                "SELECT intent_id FROM economic_intents WHERE nonce=? OR intent_sha256=?",
                (intent.nonce, intent_digest),
            ).fetchone()
            if replay is not None:
                raise EconomicReplayDetected(
                    "economic intent nonce or digest has already been recorded"
                )

            count = connection.execute("SELECT COUNT(*) FROM economic_intents").fetchone()[0]
            if count >= MAX_ECONOMIC_INTENTS:
                raise EconomicLedgerFull("economic ledger capacity reached")

            recorded_at = _utc_iso(now or datetime.now(timezone.utc))
            connection.execute(
                """
                INSERT INTO economic_intents(
                    intent_id, nonce, intent_sha256, policy_id, policy_sha256,
                    session_id, protocol, network, asset, payee, amount, mode,
                    decision_status, authorization_status, consumption_status,
                    recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING',
                          'NOT_BOUND', 'UNCONSUMED', ?)
                """,
                (
                    intent.intent_id,
                    intent.nonce,
                    intent_digest,
                    policy.policy_id,
                    policy_digest,
                    intent.session_id,
                    intent.protocol,
                    intent.network,
                    intent.asset,
                    intent.payee,
                    str(intent.amount),
                    intent.mode,
                    recorded_at,
                ),
            )
            self._append_event(
                connection,
                intent_id=intent.intent_id,
                event_type="INTENT_RECORDED",
                event_time=recorded_at,
                payload={
                    "intent_sha256": intent_digest,
                    "policy_id": policy.policy_id,
                    "policy_sha256": policy_digest,
                    "session_id": intent.session_id,
                    "protocol": intent.protocol,
                    "network": intent.network,
                    "asset": intent.asset,
                    "payee": intent.payee,
                    "amount": str(intent.amount),
                    "mode": intent.mode,
                    "nonce": intent.nonce,
                },
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent.intent_id,)
            ).fetchone()
            assert row is not None
            return _row_to_record(row)
        except (EconomicLedgerError, sqlite3.Error):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def evaluate_recorded_intent(
        self,
        intent: EconomicPaymentIntent,
        policy: EconomicAuthorizationPolicy,
        *,
        now: datetime | None = None,
    ) -> EconomicAuthorizationDecision:
        intent_digest = economic_intent_sha256(intent)
        policy_digest = economic_policy_sha256(policy)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent.intent_id,)
            ).fetchone()
            if row is None:
                raise EconomicLedgerError("economic intent is not recorded")
            record = _row_to_record(row)
            if record.consumption_status != "UNCONSUMED":
                raise EconomicReplayDetected("consumed economic intent cannot be re-evaluated")
            if record.intent_sha256 != intent_digest:
                raise EconomicLedgerConflict("recorded economic intent digest mismatch")
            if record.policy_id != policy.policy_id or record.policy_sha256 != policy_digest:
                raise EconomicLedgerConflict("recorded economic policy binding mismatch")
            if intent.session_id != policy.session_id or record.session_id != policy.session_id:
                raise EconomicLedgerConflict("economic session binding mismatch")

            if record.decision_json is not None:
                decision = record.decision()
                assert decision is not None
                connection.commit()
                return decision

            reserved_rows = connection.execute(
                """
                SELECT amount FROM economic_intents
                WHERE session_id=? AND policy_id=? AND policy_sha256=?
                  AND decision_status='ALLOWED' AND intent_id<>?
                """,
                (
                    policy.session_id,
                    policy.policy_id,
                    policy_digest,
                    intent.intent_id,
                ),
            ).fetchall()
            spent_before = sum(
                (Decimal(str(item["amount"])) for item in reserved_rows),
                Decimal("0"),
            )

            decision = evaluate_economic_intent(
                intent,
                policy,
                spent_so_far=spent_before,
                now=now,
            )
            decision_status = (
                "ALLOWED" if decision.disposition == "ALLOW_DRY_RUN" else "DENIED"
            )
            decision_json = json.dumps(
                decision.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            decision_at = _utc_iso(decision.evaluated_at)
            connection.execute(
                """
                UPDATE economic_intents
                SET decision_status=?, decision_json=?, decision_at=?
                WHERE intent_id=? AND decision_status='PENDING'
                """,
                (decision_status, decision_json, decision_at, intent.intent_id),
            )
            self._append_event(
                connection,
                intent_id=intent.intent_id,
                event_type="DECISION_RECORDED",
                event_time=decision_at,
                payload={
                    "disposition": decision.disposition,
                    "reasons": list(decision.reasons),
                    "spent_before": str(decision.spent_before),
                    "remaining_budget_after": str(decision.remaining_budget_after),
                    "intent_sha256": decision.intent_sha256,
                },
            )
            connection.commit()
            return decision
        except (EconomicLedgerError, sqlite3.Error):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def record_authorization_result(
        self,
        *,
        intent_id: str,
        status: AuthorizationStatus,
        authorization_ref: str | None,
        authorization_digest_sha256: str | None = None,
        authorization_nonce: str | None = None,
        now: datetime | None = None,
    ) -> EconomicLedgerRecord:
        if status not in {"NOT_BOUND", "PRIME_VERIFIED", "REJECTED"}:
            raise EconomicInvalidTransition("unknown economic authorization status")
        if status == "NOT_BOUND":
            raise EconomicInvalidTransition("NOT_BOUND is the initial state, not an authorization result")
        if status == "PRIME_VERIFIED":
            if not authorization_ref:
                raise EconomicInvalidTransition(
                    "PRIME_VERIFIED requires an authorization reference"
                )
            if not authorization_nonce:
                raise EconomicInvalidTransition(
                    "PRIME_VERIFIED requires an authorization nonce"
                )
            if (
                authorization_digest_sha256 is None
                or len(authorization_digest_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in authorization_digest_sha256)
            ):
                raise EconomicInvalidTransition(
                    "PRIME_VERIFIED requires a lowercase SHA-256 authorization digest"
                )

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent_id,)
            ).fetchone()
            if row is None:
                raise EconomicLedgerError("economic intent is not recorded")
            record = _row_to_record(row)
            if record.consumption_status != "UNCONSUMED":
                raise EconomicInvalidTransition("authorization cannot change after consumption")
            if record.authorization_status != "NOT_BOUND":
                if (
                    record.authorization_status == status
                    and record.authorization_ref == authorization_ref
                    and record.authorization_digest_sha256 == authorization_digest_sha256
                    and record.authorization_nonce == authorization_nonce
                ):
                    connection.commit()
                    return record
                raise EconomicInvalidTransition("authorization result is already recorded")

            if status == "PRIME_VERIFIED":
                replay = connection.execute(
                    """
                    SELECT intent_id FROM economic_intents
                    WHERE intent_id<>?
                      AND (
                        authorization_ref=?
                        OR authorization_digest_sha256=?
                        OR authorization_nonce=?
                      )
                    LIMIT 1
                    """,
                    (
                        intent_id,
                        authorization_ref,
                        authorization_digest_sha256,
                        authorization_nonce,
                    ),
                ).fetchone()
                if replay is not None:
                    raise EconomicReplayDetected(
                        "PRIME economic authorization has already been bound to another intent"
                    )

            authorization_at = _utc_iso(now or datetime.now(timezone.utc))
            connection.execute(
                """
                UPDATE economic_intents
                SET authorization_status=?, authorization_ref=?,
                    authorization_digest_sha256=?, authorization_nonce=?,
                    authorization_at=?
                WHERE intent_id=? AND authorization_status='NOT_BOUND'
                """,
                (
                    status,
                    authorization_ref,
                    authorization_digest_sha256,
                    authorization_nonce,
                    authorization_at,
                    intent_id,
                ),
            )
            self._append_event(
                connection,
                intent_id=intent_id,
                event_type="AUTHORIZATION_RECORDED",
                event_time=authorization_at,
                payload={
                    "status": status,
                    "authorization_ref": authorization_ref,
                    "authorization_digest_sha256": authorization_digest_sha256,
                    "authorization_nonce": authorization_nonce,
                },
            )
            connection.commit()
            updated = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent_id,)
            ).fetchone()
            assert updated is not None
            return _row_to_record(updated)
        except (EconomicLedgerError, sqlite3.Error):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def consume_dry_run(
        self,
        *,
        intent_id: str,
        adapter_receipt_ref: str | None = None,
        now: datetime | None = None,
    ) -> EconomicLedgerRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent_id,)
            ).fetchone()
            if row is None:
                raise EconomicLedgerError("economic intent is not recorded")
            record = _row_to_record(row)
            if record.consumption_status != "UNCONSUMED":
                raise EconomicReplayDetected("economic intent has already been consumed")
            if record.mode != "DRY_RUN":
                raise EconomicInvalidTransition("LIVE economic intent cannot be consumed by G1")
            if record.decision_status != "ALLOWED":
                raise EconomicInvalidTransition("only an allowed dry-run intent can be consumed")
            if record.authorization_status == "REJECTED":
                raise EconomicInvalidTransition("rejected authorization cannot be consumed")

            consumed_at = _utc_iso(now or datetime.now(timezone.utc))
            connection.execute(
                """
                UPDATE economic_intents
                SET consumption_status='DRY_RUN_CONSUMED',
                    adapter_receipt_ref=?, consumed_at=?
                WHERE intent_id=? AND consumption_status='UNCONSUMED'
                """,
                (adapter_receipt_ref, consumed_at, intent_id),
            )
            self._append_event(
                connection,
                intent_id=intent_id,
                event_type="DRY_RUN_CONSUMED",
                event_time=consumed_at,
                payload={"adapter_receipt_ref": adapter_receipt_ref},
            )
            connection.commit()
            updated = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent_id,)
            ).fetchone()
            assert updated is not None
            return _row_to_record(updated)
        except (EconomicLedgerError, sqlite3.Error):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def mark_failed(
        self,
        *,
        intent_id: str,
        failure_code: str,
        now: datetime | None = None,
    ) -> EconomicLedgerRecord:
        code = failure_code.strip()
        if not code:
            raise EconomicInvalidTransition("failure code cannot be empty")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent_id,)
            ).fetchone()
            if row is None:
                raise EconomicLedgerError("economic intent is not recorded")
            record = _row_to_record(row)
            if record.consumption_status != "UNCONSUMED":
                raise EconomicInvalidTransition("consumed economic intent cannot be marked failed")
            if record.failure_code is not None:
                if record.failure_code == code:
                    connection.commit()
                    return record
                raise EconomicInvalidTransition("economic intent already has a different failure code")

            failed_at = _utc_iso(now or datetime.now(timezone.utc))
            connection.execute(
                "UPDATE economic_intents SET failure_code=?, failed_at=? WHERE intent_id=?",
                (code, failed_at, intent_id),
            )
            self._append_event(
                connection,
                intent_id=intent_id,
                event_type="FAILED",
                event_time=failed_at,
                payload={"failure_code": code},
            )
            connection.commit()
            updated = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent_id,)
            ).fetchone()
            assert updated is not None
            return _row_to_record(updated)
        except (EconomicLedgerError, sqlite3.Error):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, intent_id: str) -> EconomicLedgerRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM economic_intents WHERE intent_id=?", (intent_id,)
            ).fetchone()
            return _row_to_record(row) if row is not None else None
        finally:
            connection.close()

    def session_reserved_total(
        self,
        *,
        session_id: str,
        policy_id: str,
        policy_sha256: str,
    ) -> Decimal:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT amount FROM economic_intents
                WHERE session_id=? AND policy_id=? AND policy_sha256=?
                  AND decision_status='ALLOWED'
                """,
                (session_id, policy_id, policy_sha256),
            ).fetchall()
            return sum((Decimal(str(row["amount"])) for row in rows), Decimal("0"))
        finally:
            connection.close()

    def verify_event_chain(self) -> tuple[bool, int]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM economic_events ORDER BY sequence"
            ).fetchall()
        finally:
            connection.close()

        previous_hash = ZERO_HASH
        for row in rows:
            if row["schema"] != ECONOMIC_EVENT_SCHEMA or row["previous_hash"] != previous_hash:
                return False, len(rows)
            payload_sha256 = hashlib.sha256(
                row["payload_json"].encode("utf-8")
            ).hexdigest()
            if payload_sha256 != row["payload_sha256"]:
                return False, len(rows)
            canonical = {
                "schema": row["schema"],
                "event_id": row["event_id"],
                "intent_id": row["intent_id"],
                "event_type": row["event_type"],
                "event_time": row["event_time"],
                "payload_sha256": row["payload_sha256"],
                "previous_hash": row["previous_hash"],
            }
            expected = hashlib.sha256(
                json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if row["event_hash"] != expected:
                return False, len(rows)
            previous_hash = row["event_hash"]
        return True, len(rows)

    def health(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            quick = connection.execute("PRAGMA quick_check").fetchone()
            total = connection.execute("SELECT COUNT(*) FROM economic_intents").fetchone()[0]
            allowed = connection.execute(
                "SELECT COUNT(*) FROM economic_intents WHERE decision_status='ALLOWED'"
            ).fetchone()[0]
            denied = connection.execute(
                "SELECT COUNT(*) FROM economic_intents WHERE decision_status='DENIED'"
            ).fetchone()[0]
            consumed = connection.execute(
                "SELECT COUNT(*) FROM economic_intents WHERE consumption_status='DRY_RUN_CONSUMED'"
            ).fetchone()[0]
        except sqlite3.Error as exc:
            raise EconomicLedgerError("economic ledger health check failed") from exc
        finally:
            connection.close()

        chain_ok, event_count = self.verify_event_chain()
        return {
            "ok": bool(quick and quick[0] == "ok" and chain_ok),
            "records": total,
            "allowed": allowed,
            "denied": denied,
            "dry_run_consumed": consumed,
            "events": event_count,
            "capacity": MAX_ECONOMIC_INTENTS,
            "event_chain_ok": chain_ok,
        }
