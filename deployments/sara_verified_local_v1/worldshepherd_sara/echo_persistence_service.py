from __future__ import annotations

import hmac
import os
import stat
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .echo_event_store import (
    EchoEventConflict,
    EchoEventStore,
    EchoEventStoreError,
    EchoStoreFull,
)
from .limits import validate_json_resource
from .models import AuditRecord


ECHO_TOKEN_FILE_ENV = "ECHO_INGEST_TOKEN_FILE"
MAX_TOKEN_FILE_BYTES = 4 * 1024
MIN_TOKEN_CHARS = 32


class EchoServiceConfigError(RuntimeError):
    pass


class EchoAuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(min_length=1, max_length=128)
    event: str = Field(min_length=1, max_length=128)
    actor: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any]

    @field_validator("payload")
    @classmethod
    def payload_within_limits(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_json_resource(value)

    def audit_record(self) -> AuditRecord:
        return AuditRecord(
            timestamp=self.timestamp,
            event=self.event,
            actor=self.actor,
            payload=self.payload,
        )


class EchoIngestResponse(BaseModel):
    schema: str = "WS-ECHO-INGEST-RESPONSE-V1"
    outcome: str
    event_id: str
    semantic_sha256: str
    delivery_count: int


class EchoReconcileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[EchoAuditRecord] = Field(min_length=1, max_length=500)


def _read_owned_token_file(path_value: str) -> str:
    if not path_value:
        raise EchoServiceConfigError(f"{ECHO_TOKEN_FILE_ENV} is required")
    path = Path(path_value)
    if not path.is_absolute():
        raise EchoServiceConfigError(f"{ECHO_TOKEN_FILE_ENV} must be an absolute path")
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise EchoServiceConfigError("unable to inspect ECHO ingest-token file") from exc
    if stat.S_ISLNK(link_status.st_mode):
        raise EchoServiceConfigError("ECHO ingest-token file must not be a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise EchoServiceConfigError("unable to open ECHO ingest-token file securely") from exc
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise EchoServiceConfigError("ECHO ingest-token file must be a regular file")
        if (link_status.st_dev, link_status.st_ino) != (status.st_dev, status.st_ino):
            raise EchoServiceConfigError("ECHO ingest-token file changed during secure open")
        if status.st_uid != os.geteuid():
            raise EchoServiceConfigError("ECHO ingest-token file must be owned by the service UID")
        if stat.S_IMODE(status.st_mode) & 0o077:
            raise EchoServiceConfigError("ECHO ingest-token file must not grant group/other permissions")
        if status.st_size < 1 or status.st_size > MAX_TOKEN_FILE_BYTES:
            raise EchoServiceConfigError("ECHO ingest-token file size is invalid")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(MAX_TOKEN_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > MAX_TOKEN_FILE_BYTES:
        raise EchoServiceConfigError("ECHO ingest-token file is too large")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EchoServiceConfigError("ECHO ingest-token file must be UTF-8 text") from exc
    token = text.rstrip("\r\n")
    if not token or token != token.strip() or "\n" in token or "\r" in token:
        raise EchoServiceConfigError("ECHO ingest-token file must contain one token")
    if len(token) < MIN_TOKEN_CHARS:
        raise EchoServiceConfigError(
            f"ECHO ingest token must be at least {MIN_TOKEN_CHARS} characters"
        )
    for name in ("SARA_ADMIN_TOKEN", "SARA_RELAY_TOKEN", "PRIME_SENTINEL_SERVICE_TOKEN"):
        other = os.getenv(name, "")
        if other and hmac.compare_digest(token, other):
            raise EchoServiceConfigError(f"ECHO ingest token must be independent from {name}")
    return token


def _require_bearer(request: Request, expected: str) -> None:
    raw = request.headers.get("authorization", "")
    scheme, separator, supplied = raw.partition(" ")
    if not separator or scheme.lower() != "bearer" or not supplied:
        raise HTTPException(status_code=401, detail="ECHO bearer token required")
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="ECHO bearer token rejected")


def create_echo_app() -> FastAPI:
    token = _read_owned_token_file(os.getenv(ECHO_TOKEN_FILE_ENV, ""))
    try:
        store = EchoEventStore.from_environment()
    except EchoEventStoreError as exc:
        raise EchoServiceConfigError(str(exc)) from exc

    app = FastAPI(
        title="Worldshepherd ECHO SENTINEL LINK Persistence Service",
        version="1.6",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.echo_token = token
    app.state.echo_store = store

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        return response

    @app.get("/livez")
    def livez() -> dict[str, object]:
        return {"ok": True, "service": "ECHO_SENTINEL_LINK", "version": "1.6"}

    @app.get("/readyz")
    def readyz() -> dict[str, object]:
        try:
            status = store.health()
        except EchoEventStoreError as exc:
            raise HTTPException(status_code=503, detail="ECHO persistence unavailable") from exc
        if not status["ok"]:
            raise HTTPException(status_code=503, detail="ECHO persistence integrity check failed")
        return {
            "ok": True,
            "service": "ECHO_SENTINEL_LINK",
            "persistence": "HEALTHY",
            "deduplication": "STABLE_EVENT_ID_PLUS_SEMANTIC_HASH",
        }

    @app.get("/v1/status")
    def status(request: Request) -> dict[str, object]:
        _require_bearer(request, token)
        try:
            value = store.health()
        except EchoEventStoreError as exc:
            raise HTTPException(status_code=503, detail="ECHO persistence unavailable") from exc
        return {
            "schema": "WS-ECHO-PERSISTENCE-STATUS-V1",
            **value,
            "delivery_semantics": "AT_LEAST_ONCE_INPUT_IDEMPOTENT_SEMANTIC_STORAGE",
            "claims_boundary": (
                "Reference software persistence/deduplication only; exactly-once transport, "
                "immutable/WORM storage, and independent third-party attestation are not claimed."
            ),
        }

    @app.post("/v1/ingest", response_model=EchoIngestResponse)
    def ingest(body: EchoAuditRecord, request: Request) -> EchoIngestResponse:
        _require_bearer(request, token)
        try:
            result = store.ingest(body.audit_record())
        except EchoEventConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except EchoStoreFull as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except EchoEventStoreError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return EchoIngestResponse(
            outcome=result.outcome,
            event_id=result.record.event_id,
            semantic_sha256=result.record.semantic_sha256,
            delivery_count=result.record.delivery_count,
        )

    @app.get("/v1/event/{event_id}")
    def event(event_id: str, request: Request) -> dict[str, object]:
        _require_bearer(request, token)
        try:
            record = store.get(event_id)
        except EchoEventStoreError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if record is None:
            raise HTTPException(status_code=404, detail="ECHO event not found")
        return {
            "schema": "WS-ECHO-STORED-EVENT-V1",
            "event_id": record.event_id,
            "semantic_sha256": record.semantic_sha256,
            "event": record.event,
            "actor": record.actor,
            "payload": record.payload(),
            "first_audit_timestamp": record.first_audit_timestamp,
            "last_audit_timestamp": record.last_audit_timestamp,
            "first_ingested_at": record.first_ingested_at,
            "last_seen_at": record.last_seen_at,
            "delivery_count": record.delivery_count,
        }

    @app.post("/v1/reconcile")
    def reconcile(body: EchoReconcileRequest, request: Request) -> dict[str, object]:
        _require_bearer(request, token)
        try:
            return store.reconcile([item.audit_record() for item in body.records])
        except EchoEventConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except EchoEventStoreError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app
