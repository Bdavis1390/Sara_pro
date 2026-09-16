from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .human_execution_decision import (
    HumanExecutionDecision,
    assert_human_approval_matches,
)
from .prime_action_authorization import VerifiedPrimeActionAuthorization


AI_EXECUTION_ENVELOPE_SCHEMA = "WS-AI-EXECUTION-ENVELOPE-V1"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class AIExecutionEnvelopeError(ValueError):
    pass


class AIExecutionEnvelope(BaseModel):
    """Provider-neutral immutable description of one proposed execution."""

    model_config = ConfigDict(extra="forbid")

    schema: Literal[AI_EXECUTION_ENVELOPE_SCHEMA] = AI_EXECUTION_ENVELOPE_SCHEMA
    execution_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1, max_length=128)
    provider: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9._:-]+$")
    provider_operation: str = Field(
        min_length=1, max_length=128, pattern=r"^[A-Z0-9._:-]+$"
    )
    model: str = Field(min_length=1, max_length=256)
    tools: list[str] = Field(default_factory=list, max_length=64)
    resource_scope: list[str] = Field(default_factory=list, max_length=64)
    requested_authority: int = Field(ge=0, le=1_000_000)
    reversible: bool
    side_effect_class: Literal[
        "READ_ONLY", "REVERSIBLE", "CONSEQUENTIAL", "IRREVERSIBLE"
    ]
    request_payload: dict[str, Any] = Field(default_factory=dict)
    policy_id: str = Field(min_length=1, max_length=128)
    policy_sha256: str = Field(pattern=_SHA256_PATTERN)
    request_sha256: str = Field(pattern=_SHA256_PATTERN)
    created_at: datetime

    @model_validator(mode="after")
    def validate_contract(self) -> "AIExecutionEnvelope":
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if len(set(self.tools)) != len(self.tools):
            raise ValueError("tools must not contain duplicates")
        if len(set(self.resource_scope)) != len(self.resource_scope):
            raise ValueError("resource_scope must not contain duplicates")
        if self.side_effect_class == "READ_ONLY" and not self.reversible:
            raise ValueError("READ_ONLY execution must be reversible")
        expected = execution_request_sha256(self)
        if self.request_sha256 != expected:
            raise ValueError("request_sha256 does not match canonical execution request")
        return self


def canonical_execution_request(envelope: AIExecutionEnvelope | dict[str, Any]) -> bytes:
    if isinstance(envelope, AIExecutionEnvelope):
        source = envelope.model_dump(mode="json")
    else:
        source = dict(envelope)
    payload = {
        "action_id": source["action_id"],
        "provider": source["provider"],
        "provider_operation": source["provider_operation"],
        "model": source["model"],
        "tools": source["tools"],
        "resource_scope": source["resource_scope"],
        "requested_authority": source["requested_authority"],
        "reversible": source["reversible"],
        "side_effect_class": source["side_effect_class"],
        "request_payload": source["request_payload"],
        "policy_id": source["policy_id"],
        "policy_sha256": source["policy_sha256"],
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def execution_request_sha256(envelope: AIExecutionEnvelope | dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_execution_request(envelope)).hexdigest()


def build_ai_execution_envelope(
    *,
    action_id: str,
    provider: str,
    provider_operation: str,
    model: str,
    tools: list[str],
    resource_scope: list[str],
    requested_authority: int,
    reversible: bool,
    side_effect_class: str,
    request_payload: dict[str, Any],
    policy_id: str,
    policy_sha256: str,
    execution_id: str | None = None,
    created_at: datetime | None = None,
) -> AIExecutionEnvelope:
    source = {
        "action_id": action_id,
        "provider": provider,
        "provider_operation": provider_operation,
        "model": model,
        "tools": list(tools),
        "resource_scope": list(resource_scope),
        "requested_authority": requested_authority,
        "reversible": reversible,
        "side_effect_class": side_effect_class,
        "request_payload": dict(request_payload),
        "policy_id": policy_id,
        "policy_sha256": policy_sha256,
    }
    digest = execution_request_sha256(source)
    return AIExecutionEnvelope(
        execution_id=execution_id or f"AI-EXEC-{uuid4()}",
        created_at=created_at or datetime.now(timezone.utc),
        request_sha256=digest,
        **source,
    )


def assert_execution_authorized(
    envelope: AIExecutionEnvelope,
    authorization: VerifiedPrimeActionAuthorization,
    *,
    human_decision: HumanExecutionDecision | None = None,
) -> None:
    if authorization.action_id != envelope.action_id:
        raise AIExecutionEnvelopeError("authorization action identity mismatch")
    if authorization.request_sha256 != envelope.request_sha256:
        raise AIExecutionEnvelopeError("authorization request digest mismatch")
    if authorization.provider != envelope.provider:
        raise AIExecutionEnvelopeError("authorization provider mismatch")
    if authorization.provider_operation != envelope.provider_operation:
        raise AIExecutionEnvelopeError("authorization provider operation mismatch")
    if envelope.model not in authorization.model_allowlist:
        raise AIExecutionEnvelopeError("model is outside authorization allowlist")
    if not set(envelope.tools).issubset(set(authorization.tool_allowlist)):
        raise AIExecutionEnvelopeError("tool is outside authorization allowlist")
    if not set(envelope.resource_scope).issubset(set(authorization.resource_scope)):
        raise AIExecutionEnvelopeError("resource is outside authorization scope")
    if envelope.requested_authority > authorization.requested_authority:
        raise AIExecutionEnvelopeError("requested authority exceeds authorization ceiling")
    if envelope.reversible != authorization.reversible:
        raise AIExecutionEnvelopeError("reversibility does not match authorization")
    if envelope.side_effect_class != authorization.side_effect_class:
        raise AIExecutionEnvelopeError("side-effect class does not match authorization")
    if envelope.policy_id != authorization.policy_id:
        raise AIExecutionEnvelopeError("policy identity mismatch")
    if envelope.policy_sha256 != authorization.policy_sha256:
        raise AIExecutionEnvelopeError("policy digest mismatch")

    if authorization.human_approval_required:
        if human_decision is None:
            raise AIExecutionEnvelopeError("human approval is required")
        try:
            assert_human_approval_matches(
                human_decision,
                action_id=envelope.action_id,
                action_digest_sha256=envelope.request_sha256,
            )
        except ValueError as exc:
            raise AIExecutionEnvelopeError(str(exc)) from exc
        if human_decision.decision_id != authorization.human_decision_id:
            raise AIExecutionEnvelopeError("human decision identity mismatch")
        if human_decision.decision_sha256 != authorization.human_decision_sha256:
            raise AIExecutionEnvelopeError("human decision digest mismatch")
    elif human_decision is not None:
        raise AIExecutionEnvelopeError(
            "human decision supplied for authorization that does not require it"
        )
