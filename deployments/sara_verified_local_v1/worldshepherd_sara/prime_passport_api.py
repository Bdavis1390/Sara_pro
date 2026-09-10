from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from .auth import Role, require_admin, resolve_role
from .models import AuditRecord
from .prime_configuration_custody import PrimeActivationDisposition, PrimeCustodyState
from .prime_passport import (
    PrimeDigitalPassport,
    PrimeMissionCompletionRequest,
    PrimePackActivationRequest,
    PrimePassportCreateRequest,
    PrimeRequalificationEvidenceRequest,
    activate_pack,
    apply_verified_requalification_authorization,
    complete_mission,
    create_passport,
    custody_provenance_payload,
    load_passport,
    new_transition_id,
    passport_registry_patch,
    update_requalification_evidence,
)
from .prime_sentinel_authorization import (
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
    assert_recorded_authorization_usable,
    consumed_authorization_registry_patch,
    verified_authorization_registry_patch,
)
from .storage import DurableStore


router = APIRouter(prefix="/admin/prime", tags=["prime-custody"])


def _store(request: Request) -> DurableStore:
    return request.app.state.store


def _sentinel_verifier(request: Request) -> PrimeSentinelVerifier:
    verifier = request.app.state.prime_sentinel_verifier
    if not verifier.configured:
        raise HTTPException(
            status_code=503,
            detail="PRIME SENTINEL public-key verification is not configured",
        )
    return verifier


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


def _append_sentinel_rejection(
    durable_store: DurableStore,
    role: Role,
    *,
    prime_id: str,
    reason: str,
    authorization_id: str | None = None,
) -> None:
    durable_store.append_audit(
        AuditRecord.create(
            event="prime_sentinel_authorization_rejected",
            actor=role.value,
            payload={
                "prime_id": prime_id,
                "authorization_id": authorization_id,
                "reason": reason,
                "claims_boundary": "Software authorization decision only; no physical qualification claim.",
            },
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


@router.post("/{prime_id}/requalification/authorize")
def authorize_prime_requalification(
    prime_id: str,
    body: PrimeSentinelAuthorizationAssertion,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    durable_store = _store(request)
    verifier = _sentinel_verifier(request)
    passport = _load_or_404(durable_store, prime_id)

    try:
        verified = verifier.verify(body)
        updated, payload = apply_verified_requalification_authorization(passport, verified)
        registry = durable_store.get_registry()
        auth_patch = verified_authorization_registry_patch(registry, verified)
        passport_patch = passport_registry_patch(registry, updated)
    except (PrimeSentinelAuthorizationError, ValueError) as exc:
        _append_sentinel_rejection(
            durable_store,
            role,
            prime_id=prime_id,
            authorization_id=body.authorization_id,
            reason=str(exc),
        )
        raise HTTPException(status_code=403, detail="PRIME SENTINEL authorization rejected") from exc

    durable_store.patch_registry({**passport_patch, **auth_patch})
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
    verifier = request.app.state.prime_sentinel_verifier
    passport = _load_or_404(durable_store, prime_id)
    registry = durable_store.get_registry()

    authorization_id = passport.custody.requalification_release_authorization_id
    if passport.custody.state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION and authorization_id:
        if not verifier.configured:
            _append_sentinel_rejection(
                durable_store,
                role,
                prime_id=prime_id,
                authorization_id=authorization_id,
                reason="PRIME SENTINEL public-key verification is not configured",
            )
            return JSONResponse(
                {"detail": "PRIME SENTINEL authorization cannot be revalidated"},
                status_code=503,
            )
        try:
            assert_recorded_authorization_usable(
                registry,
                authorization_id=authorization_id,
                prime_id=prime_id,
                target_environment=body.pack.target_environment,
                verifier=verifier,
            )
        except PrimeSentinelAuthorizationError as exc:
            _append_sentinel_rejection(
                durable_store,
                role,
                prime_id=prime_id,
                authorization_id=authorization_id,
                reason=str(exc),
            )
            return JSONResponse(
                {
                    "disposition": PrimeActivationDisposition.REQUALIFICATION_REQUIRED.value,
                    "reasons": [str(exc)],
                    "passport": passport.model_dump(mode="json"),
                },
                status_code=409,
            )

    updated, disposition, reasons, payload = activate_pack(passport, body)
    _append_provenance(durable_store, role, payload)

    response: dict[str, Any] = {
        "disposition": disposition.value,
        "reasons": reasons,
        "passport": updated.model_dump(mode="json"),
        "provenance": payload,
    }

    if disposition == PrimeActivationDisposition.ACTIVATION_ALLOWED:
        patch = passport_registry_patch(registry, updated)
        if authorization_id:
            try:
                patch.update(
                    consumed_authorization_registry_patch(
                        registry,
                        authorization_id=authorization_id,
                        transition_id=payload["transition_id"],
                    )
                )
            except PrimeSentinelAuthorizationError as exc:
                _append_sentinel_rejection(
                    durable_store,
                    role,
                    prime_id=prime_id,
                    authorization_id=authorization_id,
                    reason=str(exc),
                )
                return JSONResponse(
                    {"detail": "PRIME SENTINEL authorization consumption failed"},
                    status_code=409,
                )
        durable_store.patch_registry(patch)
        return JSONResponse(response, status_code=200)
    if disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED:
        return JSONResponse(response, status_code=409)
    return JSONResponse(response, status_code=403)
