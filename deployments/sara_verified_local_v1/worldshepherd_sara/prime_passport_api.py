from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from .auth import Role, require_admin, resolve_role
from .event_outbox import (
    EventOutboxError,
    drain_event_outbox,
    outbox_status,
    queue_events_outbox_patch,
)
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
    MAX_ASSERTION_LIFETIME,
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


def _event(
    *,
    event: str,
    role: Role,
    payload: dict[str, Any],
    event_id: str | None = None,
) -> dict[str, Any]:
    return {
        "event": event,
        "actor": role.value,
        "payload": payload,
        "event_id": event_id,
    }


def _provenance_event(role: Role, payload: dict[str, Any]) -> dict[str, Any]:
    transition_id = str(payload.get("transition_id", ""))
    event_id = f"SARA-EVENT-{transition_id}" if transition_id else None
    return _event(
        event="prime_custody_provenance",
        role=role,
        payload=payload,
        event_id=event_id,
    )


def _rejection_payload(
    *,
    prime_id: str,
    reason: str,
    authorization_id: str | None = None,
) -> dict[str, Any]:
    return {
        "prime_id": prime_id,
        "authorization_id": authorization_id,
        "reason": reason,
        "claims_boundary": "Software authorization decision only; no physical qualification claim.",
    }


def _with_events(
    registry: dict[str, Any],
    *,
    base_patch: dict[str, Any] | None,
    events: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    event_patch, event_ids = queue_events_outbox_patch(registry, events)
    patch = dict(base_patch or {})
    patch.update(event_patch)
    return patch, event_ids


def _drain_delivery_status(durable_store: DurableStore) -> str:
    try:
        drain_event_outbox(durable_store, limit=64)
        status = outbox_status(durable_store.get_registry())
    except (OSError, RuntimeError, ValueError, EventOutboxError):
        return "PENDING_REPLAY"
    return "DELIVERED" if status["pending"] == 0 else "PENDING_REPLAY"


def _append_direct_degraded_audit(
    durable_store: DurableStore,
    role: Role,
    *,
    event: str,
    payload: dict[str, Any],
) -> bool:
    degraded_payload = dict(payload)
    degraded_payload["provenance_mode"] = "DEGRADED_DIRECT_AUDIT"
    degraded_payload["claims_boundary"] = (
        "Safety-tightening fallback only; registry and audit are not cross-file atomic."
    )
    try:
        durable_store.append_audit(
            AuditRecord.create(
                event=event,
                actor=role.value,
                payload=degraded_payload,
            )
        )
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _queue_rejection(
    durable_store: DurableStore,
    role: Role,
    *,
    prime_id: str,
    reason: str,
    authorization_id: str | None = None,
) -> str:
    rejection_payload = _rejection_payload(
        prime_id=prime_id,
        authorization_id=authorization_id,
        reason=reason,
    )

    def operation(registry: dict[str, Any]):
        patch, _ids = _with_events(
            registry,
            base_patch=None,
            events=[
                _event(
                    event="prime_sentinel_authorization_rejected",
                    role=role,
                    payload=rejection_payload,
                )
            ],
        )
        return patch, None

    try:
        durable_store.transact_registry(operation)
    except EventOutboxError:
        return (
            "DEGRADED_DIRECT_AUDIT"
            if _append_direct_degraded_audit(
                durable_store,
                role,
                event="prime_sentinel_authorization_rejected",
                payload=rejection_payload,
            )
            else "DEGRADED_UNDELIVERED"
        )
    return _drain_delivery_status(durable_store)


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
        patch, event_ids = _with_events(
            registry,
            base_patch=passport_registry_patch(registry, passport),
            events=[_provenance_event(role, payload)],
        )
        return patch, (passport, payload, event_ids)

    try:
        passport, payload, event_ids = durable_store.transact_registry(operation)
    except _PassportAlreadyExists as exc:
        raise HTTPException(status_code=409, detail="PRIME passport already exists") from exc
    except (ValueError, EventOutboxError) as exc:
        raise HTTPException(
            status_code=500,
            detail="PRIME passport registry/outbox validation failed",
        ) from exc

    delivery = _drain_delivery_status(durable_store)
    return {
        "passport": passport.model_dump(mode="json"),
        "provenance": payload,
        "provenance_event_ids": event_ids,
        "provenance_delivery": delivery,
    }


@router.post("/{prime_id}/mission-complete")
def complete_prime_mission(
    prime_id: str,
    body: PrimeMissionCompletionRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    durable_store = _store(request)

    def derive_transition(registry: dict[str, Any]):
        passport = _load_from_registry(registry, prime_id)
        prior_authorization_id = passport.custody.requalification_release_authorization_id
        updated, payload = complete_mission(passport, body)
        supersession_error: str | None = None
        events: list[dict[str, Any]] = []
        try:
            base_patch = _passport_with_superseded_authorization_patch(
                registry,
                prior_authorization_id=prior_authorization_id,
                updated_passport=updated,
                transition_id=payload["transition_id"],
                reason="MISSION_COMPLETED",
            )
        except PrimeSentinelAuthorizationError as exc:
            base_patch = passport_registry_patch(registry, updated)
            supersession_error = str(exc)
            payload["details"]["authorization_supersession"] = "FAILED_SAFE_QUARANTINE"
            events.append(
                _event(
                    event="prime_sentinel_authorization_rejected",
                    role=role,
                    payload=_rejection_payload(
                        prime_id=prime_id,
                        authorization_id=prior_authorization_id,
                        reason=(
                            "mission quarantine preserved; authorization supersession failed: "
                            f"{supersession_error}"
                        ),
                    ),
                )
            )
        else:
            if prior_authorization_id:
                payload["details"]["superseded_authorization_id"] = prior_authorization_id
        events.append(_provenance_event(role, payload))
        return updated, payload, prior_authorization_id, supersession_error, base_patch, events

    def normal_operation(registry: dict[str, Any]):
        updated, payload, prior_id, supersession_error, base_patch, events = derive_transition(registry)
        patch, event_ids = _with_events(
            registry,
            base_patch=base_patch,
            events=events,
        )
        return patch, (updated, payload, prior_id, supersession_error, event_ids)

    try:
        updated, payload, prior_id, supersession_error, event_ids = durable_store.transact_registry(
            normal_operation
        )
    except _PassportNotFound as exc:
        raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
    except EventOutboxError as outbox_exc:
        def safety_operation(registry: dict[str, Any]):
            updated, payload, prior_id, supersession_error, base_patch, _events = derive_transition(
                registry
            )
            payload["details"]["provenance_outbox"] = "BYPASSED_FAIL_SAFE_QUARANTINE"
            payload["details"]["provenance_outbox_error"] = str(outbox_exc)
            return base_patch, (updated, payload, prior_id, supersession_error)

        try:
            updated, payload, prior_id, supersession_error = durable_store.transact_registry(
                safety_operation
            )
        except _PassportNotFound as exc:
            raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=500,
                detail="PRIME fail-safe quarantine registry validation failed",
            ) from exc

        audit_ok = True
        if supersession_error:
            audit_ok = _append_direct_degraded_audit(
                durable_store,
                role,
                event="prime_sentinel_authorization_rejected",
                payload=_rejection_payload(
                    prime_id=prime_id,
                    authorization_id=prior_id,
                    reason=(
                        "mission quarantine preserved; authorization supersession failed: "
                        f"{supersession_error}"
                    ),
                ),
            ) and audit_ok
        audit_ok = _append_direct_degraded_audit(
            durable_store,
            role,
            event="prime_custody_provenance",
            payload=payload,
        ) and audit_ok
        return {
            "passport": updated.model_dump(mode="json"),
            "provenance": payload,
            "provenance_event_ids": [],
            "provenance_delivery": (
                "DEGRADED_DIRECT_AUDIT" if audit_ok else "DEGRADED_UNDELIVERED"
            ),
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="PRIME passport registry/outbox validation failed",
        ) from exc

    delivery = _drain_delivery_status(durable_store)
    return {
        "passport": updated.model_dump(mode="json"),
        "provenance": payload,
        "provenance_event_ids": event_ids,
        "provenance_delivery": delivery,
    }


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
        base_patch = _passport_with_superseded_authorization_patch(
            registry,
            prior_authorization_id=prior_authorization_id,
            updated_passport=updated,
            transition_id=payload["transition_id"],
            reason="REQUALIFICATION_EVIDENCE_CHANGED",
        )
        if prior_authorization_id:
            payload["details"]["superseded_authorization_id"] = prior_authorization_id
        patch, event_ids = _with_events(
            registry,
            base_patch=base_patch,
            events=[_provenance_event(role, payload)],
        )
        return patch, (updated, payload, event_ids)

    try:
        updated, payload, event_ids = durable_store.transact_registry(operation)
    except _PassportNotFound as exc:
        raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
    except PrimeSentinelAuthorizationError as exc:
        _queue_rejection(
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
    except (ValueError, EventOutboxError) as exc:
        raise HTTPException(
            status_code=500,
            detail="PRIME passport registry/outbox validation failed",
        ) from exc

    delivery = _drain_delivery_status(durable_store)
    return {
        "passport": updated.model_dump(mode="json"),
        "provenance": payload,
        "provenance_event_ids": event_ids,
        "provenance_delivery": delivery,
    }


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
        records = registry.get("PRIME_SENTINEL_AUTHORIZATIONS", {})
        if not isinstance(records, dict):
            raise _PassportRegistryInvalid("PRIME SENTINEL authorization registry validation failed")
        for record_id, entry in records.items():
            if (
                not isinstance(record_id, str)
                or not isinstance(entry, dict)
                or entry.get("status") not in {"VERIFIED", "CONSUMED", "SUPERSEDED"}
                or any(
                    not isinstance(entry.get(field), str) or not entry[field]
                    for field in (
                        "prime_id",
                        "target_environment",
                        "key_id",
                        "key_fingerprint_sha256",
                        "nonce",
                        "issued_at",
                        "expires_at",
                    )
                )
            ):
                raise _PassportRegistryInvalid("PRIME SENTINEL authorization registry validation failed")
            try:
                issued = datetime.fromisoformat(entry["issued_at"].replace("Z", "+00:00"))
                expires = datetime.fromisoformat(entry["expires_at"].replace("Z", "+00:00"))
            except ValueError as exc:
                raise _PassportRegistryInvalid(
                    "PRIME SENTINEL authorization registry validation failed"
                ) from exc
            if (
                issued.tzinfo is None
                or expires.tzinfo is None
                or issued >= expires
                or expires - issued > MAX_ASSERTION_LIFETIME
            ):
                raise _PassportRegistryInvalid("PRIME SENTINEL authorization registry validation failed")
        verified = verifier.verify(body)
        updated, payload = apply_verified_requalification_authorization(passport, verified)
        base_patch = verified_authorization_registry_patch(registry, verified)
        base_patch.update(passport_registry_patch(registry, updated))
        patch, event_ids = _with_events(
            registry,
            base_patch=base_patch,
            events=[_provenance_event(role, payload)],
        )
        return patch, (updated, payload, event_ids)

    try:
        updated, payload, event_ids = durable_store.transact_registry(operation)
    except _PassportNotFound as exc:
        raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
    except _PassportRegistryInvalid as exc:
        raise HTTPException(
            status_code=500,
            detail="PRIME passport registry validation failed",
        ) from exc
    except (PrimeSentinelAuthorizationError, ValueError, EventOutboxError) as exc:
        try:
            _queue_rejection(
                durable_store,
                role,
                prime_id=prime_id,
                authorization_id=body.authorization_id,
                reason=str(exc),
            )
        except (ValueError, EventOutboxError):
            pass
        raise HTTPException(status_code=403, detail="PRIME SENTINEL authorization rejected") from exc

    delivery = _drain_delivery_status(durable_store)
    return {
        "passport": updated.model_dump(mode="json"),
        "provenance": payload,
        "provenance_event_ids": event_ids,
        "provenance_delivery": delivery,
    }


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
                rejection = _event(
                    event="prime_sentinel_authorization_rejected",
                    role=role,
                    payload=_rejection_payload(
                        prime_id=prime_id,
                        authorization_id=authorization_id,
                        reason="PRIME SENTINEL public-key verification is not configured",
                    ),
                )
                patch, event_ids = _with_events(
                    registry,
                    base_patch=None,
                    events=[rejection],
                )
                return patch, (
                    "VERIFIER_NOT_CONFIGURED",
                    passport,
                    authorization_id,
                    None,
                    None,
                    None,
                    event_ids,
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
                reason = str(exc)
                rejection = _event(
                    event="prime_sentinel_authorization_rejected",
                    role=role,
                    payload=_rejection_payload(
                        prime_id=prime_id,
                        authorization_id=authorization_id,
                        reason=reason,
                    ),
                )
                patch, event_ids = _with_events(
                    registry,
                    base_patch=None,
                    events=[rejection],
                )
                return patch, (
                    "AUTHORIZATION_INVALID",
                    passport,
                    authorization_id,
                    reason,
                    None,
                    None,
                    event_ids,
                )

        updated, disposition, reasons, payload = activate_pack(passport, body)
        provenance = _provenance_event(role, payload)
        if disposition != PrimeActivationDisposition.ACTIVATION_ALLOWED:
            patch, event_ids = _with_events(
                registry,
                base_patch=None,
                events=[provenance],
            )
            return patch, (
                "DECISION_ONLY",
                updated,
                authorization_id,
                None,
                disposition,
                (reasons, payload),
                event_ids,
            )

        if authorization_id and not releasing_quarantine:
            updated = updated.model_copy(
                update={
                    "custody": updated.custody.model_copy(
                        update={
                            "requalification_release_authorization_id": None,
                            "requalification_release_target_environment": None,
                            "requalification_release_key_id": None,
                        }
                    )
                }
            )
            payload["details"]["authorization_id"] = None
            payload["details"]["authorization_key_id"] = None
            payload["details"]["legacy_release_authorization_cleared"] = True

        base_patch = passport_registry_patch(registry, updated)
        if releasing_quarantine and authorization_id:
            base_patch.update(
                consumed_authorization_registry_patch(
                    registry,
                    authorization_id=authorization_id,
                    transition_id=payload["transition_id"],
                )
            )
        patch, event_ids = _with_events(
            registry,
            base_patch=base_patch,
            events=[provenance],
        )
        return patch, (
            "ACTIVATED",
            updated,
            authorization_id,
            None,
            disposition,
            (reasons, payload),
            event_ids,
        )

    try:
        (
            state,
            passport,
            authorization_id,
            auth_error,
            disposition,
            decision,
            event_ids,
        ) = durable_store.transact_registry(operation)
    except _PassportNotFound as exc:
        raise HTTPException(status_code=404, detail="PRIME passport not found") from exc
    except PrimeSentinelAuthorizationError as exc:
        try:
            delivery = _queue_rejection(
                durable_store,
                role,
                prime_id=prime_id,
                reason=str(exc),
            )
        except (ValueError, EventOutboxError):
            delivery = "PENDING_REPLAY"
        return JSONResponse(
            {
                "detail": "PRIME SENTINEL authorization consumption failed",
                "provenance_delivery": delivery,
            },
            status_code=409,
        )
    except (ValueError, EventOutboxError) as exc:
        raise HTTPException(
            status_code=500,
            detail="PRIME passport registry/outbox validation failed",
        ) from exc

    delivery = _drain_delivery_status(durable_store)

    if state == "VERIFIER_NOT_CONFIGURED":
        return JSONResponse(
            {
                "detail": "PRIME SENTINEL authorization cannot be revalidated",
                "provenance_event_ids": event_ids,
                "provenance_delivery": delivery,
            },
            status_code=503,
        )

    if state == "AUTHORIZATION_INVALID":
        return JSONResponse(
            {
                "disposition": PrimeActivationDisposition.REQUALIFICATION_REQUIRED.value,
                "reasons": [auth_error or "authorization invalid"],
                "passport": passport.model_dump(mode="json"),
                "provenance_event_ids": event_ids,
                "provenance_delivery": delivery,
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
        "provenance_event_ids": event_ids,
        "provenance_delivery": delivery,
    }

    if disposition == PrimeActivationDisposition.ACTIVATION_ALLOWED:
        return JSONResponse(response, status_code=200)
    if disposition == PrimeActivationDisposition.REQUALIFICATION_REQUIRED:
        return JSONResponse(response, status_code=409)
    return JSONResponse(response, status_code=403)
