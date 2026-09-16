from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")
MAX_REPLAY_RECORDS = 16384
REPLAY_RETENTION = timedelta(hours=24)


class PQReplayError(RuntimeError):
    pass


class PQReplayDetected(PQReplayError):
    pass


class PQReplayStoreFull(PQReplayError):
    pass


class PQReplayGuard:
    """Durable one-time request-ID ledger for short-lived PQ HPKE envelopes."""

    def __init__(self, database_path: str | Path, *, namespace: str) -> None:
        self.database_path = Path(database_path)
        if not self.database_path.is_absolute():
            raise PQReplayError("PQ replay database path must be absolute")
        if not namespace or len(namespace) > 128:
            raise PQReplayError("PQ replay namespace is invalid")
        self.namespace = namespace
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self.database_path,
                timeout=5.0,
                isolation_level=None,
            )
        except sqlite3.Error as exc:
            raise PQReplayError("unable to open PQ replay ledger") from exc
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS pq_transport_replay (
                    namespace TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    service TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    PRIMARY KEY(namespace, request_id)
                );
                CREATE INDEX IF NOT EXISTS idx_pq_transport_replay_received
                    ON pq_transport_replay(namespace, received_at);
                """
            )
            connection.commit()
        except sqlite3.Error as exc:
            if connection.in_transaction:
                connection.rollback()
            raise PQReplayError("unable to initialize PQ replay ledger") from exc
        finally:
            connection.close()

    def consume(
        self,
        *,
        request_id: str,
        service: str,
        operation: str,
        now: datetime | None = None,
    ) -> None:
        if not _REQUEST_ID.fullmatch(request_id):
            raise PQReplayError("PQ request_id is invalid")
        if not service or len(service) > 128 or not operation or len(operation) > 128:
            raise PQReplayError("PQ replay service/operation is invalid")
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        cutoff = current - REPLAY_RETENTION
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM pq_transport_replay WHERE namespace=? AND received_at<?",
                (self.namespace, cutoff.isoformat()),
            )
            existing = connection.execute(
                "SELECT service,operation FROM pq_transport_replay "
                "WHERE namespace=? AND request_id=?",
                (self.namespace, request_id),
            ).fetchone()
            if existing is not None:
                connection.rollback()
                raise PQReplayDetected("PQ transport request_id has already been consumed")
            count = connection.execute(
                "SELECT COUNT(*) FROM pq_transport_replay WHERE namespace=?",
                (self.namespace,),
            ).fetchone()[0]
            if count >= MAX_REPLAY_RECORDS:
                connection.rollback()
                raise PQReplayStoreFull("PQ replay ledger capacity reached")
            connection.execute(
                "INSERT INTO pq_transport_replay(namespace,request_id,service,operation,received_at) "
                "VALUES(?,?,?,?,?)",
                (
                    self.namespace,
                    request_id,
                    service,
                    operation,
                    current.isoformat(),
                ),
            )
            connection.commit()
        except (PQReplayDetected, PQReplayStoreFull):
            raise
        except sqlite3.Error as exc:
            if connection.in_transaction:
                connection.rollback()
            raise PQReplayError("unable to update PQ replay ledger") from exc
        finally:
            connection.close()

    def status(self) -> dict[str, object]:
        connection = self._connect()
        try:
            quick = connection.execute("PRAGMA quick_check").fetchone()
            count = connection.execute(
                "SELECT COUNT(*) FROM pq_transport_replay WHERE namespace=?",
                (self.namespace,),
            ).fetchone()[0]
        except sqlite3.Error as exc:
            raise PQReplayError("unable to inspect PQ replay ledger") from exc
        finally:
            connection.close()
        return {
            "ok": quick is not None and quick[0] == "ok" and count <= MAX_REPLAY_RECORDS,
            "namespace": self.namespace,
            "recent_consumed_request_ids": count,
            "capacity": MAX_REPLAY_RECORDS,
            "retention_seconds": int(REPLAY_RETENTION.total_seconds()),
        }
