from __future__ import annotations

from typing import Any, Callable, Dict

from .connector_claim_recovery import (
    ClaimReconciliation,
    UnknownClaimOutcome,
    reconcile_claim_status,
)
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


def _best_effort_rollback(connection: Any) -> None:
    try:
        connection.rollback()
    except Exception:
        pass


def _best_effort_close(connection: Any) -> None:
    try:
        connection.close()
    except Exception:
        pass


class PostgresClaimStore:
    """Credential-blind Postgres compare-and-set adapter for shared ticket claims.

    PostgreSQL is authoritative for registration expiry and consumption time. The
    signed ticket contributes only its bounded lifetime. Transaction/connection
    errors fail closed.

    If the UPDATE returned a successful claim but COMMIT acknowledgement fails,
    the outcome is explicitly UNKNOWN. UNKNOWN never authorizes connector
    execution and is never automatically retried. A fresh connection may reconcile
    durable ticket state through `reconcile_unknown_claim`.
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
            _best_effort_rollback(connection)
            raise
        finally:
            _best_effort_close(connection)

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
                _best_effort_rollback(connection)
                raise ValueError("duplicate ticket_id")
            connection.commit()
        except ValueError:
            raise
        except Exception:
            _best_effort_rollback(connection)
            raise
        finally:
            _best_effort_close(connection)

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
                consumed_at = float(row[1])
                try:
                    connection.commit()
                except Exception as exc:
                    # COMMIT may have reached PostgreSQL even when its acknowledgement
                    # did not reach the client. Do not roll back/retry or authorize
                    # execution from this uncertain state.
                    raise UnknownClaimOutcome(ticket_id) from exc
                return TicketClaim(
                    True,
                    ticket_id,
                    "ticket claimed for one-time host execution",
                    consumed_at,
                )

            _best_effort_rollback(connection)
        except UnknownClaimOutcome:
            raise
        except Exception:
            _best_effort_rollback(connection)
            raise
        finally:
            _best_effort_close(connection)

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

    def reconcile_unknown_claim(
        self,
        *,
        ticket_id: str,
        ticket_sha256: str,
    ) -> ClaimReconciliation:
        """Reconcile an UNKNOWN claim through a fresh store connection.

        A consumed record remains non-executable because the current schema does
        not prove which claimant owns it. An unconsumed, unexpired record is only
        marked retryable; the caller must still make an explicit new claim.
        """
        try:
            status = self.status(ticket_id)
        except Exception as exc:
            return ClaimReconciliation(
                state="unknown",
                ticket_id=str(ticket_id),
                reason=f"reconciliation status read failed: {type(exc).__name__}",
            )
        return reconcile_claim_status(
            ticket_id=str(ticket_id),
            ticket_sha256=str(ticket_sha256),
            status=status,
        )

    def status(self, ticket_id: str) -> Dict[str, Any]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(STATUS_SQL, (ticket_id,))
            row = cursor.fetchone()
        finally:
            _best_effort_close(connection)

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
