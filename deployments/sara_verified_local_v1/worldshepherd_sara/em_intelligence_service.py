"""Standalone read-only Worldshepherd electromagnetic-intelligence service."""

from fastapi import FastAPI

from .em_intelligence import EM_SCHEMA_VERSION, router


app = FastAPI(
    title="Worldshepherd EM Intelligence Read-Only Service",
    version=EM_SCHEMA_VERSION,
    docs_url=None,
    redoc_url=None,
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "service": "Worldshepherd EM Intelligence Read-Only Service",
        "schema_version": EM_SCHEMA_VERSION,
        "read_only": True,
        "hardware_actions": False,
        "endpoints": {
            "uc06_evidence": "/v1/em/uc06/evidence",
            "contract": "/v1/em/contract",
        },
    }
