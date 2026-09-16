from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import Role, require_admin, resolve_role
from .event_outbox import EventOutboxError, drain_event_outbox, outbox_status
from .poo_registry_commit import (
    PoODurableCommitError,
    PoODurableCommitRequest,
    load_poo_registry_namespace,
    prepare_poo_durable_commit_patch,
)
from .storage import DurableStore


router = APIRouter(prefix="/admin/poo", tags=["poo-governance"])


def _store(request: Request) -> DurableStore:
    return request.app.state.store


def _drain_delivery_status(durable_store: DurableStore) -> str:
    try:
        drain_event_outbox(durable_store, limit=64)
        status = outbox_status(durable_store.get_registry())
    except (OSError, RuntimeError, ValueError, EventOutboxError):
        return "PENDING_REPLAY"
    return "DELIVERED" if status["pending"] == 0 else "PENDING_REPLAY"


@router.get("/registry")
def get_poo_technical_registry(
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    durable_store = _store(request)
    try:
        namespace = load_poo_registry_namespace(durable_store.get_registry())
    except PoODurableCommitError as exc:
        raise HTTPException(
            status_code=500,
            detail="PoO technical registry validation failed",
        ) from exc
    return {
        "registry": namespace.model_dump(mode="json"),
        "claims_boundary": "INTERNAL_TECHNICAL_REGISTRY_ONLY",
    }


@router.post("/registry/commit")
def commit_poo_technical_registry(
    body: PoODurableCommitRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    durable_store = _store(request)

    def operation(registry: dict[str, Any]):
        return prepare_poo_durable_commit_patch(
            registry,
            body,
            actor=role.value,
        )

    try:
        result = durable_store.transact_registry(operation)
    except EventOutboxError as exc:
        raise HTTPException(
            status_code=503,
            detail="PoO technical commit blocked because durable audit custody is unavailable",
        ) from exc
    except PoODurableCommitError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="PoO technical commit exceeds registry resource limits",
        ) from exc

    delivery = _drain_delivery_status(durable_store)
    return {
        "commit": result.model_dump(mode="json"),
        "audit_delivery": delivery,
        "claims_boundary": "INTERNAL_TECHNICAL_REGISTRY_COMMIT_ONLY",
    }
