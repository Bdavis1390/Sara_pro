from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

DATA_CLASS_ORDER = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONTROLLED_UNCLASSIFIED": 2,
    "CREDENTIAL": 3,
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    connector_id: str
    action: str
    actor: str
    reason: str
    requires_human_approval: bool
    envelope: Optional[Dict[str, Any]] = None


class ConnectorControlPlane:
    """Default-deny policy gate for Worldshepherd tools and connectors."""

    def __init__(self, manifest_path: Path):
        self.manifest_path = Path(manifest_path)
        self._manifest = self._load_manifest()
        self.validate_manifest()

    @property
    def manifest(self) -> Dict[str, Any]:
        return self._manifest

    def _load_manifest(self) -> Dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def reload(self) -> None:
        self._manifest = self._load_manifest()
        self.validate_manifest()

    def connectors(self) -> List[Dict[str, Any]]:
        return list(self._manifest.get("connectors", []))

    def tools(self) -> List[Dict[str, Any]]:
        return list(self._manifest.get("tools", []))

    def connector(self, connector_id: str) -> Dict[str, Any]:
        for item in self.connectors():
            if item.get("id") == connector_id:
                return item
        raise KeyError(f"unknown connector: {connector_id}")

    def validate_manifest(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        if self._manifest.get("schema") != "worldshepherd.connectors.v2":
            errors.append("schema must be worldshepherd.connectors.v2")

        connector_ids = [c.get("id") for c in self.connectors()]
        tool_ids = [t.get("id") for t in self.tools()]
        if len(connector_ids) != len(set(connector_ids)):
            errors.append("connector ids must be unique")
        if len(tool_ids) != len(set(tool_ids)):
            errors.append("tool ids must be unique")

        for connector in self.connectors():
            cid = connector.get("id", "<missing>")
            if not connector.get("allowed_actions"):
                warnings.append(f"{cid}: no allowed actions")
            if connector.get("max_data_class") not in DATA_CLASS_ORDER:
                errors.append(f"{cid}: invalid max_data_class")

        if errors:
            raise ValueError("connector manifest invalid: " + "; ".join(errors))

        return {
            "ok": True,
            "warnings": warnings,
            "connectors": len(connector_ids),
            "tools": len(tool_ids),
        }

    def health_snapshot(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for connector in self.connectors():
            status = str(connector.get("status", "unknown"))
            by_status[status] = by_status.get(status, 0) + 1
        return {
            "schema": self._manifest.get("schema"),
            "connectors": len(self.connectors()),
            "tools": len(self.tools()),
            "connector_status": by_status,
            "default_deny": bool(self._manifest.get("governance", {}).get("default_deny", True)),
            "ts": time.time(),
        }

    def authorize(
        self,
        *,
        connector_id: str,
        action: str,
        actor: str,
        data_class: str = "PUBLIC",
        human_approved: bool = False,
        approval_id: Optional[str] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Decision:
        try:
            connector = self.connector(connector_id)
        except KeyError:
            return self._deny(connector_id, action, actor, "unknown connector")

        if action not in set(connector.get("allowed_actions", [])):
            return self._deny(connector_id, action, actor, "action not allow-listed")
        if actor not in set(connector.get("roles", [])):
            return self._deny(connector_id, action, actor, "actor role not authorized")
        if data_class not in DATA_CLASS_ORDER:
            return self._deny(connector_id, action, actor, "unknown data class")

        max_class = str(connector.get("max_data_class", "PUBLIC"))
        if DATA_CLASS_ORDER[data_class] > DATA_CLASS_ORDER[max_class]:
            return self._deny(
                connector_id,
                action,
                actor,
                f"data class {data_class} exceeds connector maximum {max_class}",
            )

        if data_class == "CREDENTIAL":
            return self._deny(connector_id, action, actor, "credential data is outside this control plane")

        external_writes = set(connector.get("external_write_actions", []))
        explicit_approval = set(connector.get("human_approval_actions", []))
        governance = self._manifest.get("governance", {})
        approval_required = action in explicit_approval
        if governance.get("external_write_requires_human_approval", True) and action in external_writes:
            approval_required = True

        if approval_required and not human_approved:
            return self._deny(
                connector_id,
                action,
                actor,
                "human approval required",
                requires_human_approval=True,
            )
        if human_approved and not approval_id:
            return self._deny(
                connector_id,
                action,
                actor,
                "approval_id required for approved actions",
                requires_human_approval=True,
            )

        envelope = self._build_envelope(
            connector_id=connector_id,
            action=action,
            actor=actor,
            data_class=data_class,
            human_approved=human_approved,
            approval_id=approval_id,
            context=dict(context or {}),
        )
        return Decision(
            allowed=True,
            connector_id=connector_id,
            action=action,
            actor=actor,
            reason="authorized by default-deny connector policy",
            requires_human_approval=approval_required,
            envelope=envelope,
        )

    def _deny(
        self,
        connector_id: str,
        action: str,
        actor: str,
        reason: str,
        requires_human_approval: bool = False,
    ) -> Decision:
        return Decision(
            allowed=False,
            connector_id=connector_id,
            action=action,
            actor=actor,
            reason=reason,
            requires_human_approval=requires_human_approval,
        )

    def _build_envelope(
        self,
        *,
        connector_id: str,
        action: str,
        actor: str,
        data_class: str,
        human_approved: bool,
        approval_id: Optional[str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {
            "schema": "worldshepherd.echo.action-envelope.v1",
            "connector_id": connector_id,
            "action": action,
            "actor": actor,
            "data_class": data_class,
            "human_approved": human_approved,
            "approval_id": approval_id,
            "context": context,
            "ts": time.time(),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        payload["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return payload


def decision_to_dict(decision: Decision) -> Dict[str, Any]:
    return {
        "allowed": decision.allowed,
        "connector_id": decision.connector_id,
        "action": decision.action,
        "actor": decision.actor,
        "reason": decision.reason,
        "requires_human_approval": decision.requires_human_approval,
        "envelope": decision.envelope,
    }
