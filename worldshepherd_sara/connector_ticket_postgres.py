from __future__ import annotations

from typing import Any, Callable, Dict

from .connector_ticket_lifecycle import (
    MAX_TTL_SECONDS,
    MIN_TTL_SECONDS,
    TicketClaim,
)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS worldshepherd_connector_read_tickets (
    ticket_id TEXT PRIMARY KEY,
    ticket_sha256 TEXT NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL,
    consumed_at DOUBLE PRECISION NULL
)
""".strip()

REGISTER_SQL = """
INSERT INTO worldshepherd_connector_read_tickets
    (ticket_id, ticket_sha256, expires_at, consumed_at)
VALUES (
    %s,
    %s,
    EXTRACT(EPOCH FROM clock_timestamp()) + %s,
    NULL
)
ON CONFLICT (ticket_id) DO NOTHING
""".strip()

CLAIM_SQL = """
UPDATE worldshepherd_connector_read_tickets
SET consumed_at = EXTRACT(EPOCH FROM clock_timestamp())
WHERE ticket_id = %s
  AND ticket_sha256 = %s
  AND consumed_at IS NULL
  AND expires_at >= EXTRACT(EPOCH FROM clock_timestamp())
RETURNING expires_at, consumed_at
""".strip()

STATUS_SQL = """
SELECT
    ticket_sha256,
    expires_at,
    consumed_at,
    expires_at < EXTRACT(EPOCH FROM clock_timestamp()) AS expired
FROM worldshepherd_connector_read_tickets
WHERE ticket_id = %s
""".strip()


class PostgresClaimStore:
    """Credential-blind Postgres compare-and-set adapter for shared ticket claims.

    The caller supplies a DB-API compatible connection factory. This module never
    accepts or stores connection strings, passwords, API keys, service-role keys,
    or other credential material.

    PostgreSQL is authoritative for registration expiry and consumption time. The
    signed ticket contributes only its bounded lifetime (expires_at - issued_at),
    which removes issuer/claimant absolute clock offsets from the database claim
    decision. The atomic UPDATE ... WHERE consumed_at IS NULL statement remains the
    anti-replay compare-and-set primitive.
    """

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    def initialize(self) -> None:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(CREATE_TABLE_SQL)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def register(
        self,
        *,
        ticket_id: str,
        ticket_sha256: str,
        issued_at: float,
        expires_at: float,
    ) -> None:
        ttl_seconds = float(expires_at) - float(issued_at)
        if ttl_seconds < MIN_TTL_SECONDS or ttl_seconds > MAX_TTL_SECONDS:
            raise ValueError(
                f"ticket lifetime must be between {MIN_TTL_SECONDS} and {MAX_TTL_SECONDS} seconds"
            )

        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(
                REGISTER_SQL,
                (ticket_id, ticket_sha256, ttl_seconds),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise ValueError("duplicate ticket_id")
            connection.commit()
        except ValueError:
            raise
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def claim(
        self,
        *,
        ticket_id: str,
        ticket_sha256: str,
        now: float,
    ) -> TicketClaim:
        # `now` remains in the shared-store interface for local/reference stores.
        # PostgreSQL-backed claims intentionally ignore client absolute time.
        _ = now
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(
                CLAIM_SQL,
                (ticket_id, ticket_sha256),
            )
            row = cursor.fetchone()
            if row is not None:
                connection.commit()
                return TicketClaim(
                    True,
                    ticket_id,
                    "ticket claimed for one-time host execution",
                    float(row[1]),
                )

            connection.rollback()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        status = self.status(ticket_id)
        if not status.get("known"):
            return TicketClaim(False, ticket_id, "ticket not registered in this ledger")
        if status.get("ticket_sha256") != ticket_sha256:
            return TicketClaim(False, ticket_id, "ticket digest does not match registered ticket")
        if bool(status.get("expired")):
            return TicketClaim(False, ticket_id, "ticket expired")
        if bool(status.get("consumed")):
            return TicketClaim(False, ticket_id, "ticket already consumed")
        return TicketClaim(False, ticket_id, "ticket claim lost compare-and-set race")

    def status(self, ticket_id: str) -> Dict[str, Any]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(STATUS_SQL, (ticket_id,))
            row = cursor.fetchone()
        finally:
            connection.close()

        if row is None:
            return {"known": False, "ticket_id": ticket_id}

        ticket_sha256, expires_at, consumed_at, expired = row
        return {
            "known": True,
            "ticket_id": ticket_id,
            "ticket_sha256": str(ticket_sha256),
            "expires_at": float(expires_at),
            "expired": bool(expired),
            "consumed": consumed_at is not None,
            "consumed_at": None if consumed_at is None else float(consumed_at),
        }
