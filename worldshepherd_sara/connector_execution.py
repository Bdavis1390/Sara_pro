from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from .connector_control import ConnectorControlPlane, Decision


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

    This broker never performs an external network call. It consumes the same
    ConnectorControlPlane used by policy evaluation and emits a sealed handoff
    ticket that a host integration may execute separately. An action must be
    explicitly listed in the connector's external_read_actions policy; absence
    from the write list is never treated as permission to read.
    """

    def __init__(self, control: ConnectorControlPlane):
        self.control = control

    def plan_read(
        self,
        *,
        connector_id: str,
        action: str,
        actor: str,
        data_class: str = "PUBLIC",
        context: Optional[Mapping[str, Any]] = None,
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

        decision: Decision = self.control.authorize(
            connector_id=connector_id,
            action=action,
            actor=actor,
            data_class=data_class,
            human_approved=False,
            approval_id=None,
            context=dict(context or {}),
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

        payload: Dict[str, Any] = {
            "schema": "worldshepherd.connector.read-ticket.v1",
            "connector_id": connector_id,
            "action": action,
            "actor": actor,
            "data_class": data_class,
            "context": dict(context or {}),
            "policy_envelope_sha256": (
                decision.envelope.get("sha256") if decision.envelope else None
            ),
            "execution_mode": "host_connector_handoff",
            "credential_handling": "outside_sara_broker",
            "write_enabled": False,
            "issued_at": time.time(),
        }
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        payload["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        return ExecutionTicket(
            ok=True,
            mode="host_connector_handoff",
            connector_id=connector_id,
            action=action,
            actor=actor,
            data_class=data_class,
            reason="authorized external read handoff ticket issued",
            ticket=payload,
        )


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
