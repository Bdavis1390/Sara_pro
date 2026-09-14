from __future__ import annotations

import math
import os
import time
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, model_validator

from .auth import Role, require_admin, resolve_role
from .models import AuditRecord
from .qualification import canonical_digest
from .sensor_fusion import Observation, fuse_observations, fusion_graph


MAX_SYNTHETIC_FUSION_OBSERVATIONS = 128
MAX_SYNTHETIC_ID_LENGTH = 128
SYNTHETIC_FUSION_SCOPE = "UNCLASSIFIED_SYNTHETIC_RESEARCH_ONLY"
SYNTHETIC_FUSION_CLAIMS_BOUNDARY = [
    "Synthetic 2-D point-observation fusion only.",
    "This endpoint is not an operational tracker, JPDA/MHT implementation, or validated ISR/sensor-fusion capability.",
    "Measured latency is application-host specific and does not establish network, multimodal, CUI/classified, edge-device, or mission performance.",
]
BENCHMARK_TIMING_HEADERS_ENV = "SARA_BENCHMARK_TIMING_HEADERS"

router = APIRouter(prefix="/v1/synthetic-fusion", tags=["synthetic-fusion"])


class SyntheticFusionRequest(BaseModel):
    scenario_id: str = Field(min_length=1, max_length=MAX_SYNTHETIC_ID_LENGTH)
    observations: list[Observation] = Field(
        min_length=1,
        max_length=MAX_SYNTHETIC_FUSION_OBSERVATIONS,
    )
    max_spatial_distance: float = Field(gt=0.0, le=1_000_000.0)
    max_time_delta_seconds: float = Field(gt=0.0, le=86_400.0)

    @model_validator(mode="after")
    def bounded_identifiers_unique_observations_and_finite_values(
        self,
    ) -> "SyntheticFusionRequest":
        if not math.isfinite(self.max_spatial_distance):
            raise ValueError("max_spatial_distance must be finite")
        if not math.isfinite(self.max_time_delta_seconds):
            raise ValueError("max_time_delta_seconds must be finite")

        observation_ids = [item.observation_id for item in self.observations]
        if len(set(observation_ids)) != len(observation_ids):
            raise ValueError("observation_id values must be unique within one request")
        for item in self.observations:
            if len(item.observation_id) > MAX_SYNTHETIC_ID_LENGTH:
                raise ValueError(
                    f"observation_id maximum length is {MAX_SYNTHETIC_ID_LENGTH}"
                )
            if len(item.sensor_id) > MAX_SYNTHETIC_ID_LENGTH:
                raise ValueError(f"sensor_id maximum length is {MAX_SYNTHETIC_ID_LENGTH}")
            for field_name in ("t_seconds", "x", "y", "confidence"):
                if not math.isfinite(float(getattr(item, field_name))):
                    raise ValueError(
                        f"observation {field_name} values must be finite"
                    )
        return self


class SyntheticFusionResponse(BaseModel):
    scenario_id: str
    scope: str
    claims_boundary: list[str]
    observation_count: int
    track_count: int
    request_digest: str
    result_digest: str
    elapsed_ms: float
    tracks: list[dict[str, Any]]
    evidence_graph: dict[str, Any]


def _durable_store(request: Request):
    return request.app.state.store


def _benchmark_timing_enabled() -> bool:
    return os.getenv(BENCHMARK_TIMING_HEADERS_ENV, "0") == "1"


@router.post("", response_model=SyntheticFusionResponse)
def synthetic_fusion(
    body: SyntheticFusionRequest,
    request: Request,
    response: Response,
    role: Annotated[Role, Depends(resolve_role)],
) -> SyntheticFusionResponse:
    """Run a bounded, authenticated, auditable synthetic fusion demonstration.

    The route intentionally remains admin-only and synthetic-only. A successful
    response means the result was also persisted to SARA's application audit.
    It is not an operational ISR or controlled-environment endpoint.
    """

    require_admin(role)
    request_digest_started = time.perf_counter_ns()
    request_digest = canonical_digest(body)
    request_digest_ms = (time.perf_counter_ns() - request_digest_started) / 1_000_000.0

    started = time.perf_counter_ns()
    tracks = fuse_observations(
        body.observations,
        max_spatial_distance=body.max_spatial_distance,
        max_time_delta_seconds=body.max_time_delta_seconds,
    )
    graph = fusion_graph(
        graph_id=f"synthetic-fusion:{body.scenario_id}",
        observations=body.observations,
        tracks=tracks,
    )
    track_payload = [asdict(track) for track in tracks]
    graph_payload = graph.model_dump(mode="json")
    result_digest = canonical_digest(
        {
            "scenario_id": body.scenario_id,
            "tracks": track_payload,
            "evidence_graph": graph_payload,
        }
    )
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0

    audit_payload = {
        "scenario_id": body.scenario_id,
        "scope": SYNTHETIC_FUSION_SCOPE,
        "observation_count": len(body.observations),
        "track_count": len(tracks),
        "request_digest": request_digest,
        "result_digest": result_digest,
        "elapsed_ms": round(elapsed_ms, 6),
    }
    audit_started = time.perf_counter_ns()
    try:
        _durable_store(request).append_audit(
            AuditRecord.create(
                event="synthetic_fusion_completed",
                actor=role.value,
                payload=audit_payload,
            )
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Synthetic fusion result withheld because audit persistence failed",
        ) from exc
    audit_elapsed_ms = (time.perf_counter_ns() - audit_started) / 1_000_000.0

    if _benchmark_timing_enabled():
        response.headers["Server-Timing"] = (
            f"request_digest;dur={request_digest_ms:.6f}, "
            f"fusion_graph;dur={elapsed_ms:.6f}, "
            f"audit_fsync;dur={audit_elapsed_ms:.6f}"
        )

    return SyntheticFusionResponse(
        scenario_id=body.scenario_id,
        scope=SYNTHETIC_FUSION_SCOPE,
        claims_boundary=list(SYNTHETIC_FUSION_CLAIMS_BOUNDARY),
        observation_count=len(body.observations),
        track_count=len(tracks),
        request_digest=request_digest,
        result_digest=result_digest,
        elapsed_ms=elapsed_ms,
        tracks=track_payload,
        evidence_graph=graph_payload,
    )
