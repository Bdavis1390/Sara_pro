from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .ai_execution_envelope import AIExecutionEnvelope
from .human_execution_decision import HumanExecutionDecision
from .prime_action_authorization import VerifiedPrimeActionAuthorization


class ProviderAdapterError(ValueError):
    pass


class ProviderFunctionCall(BaseModel):
    """Normalized provider function-call proposal; execution has not occurred."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1, max_length=64)
    provider_response_id: str = Field(min_length=1, max_length=256)
    call_id: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any]
    arguments_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def canonical_arguments_sha256(arguments: dict[str, Any]) -> str:
    encoded = json.dumps(
        arguments,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class AIProviderAdapter(Protocol):
    provider: str
    provider_operation: str

    def build_request(
        self,
        envelope: AIExecutionEnvelope,
        authorization: VerifiedPrimeActionAuthorization,
        *,
        human_decision: HumanExecutionDecision | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]: ...

    def parse_function_calls(
        self,
        envelope: AIExecutionEnvelope,
        response: dict[str, Any],
    ) -> list[ProviderFunctionCall]: ...
