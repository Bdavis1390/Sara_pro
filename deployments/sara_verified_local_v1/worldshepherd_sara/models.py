from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RelayRequest(BaseModel):
    target: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None, max_length=128)


class RelayResponse(BaseModel):
    accepted: bool
    target: str
    action: str
    correlation_id: str
    status: str


class RegistryPatch(BaseModel):
    values: dict[str, Any]


class AuditRecord(BaseModel):
    timestamp: str
    event: str
    actor: str
    payload: dict[str, Any]

    @classmethod
    def create(cls, *, event: str, actor: str, payload: dict[str, Any]) -> "AuditRecord":
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            actor=actor,
            payload=payload,
        )
