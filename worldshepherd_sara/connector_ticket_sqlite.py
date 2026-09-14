from __future__ import annotations

import hmac
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

from .connector_ticket_lifecycle import (
    ReadTicketLedger,
    TicketClaim,
    verify_v2_ticket_shape,
)


class SqliteReadTicketLedger(ReadTicketLedger):
    """Restart-safe single-host ledger for connector read-ticket claims.

    The adapter stores only ticket identifiers, ticket digests, expiry timestamps,
    and consumption timestamps. Raw connector context, connector results, and
    credential material are never stored here.

    The SQLite file provides durable single-use enforcement across process restarts
    and across local processes that share the same file. It does not establish
    multi-host or distributed anti-replay semantics and is not a consensus store.
    """

    def __init__(
        self,
        path: Path | str,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        super().__init__(clock=clock)
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.path),
            timeout=5.0,
            isolation_level=None,
        )
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS connector_read_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    ticket_sha256 TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    consumed_at REAL NULL
                )
                """
            )

    def register(self, ticket: Mapping[str, Any]) -> None:
        if not verify_v2_ticket_shape(ticket):
            raise ValueError("invalid v2 read ticket")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO connector_read_tickets
                        (ticket_id, ticket_sha256, expires_at, consumed_at)
                    VALUES (?, ?, ?, NULL)
                    """,
                    (
                        str(ticket["ticket_id"]),
                        str(ticket["sha256"]),
                        float(ticket["expires_at"]),
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("duplicate ticket_id") from exc

    def claim(
        self,
        ticket: Mapping[str, Any],
        *,
        now: Optional[float] = None,
    ) -> TicketClaim:
        ticket_id = str(ticket.get("ticket_id", ""))
        if not verify_v2_ticket_shape(ticket):
            return TicketClaim(False, ticket_id, "invalid read ticket")
        claim_time = float(self._clock() if now is None else now)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT ticket_sha256, expires_at, consumed_at
                FROM connector_read_tickets
                WHERE ticket_id = ?
                """,
                (ticket_id,),
            ).fetchone()

            if row is None:
                connection.rollback()
                return TicketClaim(False, ticket_id, "ticket not registered in this ledger")

            registered_sha, expires_at, consumed_at = row
            if not hmac.compare_digest(str(registered_sha), str(ticket["sha256"])):
                connection.rollback()
                return TicketClaim(False, ticket_id, "ticket digest does not match registered ticket")
            if claim_time > float(expires_at):
                connection.rollback()
                return TicketClaim(False, ticket_id, "ticket expired")
            if consumed_at is not None:
                connection.rollback()
                return TicketClaim(False, ticket_id, "ticket already consumed")

            cursor = connection.execute(
                """
                UPDATE connector_read_tickets
                SET consumed_at = ?
                WHERE ticket_id = ? AND consumed_at IS NULL
                """,
                (claim_time, ticket_id),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return TicketClaim(False, ticket_id, "ticket already consumed")

            connection.commit()
            return TicketClaim(
                True,
                ticket_id,
                "ticket claimed for one-time host execution",
                claim_time,
            )

    def status(self, ticket_id: str) -> Dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT expires_at, consumed_at
                FROM connector_read_tickets
                WHERE ticket_id = ?
                """,
                (str(ticket_id),),
            ).fetchone()

        if row is None:
            return {"known": False, "ticket_id": str(ticket_id)}

        expires_at, consumed_at = row
        return {
            "known": True,
            "ticket_id": str(ticket_id),
            "expires_at": float(expires_at),
            "consumed": consumed_at is not None,
            "consumed_at": consumed_at,
        }
