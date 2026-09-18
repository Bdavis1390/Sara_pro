from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from .models import AuditRecord
from .registry_monotonic_witness import (
    REMOTE_WITNESS_MODE,
    RegistryMonotonicWitnessClient,
    RegistryWitnessConflict,
    RegistryWitnessRollbackDetected,
    RegistryWitnessUnavailable,
)
from .registry_witness_runtime import (
    RegistryWitnessRuntimeConfigError,
    load_registry_witness_client_from_environment,
)
from .storage import DurableStore


REQUIRE_REGISTRY_WITNESS_ENV = "SARA_REQUIRE_REGISTRY_WITNESS"


class RegistryWitnessStartupError(RuntimeError):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def registry_witness_required(
    environ: dict[str, str] | None = None,
) -> bool:
    values = os.environ if environ is None else environ
    raw = str(values.get(REQUIRE_REGISTRY_WITNESS_ENV, "")).strip().lower()
    if raw in {"", "0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    raise RegistryWitnessStartupError(
        "WITNESS_REQUIREMENT_INVALID",
        f"{REQUIRE_REGISTRY_WITNESS_ENV} must be a boolean value",
    )


def _bounded_result(assessment: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "required": True,
        "generation": int(assessment["generation"]),
        "witness_id": str(assessment["witness_id"]),
        "witness_mode": str(assessment["witness_mode"]),
        "witness_receipt_sha256": str(
            assessment["witness_receipt_sha256"]
        ),
        "signature_verified": True,
        "monotonic_match": True,
    }


def _append_rejection(
    store: DurableStore,
    exc: RegistryWitnessStartupError,
) -> None:
    try:
        store.append_audit(
            AuditRecord.create(
                event="registry_witness_startup_rejected",
                actor="system",
                payload={
                    "status": "REJECTED",
                    "reason_code": exc.reason_code,
                },
            )
        )
    except (OSError, RuntimeError):
        # The security decision remains fail-closed even if rejection evidence
        # cannot be written.
        pass


def enforce_registry_witness_startup(
    store: DurableStore,
    *,
    environ: dict[str, str] | None = None,
    client_loader: Callable[[], RegistryMonotonicWitnessClient]
    | None = None,
) -> dict[str, Any]:
    """Require an exact remote monotonic witness when configured.

    This function never advances the witness. A locally newer checkpoint is a
    fail-closed pending condition that requires an explicit operator witness
    advance action before the next startup attempt.
    """
    try:
        required = registry_witness_required(environ)
    except RegistryWitnessStartupError as exc:
        _append_rejection(store, exc)
        raise

    if not required:
        return {
            "status": "DISABLED",
            "required": False,
            "generation": None,
            "witness_id": None,
            "witness_mode": None,
            "witness_receipt_sha256": None,
            "signature_verified": False,
            "monotonic_match": False,
        }

    loader = client_loader or load_registry_witness_client_from_environment
    try:
        client = loader()
    except RegistryWitnessRuntimeConfigError as exc:
        wrapped = RegistryWitnessStartupError(
            "WITNESS_CONFIGURATION_INVALID",
            "required registry witness configuration is invalid",
        )
        _append_rejection(store, wrapped)
        raise wrapped from exc

    local_status = store.checkpoint_status()
    try:
        assessment = client.check(local_status, require_head=True)
    except RegistryWitnessRollbackDetected as exc:
        wrapped = RegistryWitnessStartupError(
            "LOCAL_REGISTRY_ROLLBACK_DETECTED",
            "local registry is older than the signed witness head",
        )
        _append_rejection(store, wrapped)
        raise wrapped from exc
    except RegistryWitnessConflict as exc:
        wrapped = RegistryWitnessStartupError(
            "REGISTRY_WITNESS_CONFLICT",
            "local registry conflicts with the signed witness head",
        )
        _append_rejection(store, wrapped)
        raise wrapped from exc
    except RegistryWitnessUnavailable as exc:
        wrapped = RegistryWitnessStartupError(
            "REGISTRY_WITNESS_UNAVAILABLE",
            "required registry witness is unavailable",
        )
        _append_rejection(store, wrapped)
        raise wrapped from exc

    if assessment.get("status") != "PASS":
        wrapped = RegistryWitnessStartupError(
            "WITNESS_ADVANCE_REQUIRED",
            "current registry checkpoint is not yet covered by the witness",
        )
        _append_rejection(store, wrapped)
        raise wrapped

    if assessment.get("witness_mode") != REMOTE_WITNESS_MODE:
        wrapped = RegistryWitnessStartupError(
            "WITNESS_MODE_INVALID",
            "required startup witness is not in REMOTE_WITNESS mode",
        )
        _append_rejection(store, wrapped)
        raise wrapped

    if assessment.get("signature_verified") is not True:
        wrapped = RegistryWitnessStartupError(
            "WITNESS_SIGNATURE_UNVERIFIED",
            "required startup witness signature is not verified",
        )
        _append_rejection(store, wrapped)
        raise wrapped

    if assessment.get("monotonic_match") is not True:
        wrapped = RegistryWitnessStartupError(
            "WITNESS_MONOTONIC_MISMATCH",
            "required startup witness is not an exact monotonic match",
        )
        _append_rejection(store, wrapped)
        raise wrapped

    result = _bounded_result(assessment)
    store.append_audit(
        AuditRecord.create(
            event="registry_witness_startup_verified",
            actor="system",
            payload=result,
        )
    )
    return result
