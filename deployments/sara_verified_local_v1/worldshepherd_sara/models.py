from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .limits import validate_json_resource


OVERWATCH_PROTECTED_REGISTRY_PREFIX = "ws_overwatch_"


class RelayRequest(BaseModel):
    target: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None, max_length=128)

    @field_validator("payload")
    @classmethod
    def payload_within_limits(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_json_resource(value)


class RelayResponse(BaseModel):
    accepted: bool
    target: str
    action: str
    correlation_id: str
    status: str


class RegistryPatch(BaseModel):
    values: dict[str, Any]

    @field_validator("values")
    @classmethod
    def values_within_limits(cls, value: dict[str, Any]) -> dict[str, Any]:
        protected = sorted(
            key
            for key in value
            if isinstance(key, str)
            and key.startswith(OVERWATCH_PROTECTED_REGISTRY_PREFIX)
        )
        if protected:
            raise ValueError(
                "OVERWATCH protected registry namespaces cannot be mutated "
                "through the generic registry patch model"
            )
        return validate_json_resource(value)


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
