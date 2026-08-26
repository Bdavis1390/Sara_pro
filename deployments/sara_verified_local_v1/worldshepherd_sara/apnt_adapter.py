from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class NormalizedPntSource(BaseModel):
    source_id: str = Field(min_length=1)
    source_kind: str = Field(min_length=1)
    health: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    observed_utc: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class PntSourceAdapter(Protocol):
    adapter_name: str

    def normalize(self, payload: dict[str, Any]) -> NormalizedPntSource:
        ...


class SyntheticPntAdapter:
    """Adapter for frozen synthetic fixtures only.

    It intentionally does not implement ASPN, pntOS, GPNTS, or any government
    interface. Those integrations remain separate validation work.
    """

    adapter_name = "synthetic_fixture_v1"

    def normalize(self, payload: dict[str, Any]) -> NormalizedPntSource:
        return NormalizedPntSource(
            source_id=str(payload["source_id"]),
            source_kind=str(payload["source_kind"]),
            health=str(payload["health"]),
            confidence=float(payload["confidence"]),
            observed_utc=payload.get("observed_utc"),
            attributes=dict(payload.get("attributes", {})),
        )


class AspnMappingStub:
    """Non-operational mapping contract for future ASPN/pntOS work.

    This class documents the normalized fields Worldshepherd expects from a
    future adapter but raises until an actual interface mapping is implemented
    and validated with authoritative schema/data.
    """

    adapter_name = "aspn_mapping_stub"

    required_normalized_fields = (
        "source_id",
        "source_kind",
        "health",
        "confidence",
        "observed_utc",
    )

    def normalize(self, payload: dict[str, Any]) -> NormalizedPntSource:
        raise NotImplementedError(
            "ASPN/pntOS mapping is not implemented or validated; use authoritative interface definitions before enabling"
        )
