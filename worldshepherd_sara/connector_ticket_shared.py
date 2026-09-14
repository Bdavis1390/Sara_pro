from __future__ import annotations

import hmac
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol

from .connector_ticket_lifecycle import (
    DEFAULT_TTL_SECONDS,
    ReadTicketLedger,
    TicketClaim,
    verify_v2_ticket_shape,
)


@dataclass(frozen=True)
class SharedClaimRecord:
    ticket_sha256: str
    expires_at: float
    consumed_at: Optional[float] = None


class SharedClaimStore(Protocol):
    """Minimal credential-blind compare-and-set contract for ticket claims.

    Implementations may be local, database-backed, or remote. The contract stores
    only the ticket identifier, ticket digest, expiry, and consumption timestamp.
    Connector context, connector results, policy-envelope contents, and credentials
    are deliberately outside this interface.
    """

    def register(self, *, ticket_id: str, ticket_sha256: str, expires_at: float) -> None: ...

    def claim(
        self,
        *,
        ticket_id: str,
        ticket_sha256: str,
        now: float,
    ) -> TicketClaim: ...

    def status(self, ticket_id: str) -> Dict[str, Any]: ...


class SharedReadTicketLedger(ReadTicketLedger):
    """ReadTicketLedger facade backed by a shared compare-and-set claim store."""

    def __init__(self, store: SharedClaimStore, *, clock=time.time) -> None:
        super().__init__(clock=clock)
        self.store = store

    def issue_metadata(self, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> Dict[str, Any]:
        return super().issue_metadata(ttl_seconds=ttl_seconds)

    def register(self, ticket: Mapping[str, Any]) -> None:
        if not verify_v2_ticket_shape(ticket):
            raise ValueError("invalid v2 read ticket")
        self.store.register(
            ticket_id=str(ticket["ticket_id"]),
            ticket_sha256=str(ticket["sha256"]),
            expires_at=float(ticket["expires_at"]),
        )

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
        return self.store.claim(
            ticket_id=ticket_id,
            ticket_sha256=str(ticket["sha256"]),
            now=claim_time,
        )

    def status(self, ticket_id: str) -> Dict[str, Any]:
        status = dict(self.store.status(str(ticket_id)))
        status.pop("ticket_sha256", None)
        return status


class ThreadSafeSharedClaimStore:
    """Reference compare-and-set store used to verify shared-ledger semantics.

    This class is intentionally process-local and exists as a deterministic test
    implementation of the SharedClaimStore contract. It is NOT a distributed
    backend and must not be used to claim multi-host anti-replay.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: Dict[str, SharedClaimRecord] = {}

    def register(self, *, ticket_id: str, ticket_sha256: str, expires_at: float) -> None:
        with self._lock:
            if ticket_id in self._records:
                raise ValueError("duplicate ticket_id")
            self._records[ticket_id] = SharedClaimRecord(
                ticket_sha256=ticket_sha256,
                expires_at=float(expires_at),
            )

    def claim(
        self,
        *,
        ticket_id: str,
        ticket_sha256: str,
        now: float,
    ) -> TicketClaim:
        with self._lock:
            record = self._records.get(ticket_id)
            if record is None:
                return TicketClaim(False, ticket_id, "ticket not registered in this ledger")
            if not hmac.compare_digest(record.ticket_sha256, ticket_sha256):
                return TicketClaim(False, ticket_id, "ticket digest does not match registered ticket")
            if float(now) > float(record.expires_at):
                return TicketClaim(False, ticket_id, "ticket expired")
            if record.consumed_at is not None:
                return TicketClaim(False, ticket_id, "ticket already consumed")

            consumed_at = float(now)
            self._records[ticket_id] = SharedClaimRecord(
                ticket_sha256=record.ticket_sha256,
                expires_at=record.expires_at,
                consumed_at=consumed_at,
            )
            return TicketClaim(
                True,
                ticket_id,
                "ticket claimed for one-time host execution",
                consumed_at,
            )

    def status(self, ticket_id: str) -> Dict[str, Any]:
        with self._lock:
            record = self._records.get(ticket_id)
            if record is None:
                return {"known": False, "ticket_id": ticket_id}
            return {
                "known": True,
                "ticket_id": ticket_id,
                "expires_at": float(record.expires_at),
                "consumed": record.consumed_at is not None,
                "consumed_at": record.consumed_at,
            }
