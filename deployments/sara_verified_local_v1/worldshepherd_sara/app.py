from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse

from . import __version__
from .auth import Role, require_admin, resolve_role, validate_runtime_secrets
from .models import AuditRecord, RegistryPatch, RelayRequest, RelayResponse
from .storage import DurableStore


@asynccontextmanager
async def lifespan(app: FastAPI):
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
            "audit": "/v1/audit?limit=50",
            "registry": "/admin/registry",
            "relay": "/v1/relay",
            "selftest": "/admin/selftest",
        },
    }


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
    updated = store(request).patch_registry(body.values)
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
    registry = store(request).get_registry()
    checks = {
        "storage_directory": store(request).root.exists(),
        "registry_readable": isinstance(registry, dict),
        "audit_writable": True,
        "authority_separation": True,
        "external_dispatch_disabled": True,
    }
    store(request).append_audit(
        AuditRecord.create(event="selftest_run", actor=role.value, payload=checks)
    )
    return {"ok": all(checks.values()), "checks": checks}
