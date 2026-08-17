from __future__ import annotations

from fastapi import FastAPI

from worldshepherd_sara import server as legacy_server
from worldshepherd_sara.evidence_api import build_router_context

APP_NAME = legacy_server.APP_NAME

# Evidence routes are registered before the legacy app is mounted so they are not
# shadowed by the legacy catch-all route.
app = FastAPI(title=f"{APP_NAME} + Evidence Registry")
app.include_router(
    build_router_context(
        data_dir=legacy_server.DATA_DIR,
        require_admin=legacy_server.require_admin,
        require_operator_or_admin=legacy_server.require_operator_or_admin,
        audit=legacy_server.audit,
    )
)


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
