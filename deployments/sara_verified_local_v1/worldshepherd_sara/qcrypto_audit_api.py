from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

from .auth import Role, require_admin, resolve_role
from .event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    EventOutboxError,
    drain_event_outbox,
    outbox_status,
)
from .qcrypto_audit_adapter import (
    QCRYPTO_AUDIT_SCHEMA,
    QCryptoAuditAdapterError,
    qcrypto_decision_digest,
    queue_qcrypto_projection_patch,
)
from .qcrypto_audit_verifier import verify_qcrypto_audit_chain
from .storage import DurableStore


router = APIRouter(prefix="/admin/qcrypto", tags=["qcrypto-governance"])


class QCryptoAuditProjectionRequest(BaseModel):
    """Governance-evidence projection accepted by SARA.

    This request is intentionally incapable of authorizing or executing a
    cryptographic migration. The execution/compliance flags are required and
    must remain false at the adapter boundary.
    """

    model_config = ConfigDict(extra="forbid")

    schema: str = Field(default=QCRYPTO_AUDIT_SCHEMA, min_length=1, max_length=128)
    asset_id: str = Field(min_length=1, max_length=256)
    echo_state: str = Field(min_length=1, max_length=256)
    prime_state: str = Field(min_length=1, max_length=256)
    sara_state: str = Field(min_length=1, max_length=256)
    overwatch_state: str = Field(min_length=1, max_length=256)
    priority: str = Field(min_length=1, max_length=128)
    human_approval_required: bool
    migration_executed: bool
    execution_authority: bool
    live_value_authorized: bool
    federal_compliance_established: bool
    ws_cae_conformance_established: bool
    claim_boundary: str = Field(min_length=1, max_length=512)
    correlation_id: str | None = Field(default=None, min_length=1, max_length=128)


def _store(request: Request) -> DurableStore:
    return request.app.state.store


def _delivery_status(durable_store: DurableStore, event_ids: list[str]) -> str:
    """Try delivery and verify the specific QCRYPTO events, not a drain count."""
    try:
        drain_event_outbox(
            durable_store,
            limit=max(len(event_ids), 1),
        )
        registry = durable_store.get_registry()
        status_snapshot = outbox_status(registry)
    except (OSError, RuntimeError, ValueError, EventOutboxError):
        return "PENDING_REPLAY"

    if status_snapshot["malformed"]:
        return "PENDING_REPLAY"
    raw_records = registry.get(EVENT_OUTBOX_REGISTRY_KEY, {})
    if not isinstance(raw_records, dict):
        return "PENDING_REPLAY"
    for event_id in event_ids:
        entry = raw_records.get(event_id)
        if not isinstance(entry, dict) or entry.get("status") != "DELIVERED":
            return "PENDING_REPLAY"
    return "DELIVERED"


@router.post("/audit", status_code=status.HTTP_202_ACCEPTED)
def record_qcrypto_governance_audit(
    body: QCryptoAuditProjectionRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    """Persist one governed QCRYPTO decision through SARA's native audit path.

    Acceptance means governance evidence was durably queued. It does not mean
    migration execution, live-value authorization, Federal compliance, or
    WS-CAE conformance has been established.
    """

    require_admin(role)
    durable_store = _store(request)
    projection = body.model_dump(mode="json", exclude_none=True)

    try:
        decision_digest = qcrypto_decision_digest(projection)
    except QCryptoAuditAdapterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    def operation(registry: dict[str, Any]):
        patch, event_ids = queue_qcrypto_projection_patch(
            registry,
            projection,
            actor=role.value,
        )
        return patch, event_ids

    try:
        event_ids = durable_store.transact_registry(operation)
    except QCryptoAuditAdapterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EventOutboxError as exc:
        raise HTTPException(
            status_code=503,
            detail="QCRYPTO governance audit outbox is unavailable",
        ) from exc
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="QCRYPTO governance audit persistence failed",
        ) from exc

    delivery = _delivery_status(durable_store, event_ids)
    return {
        "accepted": True,
        "asset_id": body.asset_id,
        "decision_digest": decision_digest,
        "event_ids": event_ids,
        "provenance_delivery": delivery,
        "migration_executed": False,
        "execution_authority": False,
        "live_value_authorized": False,
        "federal_compliance_established": False,
        "ws_cae_conformance_established": False,
        "claim_boundary": body.claim_boundary,
    }


@router.get("/audit/verify")
def verify_qcrypto_governance_audit(
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
    decision_digest: Annotated[
        str,
        Query(
            min_length=71,
            max_length=71,
            pattern=r"^sha256:[0-9a-f]{64}$",
        ),
    ],
    limit: Annotated[int, Query(ge=4, le=500)] = 500,
) -> dict[str, Any]:
    """Reconstruct one decision from a bounded window of native SARA audit data."""

    require_admin(role)
    records = _store(request).read_audit(limit)
    verification = verify_qcrypto_audit_chain(
        records,
        decision_digest=decision_digest,
    )
    return {
        "verification": verification.to_dict(),
        "audit_window_limit": limit,
        "audit_window_record_count": len(records),
        "window_complete_for_history": False,
        "window_note": (
            "Verification applies only to the bounded audit window returned by SARA; "
            "it is not a whole-history or external-attestation claim."
        ),
    }
