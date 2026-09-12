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
    superseded_authorization_registry_patch,
    verified_authorization_registry_patch,
)
from .storage import DurableStore


router = APIRouter(prefix="/admin/prime", tags=["prime-custody"])


class _PassportNotFound(LookupError):
    pass


class _PassportAlreadyExists(ValueError):
    pass


class _PassportRegistryInvalid(RuntimeError):
    pass


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


def _load_from_registry(registry: dict[str, Any], prime_id: str) -> PrimeDigitalPassport:
    passport = load_passport(registry, prime_id)
    if passport is None:
        raise _PassportNotFound(prime_id)
    return passport


def _load_or_404(durable_store: DurableStore, prime_id: str) -> PrimeDigitalPassport:
    try:
        return _load_from_registry(durable_store.get_registry(), prime_id)
    except _PassportNotFound as exc:
        raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="PRIME passport registry validation failed") from exc


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


def _passport_with_superseded_authorization_patch(
    registry: dict[str, Any],
    *,
    prior_authorization_id: str | None,
    updated_passport: PrimeDigitalPassport,
    transition_id: str,
    reason: str,
) -> dict[str, Any]:
    patch = passport_registry_patch(registry, updated_passport)
    if prior_authorization_id:
        patch.update(
            superseded_authorization_registry_patch(
                registry,
                authorization_id=prior_authorization_id,
                transition_id=transition_id,
                reason=reason,
            )
        )
    return patch


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

    def operation(registry: dict[str, Any]):
        if load_passport(registry, prime_id) is not None:
            raise _PassportAlreadyExists(prime_id)
        passport = create_passport(
            prime_id=prime_id,
            hardware_revision=body.hardware_revision,
            software_revision=body.software_revision,
            evidence_refs=body.evidence_refs,
        )
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
        return passport_registry_patch(registry, passport), (passport, payload)

    try:
        passport, payload = durable_store.transact_registry(operation)
    except _PassportAlreadyExists as exc:
        raise HTTPException(status_code=409, detail="PRIME passport already exists") from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="PRIME passport registry validation failed") from exc

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

    def operation(registry: dict[str, Any]):
        passport = _load_from_registry(registry, prime_id)
        prior_authorization_id = passport.custody.requalification_release_authorization_id
        updated, payload = complete_mission(passport, body)
        supersession_error: str | None = None
        try:
            patch = _passport_with_superseded_authorization_patch(
                registry,
                prior_authorization_id=prior_authorization_id,
                updated_passport=updated,
                transition_id=payload["transition_id"],
                reason="MISSION_COMPLETED",
            )
        except PrimeSentinelAuthorizationError as exc:
            # Mission completion is safety-tightening. Persist quarantine even if
            # authorization-ledger integrity is broken.
            patch = passport_registry_patch(registry, updated)
            supersession_error = str(exc)
            payload["details"]["authorization_supersession"] = "FAILED_SAFE_QUARANTINE"
        else:
            if prior_authorization_id:
                payload["details"]["superseded_authorization_id"] = prior_authorization_id
        return patch, (updated, payload, prior_authorization_id, supersession_error)

    try:
        updated, payload, prior_authorization_id, supersession_error = durable_store.transact_registry(operation)
    except _PassportNotFound as exc:
        raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="PRIME passport registry validation failed") from exc

    if supersession_error:
        _append_sentinel_rejection(
            durable_store,
            role,
            prime_id=prime_id,
            authorization_id=prior_authorization_id,
            reason=f"mission quarantine preserved; authorization supersession failed: {supersession_error}",
        )
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
    context: dict[str, str | None] = {"authorization_id": None}

    def operation(registry: dict[str, Any]):
        passport = _load_from_registry(registry, prime_id)
        prior_authorization_id = passport.custody.requalification_release_authorization_id
        context["authorization_id"] = prior_authorization_id
        updated, payload = update_requalification_evidence(passport, body)
        patch = _passport_with_superseded_authorization_patch(
            registry,
            prior_authorization_id=prior_authorization_id,
            updated_passport=updated,
            transition_id=payload["transition_id"],
            reason="REQUALIFICATION_EVIDENCE_CHANGED",
        )
        if prior_authorization_id:
            payload["details"]["superseded_authorization_id"] = prior_authorization_id
        return patch, (updated, payload)

    try:
        updated, payload = durable_store.transact_registry(operation)
    except _PassportNotFound as exc:
        raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
    except PrimeSentinelAuthorizationError as exc:
        _append_sentinel_rejection(
            durable_store,
            role,
            prime_id=prime_id,
            authorization_id=context["authorization_id"],
            reason=f"requalification update rejected because authorization supersession failed: {exc}",
        )
        raise HTTPException(
            status_code=409,
            detail="PRIME SENTINEL authorization supersession failed",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="PRIME passport registry validation failed") from exc

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

    def operation(registry: dict[str, Any]):
        try:
            passport = _load_from_registry(registry, prime_id)
        except ValueError as exc:
            raise _PassportRegistryInvalid from exc
        if not isinstance(registry.get("PRIME_SENTINEL_AUTHORIZATIONS", {}), dict):
            raise _PassportRegistryInvalid("PRIME SENTINEL authorization registry validation failed")
        verified = verifier.verify(body)
        updated, payload = apply_verified_requalification_authorization(passport, verified)
        patch = verified_authorization_registry_patch(registry, verified)
        patch.update(passport_registry_patch(registry, updated))
        return patch, (updated, payload)

    try:
        updated, payload = durable_store.transact_registry(operation)
    except _PassportNotFound as exc:
        raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
    except _PassportRegistryInvalid as exc:
        raise HTTPException(
            status_code=500,
            detail="PRIME passport registry validation failed",
        ) from exc
    except (PrimeSentinelAuthorizationError, ValueError) as exc:
        _append_sentinel_rejection(
            durable_store,
            role,
            prime_id=prime_id,
            authorization_id=body.authorization_id,
            reason=str(exc),
        )
        raise HTTPException(status_code=403, detail="PRIME SENTINEL authorization rejected") from exc

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

    def operation(registry: dict[str, Any]):
        passport = _load_from_registry(registry, prime_id)
        authorization_id = passport.custody.requalification_release_authorization_id
        releasing_quarantine = (
            passport.custody.state == PrimeCustodyState.QUARANTINED_FOR_REQUALIFICATION
            and authorization_id is not None
        )

        if releasing_quarantine:
            if not verifier.configured:
                return None, (
                    "VERIFIER_NOT_CONFIGURED",
                    passport,
                    authorization_id,
                    None,
                    None,
                    None,
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
                return None, (
                    "AUTHORIZATION_INVALID",
                    passport,
                    authorization_id,
                    str(exc),
                    None,
                    None,
                )

        updated, disposition, reasons, payload = activate_pack(passport, body)
        if disposition != PrimeActivationDisposition.ACTIVATION_ALLOWED:
            return None, (
                "DECISION_ONLY",
                updated,
                authorization_id,
                None,
                disposition,
                (reasons, payload),
            )

        if authorization_id and not releasing_quarantine:
            # Pre-ledger READY records may carry an obsolete release ID. Clear it
            # during this successful custody transition to avoid later invalid
            # supersession, without treating the old ID as a new authorization.
            updated = updated.model_copy(update={
                "custody": updated.custody.model_copy(update={
                    "requalification_release_authorization_id": None,
                    "requalification_release_target_environment": None,
                    "requalification_release_key_id": None,
                }),
            })
            payload["details"]["legacy_release_authorization_cleared"] = True
        patch = passport_registry_patch(registry, updated)
        if releasing_quarantine and authorization_id:
            patch.update(
                consumed_authorization_registry_patch(
                    registry,
                    authorization_id=authorization_id,
                    transition_id=payload["transition_id"],
                )
            )
        return patch, (
            "ACTIVATED",
            updated,
            authorization_id,
            None,
            disposition,
            (reasons, payload),
        )

    try:
        state, passport, authorization_id, auth_error, disposition, decision = durable_store.transact_registry(operation)
    except _PassportNotFound as exc:
        raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
    except PrimeSentinelAuthorizationError as exc:
        _append_sentinel_rejection(
            durable_store,
            role,
            prime_id=prime_id,
            reason=str(exc),
        )
        return JSONResponse(
            {"detail": "PRIME SENTINEL authorization consumption failed"},
            status_code=409,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="PRIME passport registry validation failed") from exc

    if state == "VERIFIER_NOT_CONFIGURED":
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

    if state == "AUTHORIZATION_INVALID":
        _append_sentinel_rejection(
            durable_store,
            role,
            prime_id=prime_id,
            authorization_id=authorization_id,
            reason=auth_error or "authorization invalid",
        )
        return JSONResponse(
            {
                "disposition": PrimeActivationDisposition.REQUALIFICATION_REQUIRED.value,
                "reasons": [auth_error or "authorization invalid"],
                "passport": passport.model_dump(mode="json"),
            },
            status_code=409,
        )

    assert disposition is not None and decision is not None
    reasons, payload = decision
    response: dict[str, Any] = {
        "disposition": disposition.value,
        "reasons": reasons,
        "passport": passport.model_dump(mode="json"),
        "provenance": payload,
    }
    _append_provenance(durable_store, role, payload)

    if disposition == PrimeActivationDisposition.ACTIVATION_ALLOWED:
        return JSONResponse(response, status_code=200)
    if disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED:
        return JSONResponse(response, status_code=409)
    return JSONResponse(response, status_code=403)
