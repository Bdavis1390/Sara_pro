from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ClaimReconciliation:
    state: str
    ticket_id: str
    reason: str
    may_execute_connector: bool = False
    may_retry_claim: bool = False


class UnknownClaimOutcome(RuntimeError):
    """The database claim may have committed but the client did not confirm it.

    An UNKNOWN outcome must never be treated as authorization to execute an
    external connector. Callers must reconcile through a fresh connection.
    """

    def __init__(self, ticket_id: str, message: str = "claim commit outcome is unknown") -> None:
        super().__init__(message)
        self.ticket_id = str(ticket_id)
        self.state = "unknown"
        self.may_execute_connector = False
        self.may_retry_claim = False


def reconcile_claim_status(
    *,
    ticket_id: str,
    ticket_sha256: str,
    status: Mapping[str, Any],
) -> ClaimReconciliation:
    """Convert fresh-store status into a fail-closed recovery decision.

    Even if the ticket is observed consumed after an ambiguous commit, ownership
    cannot be proven by the current schema. The result therefore remains
    non-executable. Only a fresh observation that the ticket is still unconsumed
    and unexpired is considered retryable, and retry is never automatic.
    """

    if not status.get("known"):
        return ClaimReconciliation(
            state="not_found",
            ticket_id=ticket_id,
            reason="ticket not found during reconciliation",
        )

    observed_digest = status.get("ticket_sha256")
    if observed_digest != ticket_sha256:
        return ClaimReconciliation(
            state="digest_mismatch",
            ticket_id=ticket_id,
            reason="ticket digest mismatch during reconciliation",
        )

    if bool(status.get("consumed")):
        return ClaimReconciliation(
            state="consumed_ownership_unknown",
            ticket_id=ticket_id,
            reason="ticket is consumed but claimant ownership cannot be proven",
        )

    if bool(status.get("expired")):
        return ClaimReconciliation(
            state="expired",
            ticket_id=ticket_id,
            reason="ticket expired before reconciliation completed",
        )

    return ClaimReconciliation(
        state="unconsumed_retryable",
        ticket_id=ticket_id,
        reason="fresh status shows ticket remains unconsumed and unexpired",
        may_retry_claim=True,
    )
