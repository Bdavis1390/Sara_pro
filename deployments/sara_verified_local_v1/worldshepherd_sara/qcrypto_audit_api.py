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
from .models import AuditRecord
from .qcrypto_audit_adapter import (
    QCRYPTO_AUDIT_SCHEMA,
    QCryptoAuditAdapterError,
    new_qcrypto_audit_instance_id,
    qcrypto_decision_digest,
    queue_qcrypto_projection_patch,
)
from .qcrypto_audit_verifier import verify_qcrypto_audit_chain
from .qcrypto_echo_config import forwarder_from_environment
from .qcrypto_echo_forwarder import QCryptoEchoConflict, QCryptoEchoForwarderError
from .storage import DurableStore


router = APIRouter(prefix="/admin/qcrypto", tags=["qcrypto-governance"])
_AUDIT_INSTANCE_QUERY = Query(
    min_length=46,
    max_length=46,
    pattern=r"^QCRYPTO-AUDIT-[0-9a-f]{32}$",
)


class QCryptoAuditProjectionRequest(BaseModel):
    """Governance-evidence projection accepted by SARA."""

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
    try:
        drain_event_outbox(durable_store, limit=max(len(event_ids), 1))
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


def _verified_sync_records(
    records: list[dict[str, Any]],
    decision_digest: str,
    audit_instance_id: str,
) -> tuple[list[AuditRecord], dict[str, Any]]:
    verification = verify_qcrypto_audit_chain(
        records,
        decision_digest=decision_digest,
        audit_instance_id=audit_instance_id,
    )
    if not verification.complete or not verification.consistent:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "QCRYPTO audit evidence is not complete and consistent",
                "verification": verification.to_dict(),
            },
        )

    canonical_events = {
        "qcrypto_echo_state",
        "qcrypto_prime_state",
        "qcrypto_sara_state",
        "qcrypto_overwatch_state",
    }
    by_id: dict[str, AuditRecord] = {}
    for raw in records:
        payload = raw.get("payload") if isinstance(raw, dict) else None
        if (
            isinstance(payload, dict)
            and payload.get("decision_digest") == decision_digest
            and payload.get("audit_instance_id") == audit_instance_id
            and raw.get("event") in canonical_events
        ):
            event_id = payload.get("_outbox_event_id")
            if isinstance(event_id, str) and event_id not in by_id:
                by_id[event_id] = AuditRecord.model_validate(raw)

    selected = list(by_id.values())
    if len(selected) != 4 or {record.event for record in selected} != canonical_events:
        raise HTTPException(
            status_code=409,
            detail="Verified QCRYPTO audit instance could not be reduced to four canonical events",
        )
    return selected, verification.to_dict()


@router.post("/audit", status_code=status.HTTP_202_ACCEPTED)
def record_qcrypto_governance_audit(
    body: QCryptoAuditProjectionRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    """Persist one governed QCRYPTO decision through SARA's native audit path."""

    require_admin(role)
    durable_store = _store(request)
    projection = body.model_dump(mode="json", exclude_none=True)

    try:
        decision_digest = qcrypto_decision_digest(projection)
        audit_instance_id = new_qcrypto_audit_instance_id()
    except QCryptoAuditAdapterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    def operation(registry: dict[str, Any]):
        patch, event_ids = queue_qcrypto_projection_patch(
            registry,
            projection,
            actor=role.value,
            audit_instance_id=audit_instance_id,
        )
        return patch, event_ids

    try:
        event_ids = durable_store.transact_registry(operation)
    except QCryptoAuditAdapterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EventOutboxError as exc:
        raise HTTPException(status_code=503, detail="QCRYPTO governance audit outbox is unavailable") from exc
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="QCRYPTO governance audit persistence failed") from exc

    delivery = _delivery_status(durable_store, event_ids)
    return {
        "accepted": True,
        "asset_id": body.asset_id,
        "decision_digest": decision_digest,
        "audit_instance_id": audit_instance_id,
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
        Query(min_length=71, max_length=71, pattern=r"^sha256:[0-9a-f]{64}$"),
    ],
    audit_instance_id: Annotated[str | None, _AUDIT_INSTANCE_QUERY] = None,
    limit: Annotated[int, Query(ge=4, le=500)] = 500,
) -> dict[str, Any]:
    """Reconstruct one decision or one concrete audit submission from SARA."""

    require_admin(role)
    records = _store(request).read_audit(limit)
    verification = verify_qcrypto_audit_chain(
        records,
        decision_digest=decision_digest,
        audit_instance_id=audit_instance_id,
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


@router.post("/audit/echo-sync")
def sync_qcrypto_governance_audit_to_echo(
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
    decision_digest: Annotated[
        str,
        Query(min_length=71, max_length=71, pattern=r"^sha256:[0-9a-f]{64}$"),
    ],
    audit_instance_id: Annotated[str, _AUDIT_INSTANCE_QUERY],
    limit: Annotated[int, Query(ge=4, le=500)] = 500,
) -> dict[str, Any]:
    """Forward one verified, concrete QCRYPTO audit instance to ECHO."""

    require_admin(role)
    durable_store = _store(request)
    raw_records = durable_store.read_audit(limit)
    selected, verification = _verified_sync_records(
        raw_records,
        decision_digest,
        audit_instance_id,
    )

    sync_identity = {
        "source_decision_digest": decision_digest,
        "source_audit_instance_id": audit_instance_id,
    }
    try:
        forwarder = forwarder_from_environment()
        if forwarder is None:
            raise QCryptoEchoForwarderError("ECHO forwarding is not configured")
        result = forwarder.sync(selected)
    except QCryptoEchoConflict as exc:
        durable_store.append_audit(
            AuditRecord.create(
                event="qcrypto_echo_sync_conflict",
                actor=role.value,
                payload=sync_identity,
            )
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except QCryptoEchoForwarderError as exc:
        durable_store.append_audit(
            AuditRecord.create(
                event="qcrypto_echo_sync_pending",
                actor=role.value,
                payload=sync_identity,
            )
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    durable_store.append_audit(
        AuditRecord.create(
            event="qcrypto_echo_sync_completed",
            actor=role.value,
            payload={
                **sync_identity,
                "event_ids": list(result.event_ids),
                "stored_count": result.stored,
                "deduplicated_count": result.deduplicated,
                "execution_authority": False,
                "live_value_authorized": False,
            },
        )
    )
    return {
        "verification": verification,
        "sync": result.to_dict(),
        "audit_window_limit": limit,
        "window_complete_for_history": False,
    }
