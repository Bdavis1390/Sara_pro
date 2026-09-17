from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import Role, require_admin, resolve_role
from .event_outbox import EventOutboxError, drain_event_outbox, outbox_status
from .poo_prime_authorized_commit import (
    PoOPrimeAuthorizedCommitError,
    PoOPrimeAuthorizedCommitRequest,
    prepare_prime_authorized_poo_commit_patch,
)
from .poo_prime_quorum_commit import (
    MAX_QUORUM_SIZE,
    PoOPrimeQuorumCommitError,
    PoOPrimeQuorumCommitRequest,
    prepare_prime_quorum_poo_commit_patch,
)
from .poo_registry_commit import (
    PoODurableCommitError,
    PoODurableCommitRequest,
    load_poo_registry_namespace,
    prepare_poo_durable_commit_patch,
)
from .prime_sentinel_poo_authorization import PrimeSentinelPoOVerifier
from .storage import DurableStore


router = APIRouter(prefix="/admin/poo", tags=["poo-governance"])
POO_REQUIRE_PRIME_AUTHORIZATION_ENV = "POO_REQUIRE_PRIME_AUTHORIZATION"
POO_PRIME_QUORUM_THRESHOLD_ENV = "POO_PRIME_QUORUM_THRESHOLD"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"", "0", "false", "no", "off"})


def poo_prime_authorization_required() -> bool:
    raw = os.getenv(POO_REQUIRE_PRIME_AUTHORIZATION_ENV, "").strip().lower()
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    raise RuntimeError(
        f"{POO_REQUIRE_PRIME_AUTHORIZATION_ENV} must be one of: "
        "0/1, false/true, no/yes, off/on"
    )


def poo_prime_quorum_threshold() -> int:
    raw = os.getenv(POO_PRIME_QUORUM_THRESHOLD_ENV, "").strip()
    if not raw:
        raise RuntimeError(f"{POO_PRIME_QUORUM_THRESHOLD_ENV} is not configured")
    try:
        threshold = int(raw, 10)
    except ValueError as exc:
        raise RuntimeError(f"{POO_PRIME_QUORUM_THRESHOLD_ENV} must be an integer") from exc
    if threshold < 2 or threshold > MAX_QUORUM_SIZE:
        raise RuntimeError(
            f"{POO_PRIME_QUORUM_THRESHOLD_ENV} must be between 2 and {MAX_QUORUM_SIZE}"
        )
    return threshold


def _store(request: Request) -> DurableStore:
    return request.app.state.store


def _drain_delivery_status(durable_store: DurableStore) -> str:
    try:
        drain_event_outbox(durable_store, limit=64)
        status = outbox_status(durable_store.get_registry())
    except (OSError, RuntimeError, ValueError, EventOutboxError):
        return "PENDING_REPLAY"
    return "DELIVERED" if status["pending"] == 0 else "PENDING_REPLAY"


def _prime_verifier() -> PrimeSentinelPoOVerifier:
    try:
        verifier = PrimeSentinelPoOVerifier.from_environment()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="PRIME SENTINEL PoO verifier configuration is invalid",
        ) from exc
    if not verifier.configured:
        raise HTTPException(
            status_code=503,
            detail="PRIME SENTINEL PoO public-key trust is not configured",
        )
    return verifier


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
    try:
        prime_required = poo_prime_authorization_required()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "registry": namespace.model_dump(mode="json"),
        "prime_authorization_required": prime_required,
        "claims_boundary": "INTERNAL_TECHNICAL_REGISTRY_ONLY",
    }


@router.post("/registry/commit")
def commit_poo_technical_registry(
    body: PoODurableCommitRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    try:
        if poo_prime_authorization_required():
            raise HTTPException(
                status_code=403,
                detail=(
                    "Unsigned PoO technical commits are disabled by policy; "
                    "use a PRIME-authorized PoO commit route"
                ),
            )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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


@router.post("/registry/commit-prime-authorized")
def commit_poo_technical_registry_prime_authorized(
    body: PoOPrimeAuthorizedCommitRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    try:
        prime_required = poo_prime_authorization_required()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    durable_store = _store(request)
    verifier = _prime_verifier()

    def operation(registry: dict[str, Any]):
        return prepare_prime_authorized_poo_commit_patch(
            registry,
            body,
            actor=role.value,
            verifier=verifier,
        )

    try:
        result = durable_store.transact_registry(operation)
    except EventOutboxError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "PRIME-authorized PoO commit blocked because durable audit custody "
                "is unavailable"
            ),
        ) from exc
    except (PoODurableCommitError, PoOPrimeAuthorizedCommitError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="PRIME-authorized PoO commit exceeds registry resource limits",
        ) from exc

    delivery = _drain_delivery_status(durable_store)
    return {
        "commit": result.model_dump(mode="json"),
        "audit_delivery": delivery,
        "prime_authorization_required": prime_required,
        "claims_boundary": (
            "PRIME_SIGNED_INTERNAL_TECHNICAL_STATE_COMMIT_NOT_LEGAL_TITLE_OR_"
            "LIVE_VALUE_AUTHORITY"
        ),
    }


@router.post("/registry/commit-prime-quorum-authorized")
def commit_poo_technical_registry_prime_quorum_authorized(
    body: PoOPrimeQuorumCommitRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, Any]:
    require_admin(role)
    try:
        threshold = poo_prime_quorum_threshold()
        prime_required = poo_prime_authorization_required()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    verifier = _prime_verifier()
    durable_store = _store(request)

    def operation(registry: dict[str, Any]):
        return prepare_prime_quorum_poo_commit_patch(
            registry,
            body,
            actor=role.value,
            verifier=verifier,
            threshold=threshold,
        )

    try:
        result = durable_store.transact_registry(operation)
    except EventOutboxError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "PRIME quorum PoO commit blocked because durable audit custody is unavailable"
            ),
        ) from exc
    except (PoODurableCommitError, PoOPrimeQuorumCommitError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="PRIME quorum PoO commit exceeds registry resource limits",
        ) from exc

    delivery = _drain_delivery_status(durable_store)
    return {
        "commit": result.model_dump(mode="json"),
        "audit_delivery": delivery,
        "prime_authorization_required": prime_required,
        "prime_quorum_threshold": threshold,
        "claims_boundary": (
            "PRIME_MULTI_KEY_QUORUM_INTERNAL_TECHNICAL_STATE_COMMIT_NOT_LEGAL_TITLE_OR_"
            "LIVE_VALUE_AUTHORITY"
        ),
    }
