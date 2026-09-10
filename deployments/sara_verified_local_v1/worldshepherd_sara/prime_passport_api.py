from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from .auth import Role, require_admin, resolve_role
from .models import AuditRecord
from .prime_configuration_custody import PrimeActivationDisposition
from .prime_passport import (
    PrimeDigitalPassport,
    PrimeMissionCompletionRequest,
    PrimePackActivationRequest,
    PrimePassportCreateRequest,
    PrimeRequalificationEvidenceRequest,
    activate_pack,
    complete_mission,
    create_passport,
    custody_provenance_payload,
    load_passport,
    new_transition_id,
    passport_registry_patch,
    update_requalification_evidence,
)
from .storage import DurableStore


router = APIRouter(prefix="/admin/prime", tags=["prime-custody"])


def _store(request: Request) -> DurableStore:
    return request.app.state.store


def _load_or_404(durable_store: DurableStore, prime_id: str) -> PrimeDigitalPassport:
    try:
        passport = load_passport(durable_store.get_registry(), prime_id)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="PRIME passport registry validation failed") from exc
    if passport is None:
        raise HTTPException(status_code=404, detail="PRIME passport not found")
    return passport


def _persist(durable_store: DurableStore, passport: PrimeDigitalPassport) -> None:
    registry = durable_store.get_registry()
    durable_store.patch_registry(passport_registry_patch(registry, passport))


def _append_provenance(
    durable_store: DurableStore,
    role: Role,
    payload: dict[str, Any],
) -> None:
    durable_store.append_audit(
        AuditRecord.create(
            event="prime_custody_provenance",
            actor=role.value,
            payload=payload,
        )
    )


@router.get("/{prime_id}/passport")
def get_prime_passport(
    prime_id: str,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    passport = _load_or_404(_store(request), prime_id)
    return {"passport": passport.model_dump(mode="json")}


@router.post("/{prime_id}/passport", status_code=201)
def create_prime_passport(
    prime_id: str,
    body: PrimePassportCreateRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    durable_store = _store(request)
    try:
        existing = load_passport(durable_store.get_registry(), prime_id)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="PRIME passport registry validation failed") from exc
    if existing is not None:
        raise HTTPException(status_code=409, detail="PRIME passport already exists")

    passport = create_passport(
        prime_id=prime_id,
        hardware_revision=body.hardware_revision,
        software_revision=body.software_revision,
        evidence_refs=body.evidence_refs,
    )
    _persist(durable_store, passport)
    payload = custody_provenance_payload(
        transition_id=new_transition_id(),
        prime_id=prime_id,
        action="PASSPORT_CREATED",
        previous_state="UNREGISTERED",
        new_state=passport.custody.state.value,
        evidence_refs=body.evidence_refs,
        hardware_revision=body.hardware_revision,
        software_revision=body.software_revision,
    )
    _append_provenance(durable_store, role, payload)
    return {"passport": passport.model_dump(mode="json"), "provenance": payload}


@router.post("/{prime_id}/mission-complete")
def complete_prime_mission(
    prime_id: str,
    body: PrimeMissionCompletionRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    durable_store = _store(request)
    passport = _load_or_404(durable_store, prime_id)
    updated, payload = complete_mission(passport, body)
    _persist(durable_store, updated)
    _append_provenance(durable_store, role, payload)
    return {"passport": updated.model_dump(mode="json"), "provenance": payload}


@router.patch("/{prime_id}/requalification")
def patch_prime_requalification(
    prime_id: str,
    body: PrimeRequalificationEvidenceRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    durable_store = _store(request)
    passport = _load_or_404(durable_store, prime_id)
    updated, payload = update_requalification_evidence(passport, body)
    _persist(durable_store, updated)
    _append_provenance(durable_store, role, payload)
    return {"passport": updated.model_dump(mode="json"), "provenance": payload}


@router.post("/{prime_id}/activate-pack")
def activate_prime_pack(
    prime_id: str,
    body: PrimePackActivationRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> JSONResponse:
    require_admin(role)
    durable_store = _store(request)
    passport = _load_or_404(durable_store, prime_id)
    updated, disposition, reasons, payload = activate_pack(passport, body)
    _append_provenance(durable_store, role, payload)

    response: dict[str, Any] = {
        "disposition": disposition.value,
        "reasons": reasons,
        "passport": updated.model_dump(mode="json"),
        "provenance": payload,
    }

    if disposition == PrimeActivationDisposition.ACTIVATION_ALLOWED:
        _persist(durable_store, updated)
        return JSONResponse(response, status_code=200)
    if disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED:
        return JSONResponse(response, status_code=409)
    return JSONResponse(response, status_code=403)
