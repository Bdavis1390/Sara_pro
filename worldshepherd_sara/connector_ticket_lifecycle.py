from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional

READ_TICKET_SCHEMA_V2 = "worldshepherd.connector.read-ticket.v2"
MIN_TTL_SECONDS = 5
MAX_TTL_SECONDS = 300
DEFAULT_TTL_SECONDS = 60


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def context_sha256(context: Optional[Mapping[str, Any]]) -> str:
    return canonical_sha256(dict(context or {}))


def valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def verify_v2_ticket_shape(ticket: Mapping[str, Any]) -> bool:
    if ticket.get("schema") != READ_TICKET_SCHEMA_V2:
        return False
    if ticket.get("write_enabled") is not False:
        return False
    if ticket.get("execution_mode") != "host_connector_handoff":
        return False
    if ticket.get("credential_handling") != "outside_sara_broker":
        return False
    if ticket.get("max_uses") != 1:
        return False
    if "context" in ticket:
        return False
    if not valid_sha256(ticket.get("context_sha256")):
        return False
    if not valid_sha256(ticket.get("policy_envelope_sha256")):
        return False

    ticket_id = ticket.get("ticket_id")
    if not isinstance(ticket_id, str) or len(ticket_id) < 32:
        return False

    try:
        issued_at = float(ticket.get("issued_at"))
        expires_at = float(ticket.get("expires_at"))
    except (TypeError, ValueError):
        return False
    ttl = expires_at - issued_at
    if ttl < MIN_TTL_SECONDS or ttl > MAX_TTL_SECONDS:
        return False

    supplied = ticket.get("sha256")
    if not valid_sha256(supplied):
        return False
    unsigned = dict(ticket)
    unsigned.pop("sha256", None)
    expected = canonical_sha256(unsigned)
    return hmac.compare_digest(str(supplied), expected)


@dataclass(frozen=True)
class TicketClaim:
    ok: bool
    ticket_id: str
    reason: str
    consumed_at: Optional[float] = None


class ReadTicketLedger:
    """Process-local single-use ledger for bounded connector read tickets.

    The ledger provides atomic one-time claims within one running process. It is
    intentionally credential-blind and stores only ticket identifiers, ticket
    hashes, expiry, and consumption state. Durable/distributed anti-replay is a
    separate promotion gate and is not claimed by this implementation.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._records: Dict[str, Dict[str, Any]] = {}

    def issue_metadata(self, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> Dict[str, Any]:
        ttl = int(ttl_seconds)
        if ttl < MIN_TTL_SECONDS or ttl > MAX_TTL_SECONDS:
            raise ValueError(
                f"ttl_seconds must be between {MIN_TTL_SECONDS} and {MAX_TTL_SECONDS}"
            )
        issued_at = float(self._clock())
        return {
            "ticket_id": secrets.token_hex(24),
            "issued_at": issued_at,
            "expires_at": issued_at + ttl,
            "max_uses": 1,
        }

    def register(self, ticket: Mapping[str, Any]) -> None:
        if not verify_v2_ticket_shape(ticket):
            raise ValueError("invalid v2 read ticket")
        ticket_id = str(ticket["ticket_id"])
        record = {
            "sha256": str(ticket["sha256"]),
            "expires_at": float(ticket["expires_at"]),
            "consumed": False,
            "consumed_at": None,
        }
        with self._lock:
            if ticket_id in self._records:
                raise ValueError("duplicate ticket_id")
            self._records[ticket_id] = record

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

        with self._lock:
            record = self._records.get(ticket_id)
            if record is None:
                return TicketClaim(False, ticket_id, "ticket not registered in this ledger")
            if not hmac.compare_digest(str(record["sha256"]), str(ticket["sha256"])):
                return TicketClaim(False, ticket_id, "ticket digest does not match registered ticket")
            if claim_time > float(record["expires_at"]):
                return TicketClaim(False, ticket_id, "ticket expired")
            if bool(record["consumed"]):
                return TicketClaim(False, ticket_id, "ticket already consumed")

            record["consumed"] = True
            record["consumed_at"] = claim_time
            return TicketClaim(True, ticket_id, "ticket claimed for one-time host execution", claim_time)

    def status(self, ticket_id: str) -> Dict[str, Any]:
        with self._lock:
            record = self._records.get(str(ticket_id))
            if record is None:
                return {"known": False, "ticket_id": str(ticket_id)}
            return {
                "known": True,
                "ticket_id": str(ticket_id),
                "expires_at": float(record["expires_at"]),
                "consumed": bool(record["consumed"]),
                "consumed_at": record["consumed_at"],
            }
