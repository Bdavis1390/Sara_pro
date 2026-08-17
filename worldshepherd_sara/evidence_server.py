from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from worldshepherd_sara import server as legacy_server
from worldshepherd_sara.evidence_contract import EvidenceValidationError
from worldshepherd_sara.evidence_registry import (
    DuplicateEvidenceId,
    EvidenceDigestMismatch,
    EvidenceNotFound,
    EvidenceReferenceError,
    EvidenceRegistry,
    EvidenceRegistryError,
    EvidenceSupersessionError,
)

APP_NAME = legacy_server.APP_NAME
registry = EvidenceRegistry(legacy_server.DATA_DIR)

# Evidence routes are registered directly before the legacy app is mounted. This
# avoids dependency on nested-router behavior and ensures the legacy catch-all
# cannot shadow /v1/evidence/*.
app = FastAPI(title=f"{APP_NAME} + Evidence Registry")


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, DuplicateEvidenceId):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, EvidenceNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(
        exc,
        (
            EvidenceValidationError,
            EvidenceReferenceError,
            EvidenceSupersessionError,
            EvidenceDigestMismatch,
        ),
    ):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, EvidenceRegistryError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail="evidence registry failure")


async def _create_record(kind: str, request: Request, authorization: str | None):
    actor = legacy_server.require_operator_or_admin(authorization)
    payload = await request.json()
    if not isinstance(payload, dict):
        legacy_server.audit("evidence_rejected", actor, {"kind": kind, "reason": "payload_not_object"})
        raise HTTPException(status_code=400, detail="evidence payload must be a JSON object")

    payload = dict(payload)
    supersedes = payload.pop("supersedes_record_id", None)
    try:
        envelope = registry.append(
            kind,  # type: ignore[arg-type]
            payload,
            actor=actor,
            supersedes_record_id=supersedes,
        )
    except Exception as exc:
        id_field = "experiment_id" if kind == "experiment" else "claim_id"
        legacy_server.audit(
            "evidence_rejected",
            actor,
            {"kind": kind, "record_id": payload.get(id_field), "reason": str(exc)},
        )
        raise _translate_error(exc) from exc

    legacy_server.audit(
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


@app.post("/v1/evidence/experiments")
async def create_experiment(request: Request, authorization: str | None = Header(default=None)):
    return await _create_record("experiment", request, authorization)


@app.get("/v1/evidence/experiments/{experiment_id}")
def get_experiment(experiment_id: str, authorization: str | None = Header(default=None)):
    actor = legacy_server.require_admin(authorization)
    try:
        envelope = registry.get("experiment", experiment_id)
    except Exception as exc:
        legacy_server.audit("evidence_read_failed", actor, {"kind": "experiment", "record_id": experiment_id})
        raise _translate_error(exc) from exc
    legacy_server.audit("evidence_read", actor, {"kind": "experiment", "record_id": experiment_id})
    return envelope


@app.post("/v1/evidence/claims")
async def create_claim(request: Request, authorization: str | None = Header(default=None)):
    return await _create_record("claim", request, authorization)


@app.get("/v1/evidence/claims/{claim_id}")
def get_claim(claim_id: str, authorization: str | None = Header(default=None)):
    actor = legacy_server.require_admin(authorization)
    try:
        envelope = registry.get("claim", claim_id)
    except Exception as exc:
        legacy_server.audit("evidence_read_failed", actor, {"kind": "claim", "record_id": claim_id})
        raise _translate_error(exc) from exc
    legacy_server.audit("evidence_read", actor, {"kind": "claim", "record_id": claim_id})
    return envelope


@app.get("/v1/evidence/export", response_class=PlainTextResponse)
def export_evidence(authorization: str | None = Header(default=None)):
    actor = legacy_server.require_admin(authorization)
    text = registry.export_jsonl()
    legacy_server.audit("evidence_export", actor, {"bytes": len(text.encode("utf-8"))})
    return PlainTextResponse(text, media_type="application/jsonl")


@app.get("/v1/evidence/metrics")
def evidence_metrics(authorization: str | None = Header(default=None)):
    actor = legacy_server.require_admin(authorization)
    metrics = registry.metrics()
    legacy_server.audit("evidence_metrics_read", actor, metrics)
    return metrics


@app.get("/v1/capabilities")
def capabilities():
    base = legacy_server.capabilities()
    result = dict(base)
    caps = dict(result.get("capabilities", {}))
    caps.update(
        {
            "evidence_experiment_create": {
                "path": "/v1/evidence/experiments",
                "method": "POST",
                "auth": "operator_or_admin",
            },
            "evidence_experiment_read": {
                "path": "/v1/evidence/experiments/{experiment_id}",
                "method": "GET",
                "auth": "admin",
            },
            "evidence_claim_create": {
                "path": "/v1/evidence/claims",
                "method": "POST",
                "auth": "operator_or_admin",
            },
            "evidence_claim_read": {
                "path": "/v1/evidence/claims/{claim_id}",
                "method": "GET",
                "auth": "admin",
            },
            "evidence_export": {
                "path": "/v1/evidence/export",
                "method": "GET",
                "auth": "admin",
            },
            "evidence_metrics": {
                "path": "/v1/evidence/metrics",
                "method": "GET",
                "auth": "admin",
            },
        }
    )
    result["capabilities"] = caps
    return result


app.mount("/", legacy_server.app)
