"""Standalone read-only Worldshepherd electromagnetic-intelligence service."""

from fastapi import FastAPI

from .em_convergence_contract import router as convergence_router
from .em_d5 import router as d5_router
from .em_intelligence import EM_SCHEMA_VERSION, router
from .em_latent import router as latent_router
from .em_maturity import router as maturity_router
from .em_recovery import router as recovery_router


app = FastAPI(
    title="Worldshepherd EM Intelligence Read-Only Service",
    version=EM_SCHEMA_VERSION,
    docs_url=None,
    redoc_url=None,
)
app.include_router(router)
app.include_router(d5_router)
app.include_router(latent_router)
app.include_router(maturity_router)
app.include_router(recovery_router)
app.include_router(convergence_router)


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
            "d5_status": "/v1/em/uc06/d5/status",
            "d5_contract": "/v1/em/uc06/d5/contract",
            "latent_contract": "/v1/em/uc06/latent/contract",
            "maturity": "/v1/em/uc06/maturity",
            "recovery_status": "/v1/em/uc06/recovery/status",
            "recovery_contract": "/v1/em/uc06/recovery/contract",
            "convergence_contract": "/v1/em/uc06/convergence/contract",
        },
    }
