from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .connector_control import ConnectorControlPlane, decision_to_dict
from . import worldshepherd_gateway as gateway

CONNECTOR_MANIFEST = Path(
    os.getenv(
        "SARA_CONNECTOR_MANIFEST",
        str(gateway.DATA_DIR / "worldshepherd_connectors.v2.json"),
    )
)


def _control_plane() -> ConnectorControlPlane:
    if not CONNECTOR_MANIFEST.exists():
        raise HTTPException(
            status_code=503,
            detail=f"connector manifest unavailable: {CONNECTOR_MANIFEST}",
        )
    try:
        return ConnectorControlPlane(CONNECTOR_MANIFEST)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"connector manifest invalid: {exc}") from exc


def _minimal_audit_payload(
    *,
    connector_id: str,
    action: str,
    data_class: str,
    allowed: bool,
    reason: str,
    envelope_sha256: str | None,
) -> Dict[str, Any]:
    return {
        "connector_id": connector_id,
        "action": action,
        "data_class": data_class,
        "allowed": allowed,
        "reason": reason,
        "envelope_sha256": envelope_sha256,
    }


@gateway.router.get("/api/worldshepherd/connectors/status")
def connector_status(authorization: str | None = Header(default=None)):
    actor = gateway.require_operator_or_admin(authorization)
    plane = _control_plane()
    result = plane.health_snapshot()
    result["execution_enabled"] = False
    result["actor"] = actor
    gateway.audit("connector_status_read", actor, {"connectors": result.get("connectors", 0)})
    return JSONResponse(result)


@gateway.router.get("/api/worldshepherd/connectors/catalog")
def connector_catalog(authorization: str | None = Header(default=None)):
    actor = gateway.require_admin(authorization)
    plane = _control_plane()
    validation = plane.validate_manifest()
    gateway.audit("connector_catalog_read", actor, validation)
    return {
        "schema": plane.manifest.get("schema"),
        "governance": plane.manifest.get("governance", {}),
        "connectors": plane.connectors(),
        "tools": plane.tools(),
        "validation": validation,
    }


@gateway.router.post("/api/worldshepherd/connectors/evaluate")
async def connector_evaluate(
    request: Request,
    authorization: str | None = Header(default=None),
):
    actor = gateway.require_operator_or_admin(authorization)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="request must be a JSON object")

    connector_id = str(payload.get("connector_id", "")).strip()
    action = str(payload.get("action", "")).strip()
    data_class = str(payload.get("data_class", "PUBLIC")).strip()
    human_approved = bool(payload.get("human_approved", False))
    approval_id = payload.get("approval_id")
    context = payload.get("context", {})

    if not connector_id or not action:
        raise HTTPException(status_code=400, detail="connector_id and action are required")
    if not isinstance(context, dict):
        raise HTTPException(status_code=400, detail="context must be a JSON object")

    if human_approved and actor != "admin":
        gateway.audit(
            "connector_policy_denied",
            actor,
            {
                "connector_id": connector_id,
                "action": action,
                "reason": "admin approval path required",
            },
        )
        raise HTTPException(status_code=403, detail="admin approval path required")

    plane = _control_plane()
    decision = plane.authorize(
        connector_id=connector_id,
        action=action,
        actor=actor,
        data_class=data_class,
        human_approved=human_approved,
        approval_id=str(approval_id) if approval_id is not None else None,
        context=context,
    )
    envelope_sha = decision.envelope.get("sha256") if decision.envelope else None
    gateway.audit(
        "connector_policy_evaluated",
        actor,
        _minimal_audit_payload(
            connector_id=connector_id,
            action=action,
            data_class=data_class,
            allowed=decision.allowed,
            reason=decision.reason,
            envelope_sha256=envelope_sha,
        ),
    )
    return JSONResponse(decision_to_dict(decision))
