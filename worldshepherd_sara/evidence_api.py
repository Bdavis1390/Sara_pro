from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from worldshepherd_sara.evidence_contract import EvidenceValidationError
from worldshepherd_sara.evidence_registry import (
    DuplicateEvidenceId,
    EvidenceDigestMismatch,
    EvidenceNotFound,
    EvidenceRegistry,
    EvidenceRegistryError,
    EvidenceSupersessionError,
)

router = APIRouter(prefix="/v1/evidence", tags=["evidence"])


def build_router_context(*, data_dir: Path, require_admin, require_operator_or_admin, audit):
    """Return a configured evidence router bound to SARA auth/audit primitives."""

    registry = EvidenceRegistry(data_dir)
    configured = APIRouter(prefix="/v1/evidence", tags=["evidence"])

    def _translate_error(exc: Exception) -> HTTPException:
        if isinstance(exc, DuplicateEvidenceId):
            return HTTPException(status_code=409, detail=str(exc))
        if isinstance(exc, EvidenceNotFound):
            return HTTPException(status_code=404, detail=str(exc))
        if isinstance(exc, (EvidenceValidationError, EvidenceSupersessionError, EvidenceDigestMismatch)):
            return HTTPException(status_code=400, detail=str(exc))
        if isinstance(exc, EvidenceRegistryError):
            return HTTPException(status_code=500, detail=str(exc))
        return HTTPException(status_code=500, detail="evidence registry failure")

    async def _create(kind: str, request: Request, authorization: str | None):
        actor = require_operator_or_admin(authorization)
        payload = await request.json()
        if not isinstance(payload, dict):
            audit("evidence_rejected", actor, {"kind": kind, "reason": "payload_not_object"})
            raise HTTPException(status_code=400, detail="evidence payload must be a JSON object")

        supersedes = payload.pop("supersedes_record_id", None)
        try:
            envelope = registry.append(
                kind,  # type: ignore[arg-type]
                payload,
                actor=actor,
                supersedes_record_id=supersedes,
            )
        except Exception as exc:
            audit(
                "evidence_rejected",
                actor,
                {"kind": kind, "record_id": payload.get(f"{kind}_id"), "reason": str(exc)},
            )
            raise _translate_error(exc) from exc

        audit(
            "evidence_created",
            actor,
            {
                "kind": kind,
                "record_id": envelope["record_id"],
                "supersedes_record_id": supersedes,
                "digest_verification": envelope["digest_verification"],
            },
        )
        return envelope

    @configured.post("/experiments")
    async def create_experiment(request: Request, authorization: str | None = Header(default=None)):
        return await _create("experiment", request, authorization)

    @configured.get("/experiments/{experiment_id}")
    def get_experiment(experiment_id: str, authorization: str | None = Header(default=None)):
        actor = require_admin(authorization)
        try:
            envelope = registry.get("experiment", experiment_id)
        except Exception as exc:
            audit("evidence_read_failed", actor, {"kind": "experiment", "record_id": experiment_id})
            raise _translate_error(exc) from exc
        audit("evidence_read", actor, {"kind": "experiment", "record_id": experiment_id})
        return envelope

    @configured.post("/claims")
    async def create_claim(request: Request, authorization: str | None = Header(default=None)):
        return await _create("claim", request, authorization)

    @configured.get("/claims/{claim_id}")
    def get_claim(claim_id: str, authorization: str | None = Header(default=None)):
        actor = require_admin(authorization)
        try:
            envelope = registry.get("claim", claim_id)
        except Exception as exc:
            audit("evidence_read_failed", actor, {"kind": "claim", "record_id": claim_id})
            raise _translate_error(exc) from exc
        audit("evidence_read", actor, {"kind": "claim", "record_id": claim_id})
        return envelope

    @configured.get("/export", response_class=PlainTextResponse)
    def export_evidence(authorization: str | None = Header(default=None)):
        actor = require_admin(authorization)
        text = registry.export_jsonl()
        audit("evidence_export", actor, {"bytes": len(text.encode("utf-8"))})
        return PlainTextResponse(text, media_type="application/jsonl")

    @configured.get("/metrics")
    def evidence_metrics(authorization: str | None = Header(default=None)):
        actor = require_admin(authorization)
        metrics = registry.metrics()
        audit("evidence_metrics_read", actor, metrics)
        return metrics

    return configured
