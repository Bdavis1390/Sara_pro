from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from .connector_control import ConnectorControlPlane, Decision
from .connector_ticket_lifecycle import (
    DEFAULT_TTL_SECONDS,
    READ_TICKET_SCHEMA_V2,
    ReadTicketLedger,
    canonical_sha256,
    context_sha256,
)


@dataclass(frozen=True)
class ExecutionTicket:
    ok: bool
    mode: str
    connector_id: str
    action: str
    actor: str
    data_class: str
    reason: str
    ticket: Optional[Dict[str, Any]] = None


class ReadExecutionBroker:
    """Credential-blind broker for explicitly classified external read handoffs.

    The broker never performs an external network call. It emits short-lived,
    single-use tickets for host-side execution and keeps raw operation context
    out of the ticket and PRIME/ECHO policy envelope by substituting a canonical
    context digest.
    """

    def __init__(
        self,
        control: ConnectorControlPlane,
        *,
        ledger: Optional[ReadTicketLedger] = None,
    ) -> None:
        self.control = control
        self.ledger = ledger or ReadTicketLedger()

    def plan_read(
        self,
        *,
        connector_id: str,
        action: str,
        actor: str,
        data_class: str = "PUBLIC",
        context: Optional[Mapping[str, Any]] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> ExecutionTicket:
        try:
            connector = self.control.connector(connector_id)
        except KeyError:
            connector = None

        if connector is None:
            return ExecutionTicket(
                ok=False,
                mode="blocked",
                connector_id=connector_id,
                action=action,
                actor=actor,
                data_class=data_class,
                reason="unknown connector",
            )

        if not str(connector.get("kind", "")).startswith("external_"):
            return ExecutionTicket(
                ok=False,
                mode="blocked",
                connector_id=connector_id,
                action=action,
                actor=actor,
                data_class=data_class,
                reason="connector is not an external handoff target",
            )

        read_actions = set(connector.get("external_read_actions", []))
        if action not in read_actions:
            return ExecutionTicket(
                ok=False,
                mode="blocked",
                connector_id=connector_id,
                action=action,
                actor=actor,
                data_class=data_class,
                reason="action not explicitly classified as an external read",
            )

        digest = context_sha256(context)
        decision: Decision = self.control.authorize(
            connector_id=connector_id,
            action=action,
            actor=actor,
            data_class=data_class,
            human_approved=False,
            approval_id=None,
            context={"context_sha256": digest},
        )
        if not decision.allowed:
            return ExecutionTicket(
                ok=False,
                mode="blocked",
                connector_id=connector_id,
                action=action,
                actor=actor,
                data_class=data_class,
                reason=decision.reason,
            )

        try:
            lifecycle = self.ledger.issue_metadata(ttl_seconds=ttl_seconds)
        except ValueError as exc:
            return ExecutionTicket(
                ok=False,
                mode="blocked",
                connector_id=connector_id,
                action=action,
                actor=actor,
                data_class=data_class,
                reason=str(exc),
            )

        payload: Dict[str, Any] = {
            "schema": READ_TICKET_SCHEMA_V2,
            "ticket_id": lifecycle["ticket_id"],
            "connector_id": connector_id,
            "action": action,
            "actor": actor,
            "data_class": data_class,
            "context_sha256": digest,
            "policy_envelope_sha256": (
                decision.envelope.get("sha256") if decision.envelope else None
            ),
            "execution_mode": "host_connector_handoff",
            "credential_handling": "outside_sara_broker",
            "write_enabled": False,
            "max_uses": lifecycle["max_uses"],
            "issued_at": lifecycle["issued_at"],
            "expires_at": lifecycle["expires_at"],
        }
        payload["sha256"] = canonical_sha256(payload)
        self.ledger.register(payload)

        return ExecutionTicket(
            ok=True,
            mode="host_connector_handoff",
            connector_id=connector_id,
            action=action,
            actor=actor,
            data_class=data_class,
            reason="authorized short-lived single-use external read ticket issued",
            ticket=payload,
        )

    def claim_for_execution(
        self,
        ticket: Mapping[str, Any],
        *,
        now: Optional[float] = None,
    ) -> Dict[str, Any]:
        claim = self.ledger.claim(ticket, now=now)
        return {
            "ok": claim.ok,
            "ticket_id": claim.ticket_id,
            "reason": claim.reason,
            "consumed_at": claim.consumed_at,
        }


def ticket_to_dict(ticket: ExecutionTicket) -> Dict[str, Any]:
    return {
        "ok": ticket.ok,
        "mode": ticket.mode,
        "connector_id": ticket.connector_id,
        "action": ticket.action,
        "actor": ticket.actor,
        "data_class": ticket.data_class,
        "reason": ticket.reason,
        "ticket": ticket.ticket,
    }
