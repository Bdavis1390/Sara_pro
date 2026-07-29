from __future__ import annotations

import json
import os
import secrets
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import __version__
from .auth import Role, require_admin, resolve_role, validate_runtime_secrets
from .limits import MAX_REQUEST_BYTES
from .models import AuditRecord, RegistryPatch, RelayRequest, RelayResponse
from .storage import DurableStore


class RequestTooLarge(Exception):
    pass


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_length = headers.get(b"content-length")
        if raw_length is not None:
            try:
                content_length = int(raw_length)
            except ValueError:
                await JSONResponse(
                    {"detail": "Malformed Content-Length header"}, status_code=400
                )(scope, receive, send)
                return
            if content_length < 0:
                await JSONResponse(
                    {"detail": "Malformed Content-Length header"}, status_code=400
                )(scope, receive, send)
                return
            if content_length > self.max_bytes:
                await self._reject(scope, receive, send)
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestTooLarge:
            await self._reject(scope, receive, send)

    async def _reject(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        await JSONResponse(
            {"detail": f"Request body exceeds {self.max_bytes} bytes"},
            status_code=413,
        )(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.umask(0o077)
    validate_runtime_secrets()
    app.state.store = DurableStore()
    app.state.store.append_audit(
        AuditRecord.create(
            event="service_started",
            actor="system",
            payload={"version": __version__, "mode": os.getenv("SARA_MODE", "local")},
        )
    )
    yield
    app.state.store.append_audit(
        AuditRecord.create(event="service_stopped", actor="system", payload={})
    )


app = FastAPI(
    title="Worldshepherd SARA / SSPADAWANZZ Admin Interface",
    version=__version__,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(RequestSizeLimitMiddleware)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'unsafe-inline'"
    return response


def store(request: Request) -> DurableStore:
    return request.app.state.store


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "service": "Worldshepherd SARA / SSPADAWANZZ Admin Interface",
        "version": __version__,
        "mode": os.getenv("SARA_MODE", "local"),
        "endpoints": {
            "ui": "/ui",
            "liveness": "/livez",
            "readiness": "/readyz",
            "audit": "/v1/audit?limit=50",
            "registry": "/admin/registry",
            "relay": "/v1/relay",
            "selftest": "/admin/selftest",
        },
    }


@app.get("/livez")
def liveness() -> dict[str, object]:
    return {"ok": True, "status": "alive"}


@app.get("/readyz")
def readiness(request: Request) -> JSONResponse:
    ready, detail = store(request).check_storage()
    return JSONResponse(
        {"ok": ready, "status": "ready" if ready else "not_ready", "storage": detail},
        status_code=200 if ready else 503,
    )


@app.get("/ui", response_class=HTMLResponse)
def ui() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Worldshepherd SARA</title><style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:3rem auto;padding:0 1rem;background:#0b1020;color:#e8edf7}
.card{border:1px solid #34415f;border-radius:12px;padding:1rem;margin:1rem 0;background:#121a2e}
code{color:#9ad5ff} .ok{color:#96e6a1}
</style></head><body><h1>Worldshepherd SARA</h1>
<p class="ok">Local administration interface is online.</p>
<div class="card"><strong>Authority separation</strong><p>CRE1AWS approves high-impact releases. SSPADAWANZZ operates the local service.</p></div>
<div class="card"><strong>Operational endpoints</strong><p><code>/health</code>, <code>/v1/relay</code>, <code>/v1/audit</code>, <code>/admin/registry</code>, <code>/admin/selftest</code></p></div>
<div class="card"><strong>Security boundary</strong><p>Tokens are never stored in this page. Use Bearer authentication from an approved local client.</p></div>
</body></html>"""


@app.post("/v1/relay", response_model=RelayResponse)
def relay(
    body: RelayRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> RelayResponse:
    correlation_id = body.correlation_id or secrets.token_hex(12)
    result = RelayResponse(
        accepted=True,
        target=body.target,
        action=body.action,
        correlation_id=correlation_id,
        status="recorded_local_only",
    )
    store(request).append_audit(
        AuditRecord.create(
            event="relay_recorded",
            actor=role.value,
            payload={
                "target": body.target,
                "action": body.action,
                "correlation_id": correlation_id,
                "payload_keys": sorted(body.payload.keys()),
            },
        )
    )
    return result


@app.get("/v1/audit")
def audit(
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> dict[str, object]:
    require_admin(role)
    return {"records": store(request).read_audit(limit)}


@app.get("/admin/registry")
def registry_get(
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    return {"registry": store(request).get_registry()}


@app.patch("/admin/registry")
def registry_patch(
    body: RegistryPatch,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    try:
        updated = store(request).patch_registry(body.values)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store(request).append_audit(
        AuditRecord.create(
            event="registry_patched",
            actor=role.value,
            payload={"keys": sorted(body.values.keys())},
        )
    )
    return {"registry": updated}


@app.get("/admin/selftest")
def selftest(
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    durable_store = store(request)
    storage_ok, storage_detail = durable_store.check_storage()
    try:
        registry_ok = isinstance(durable_store.get_registry(), dict)
        registry_detail = "registry parsed as a JSON object"
    except (OSError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
        registry_ok = False
        registry_detail = f"registry read failed: {exc}"
    audit_probe = AuditRecord.create(
        event="selftest_audit_probe", actor=role.value, payload={}
    )
    try:
        durable_store.append_audit(audit_probe)
        audit_ok = True
        audit_detail = "application audit append and fsync completed"
    except (OSError, RuntimeError) as exc:
        audit_ok = False
        audit_detail = f"audit append failed: {exc}"
    checks: dict[str, dict[str, Any]] = {
        "persistent_storage": {"ok": storage_ok, "detail": storage_detail},
        "registry_read": {
            "ok": registry_ok,
            "detail": registry_detail,
        },
        "audit_append": {
            "ok": audit_ok,
            "detail": audit_detail,
        },
    }
    if audit_ok:
        durable_store.append_audit(
            AuditRecord.create(
                event="selftest_run",
                actor=role.value,
                payload={name: check["ok"] for name, check in checks.items()},
            )
        )
    return {"ok": all(check["ok"] for check in checks.values()), "checks": checks}
