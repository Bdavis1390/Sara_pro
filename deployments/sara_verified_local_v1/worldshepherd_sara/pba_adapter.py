from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .pba_models import PBAObservation


class PBAAdapterEnvelope(BaseModel):
    """Normalized, read-only assurance snapshot supplied by a partner adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    adapter_id: str = Field(min_length=1, max_length=128)
    observed_at: datetime
    observation: PBAObservation

    @model_validator(mode="after")
    def validate_time(self) -> "PBAAdapterEnvelope":
        if self.observed_at.tzinfo is None:
            raise ValueError("adapter observation time must be timezone-aware")
        return self


@runtime_checkable
class PBAPartnerAdapter(Protocol):
    """G2 partner boundary.

    Implementations may read partner telemetry and normalize it into a
    ``PBAAdapterEnvelope``. This protocol intentionally exposes no method that
    can drive beam, pointing, targeting, or energy-delivery hardware.
    """

    adapter_id: str

    def snapshot(self) -> PBAAdapterEnvelope:
        ...
