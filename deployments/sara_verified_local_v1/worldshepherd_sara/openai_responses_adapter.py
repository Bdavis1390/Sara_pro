from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .ai_execution_envelope import AIExecutionEnvelope, assert_execution_authorized
from .ai_provider_protocol import (
    ProviderAdapterError,
    ProviderFunctionCall,
    canonical_arguments_sha256,
)
from .human_execution_decision import HumanExecutionDecision
from .prime_action_authorization import VerifiedPrimeActionAuthorization


OPENAI_PROVIDER = "OPENAI"
OPENAI_RESPONSES_CREATE = "RESPONSES_CREATE"
READ_SYSTEM_STATUS_TOOL = "read_system_status"
MAX_PROVIDER_OUTPUT_ITEMS = 128
MAX_FUNCTION_ARGUMENT_BYTES = 4 * 1024
MAX_FUNCTION_OUTPUT_BYTES = 64 * 1024


class OpenAIReadOnlyPayload(BaseModel):
    """The only provider-specific request fields admitted by the v1 proof adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input: str = Field(min_length=1, max_length=32_768)
    instructions: str | None = Field(default=None, min_length=1, max_length=8_192)
    max_output_tokens: int | None = Field(default=None, ge=1, le=4_096)


class ReadSystemStatusArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


_READ_SYSTEM_STATUS_DEFINITION: dict[str, Any] = {
    "type": "function",
    "name": READ_SYSTEM_STATUS_TOOL,
    "description": (
        "Read the bounded Worldshepherd system status snapshot. "
        "This function performs no mutation and accepts no arguments."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}


def _validate_proof_scope(envelope: AIExecutionEnvelope) -> None:
    if envelope.provider != OPENAI_PROVIDER:
        raise ProviderAdapterError("OpenAI adapter requires provider OPENAI")
    if envelope.provider_operation != OPENAI_RESPONSES_CREATE:
        raise ProviderAdapterError("OpenAI adapter only supports RESPONSES_CREATE")
    if envelope.side_effect_class != "READ_ONLY" or not envelope.reversible:
        raise ProviderAdapterError("v1 OpenAI adapter is restricted to reversible READ_ONLY execution")
    if envelope.tools != [READ_SYSTEM_STATUS_TOOL]:
        raise ProviderAdapterError(
            "v1 OpenAI adapter permits exactly the read_system_status tool"
        )
    if envelope.resource_scope != ["system:status"]:
        raise ProviderAdapterError(
            "v1 OpenAI adapter permits exactly the system:status resource scope"
        )


def _strict_json_object(raw: str) -> dict[str, Any]:
    if len(raw.encode("utf-8")) > MAX_FUNCTION_ARGUMENT_BYTES:
        raise ProviderAdapterError("OpenAI function arguments exceed the v1 size limit")

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-standard JSON constant: {value}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw,
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ProviderAdapterError("OpenAI function arguments are invalid strict JSON") from exc
    if not isinstance(value, dict):
        raise ProviderAdapterError("OpenAI function arguments must decode to an object")
    return value


def _validated_payload(envelope: AIExecutionEnvelope) -> OpenAIReadOnlyPayload:
    try:
        return OpenAIReadOnlyPayload.model_validate(envelope.request_payload)
    except ValidationError as exc:
        raise ProviderAdapterError(
            "OpenAI request payload contains unsupported or invalid fields"
        ) from exc


class OpenAIResponsesReadOnlyAdapter:
    """Fail-closed Responses API request compiler for the first read-only proof.

    This module deliberately performs no network I/O and does not load an API
    key. A later transport layer may submit the returned request only after the
    authorization has been recorded/claimed by the durable execution ledger.
    """

    provider = OPENAI_PROVIDER
    provider_operation = OPENAI_RESPONSES_CREATE

    def build_request(
        self,
        envelope: AIExecutionEnvelope,
        authorization: VerifiedPrimeActionAuthorization,
        *,
        human_decision: HumanExecutionDecision | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        try:
            assert_execution_authorized(
                envelope,
                authorization,
                human_decision=human_decision,
                now=now,
            )
        except ValueError as exc:
            raise ProviderAdapterError(str(exc)) from exc
        _validate_proof_scope(envelope)
        payload = _validated_payload(envelope)

        request: dict[str, Any] = {
            "model": envelope.model,
            "input": payload.input,
            "tools": [dict(_READ_SYSTEM_STATUS_DEFINITION)],
            "tool_choice": {
                "type": "allowed_tools",
                "mode": "auto",
                "tools": [{"type": "function", "name": READ_SYSTEM_STATUS_TOOL}],
            },
            "parallel_tool_calls": False,
        }
        if payload.instructions is not None:
            request["instructions"] = payload.instructions
        if payload.max_output_tokens is not None:
            request["max_output_tokens"] = payload.max_output_tokens
        return request

    def parse_function_calls(
        self,
        envelope: AIExecutionEnvelope,
        response: dict[str, Any],
    ) -> list[ProviderFunctionCall]:
        _validate_proof_scope(envelope)
        response_id = response.get("id")
        output = response.get("output")
        if not isinstance(response_id, str) or not response_id:
            raise ProviderAdapterError("OpenAI response is missing a response id")
        if not isinstance(output, list):
            raise ProviderAdapterError("OpenAI response output must be a list")
        if len(output) > MAX_PROVIDER_OUTPUT_ITEMS:
            raise ProviderAdapterError("OpenAI response output exceeds the v1 item limit")

        calls: list[ProviderFunctionCall] = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "function_call":
                continue
            name = item.get("name")
            call_id = item.get("call_id")
            raw_arguments = item.get("arguments")
            if name != READ_SYSTEM_STATUS_TOOL or name not in envelope.tools:
                raise ProviderAdapterError("OpenAI proposed a function outside the governed tool set")
            if not isinstance(call_id, str) or not call_id:
                raise ProviderAdapterError("OpenAI function call is missing call_id")
            if not isinstance(raw_arguments, str):
                raise ProviderAdapterError("OpenAI function arguments must be JSON text")
            arguments = _strict_json_object(raw_arguments)
            try:
                ReadSystemStatusArguments.model_validate(arguments)
            except ValidationError as exc:
                raise ProviderAdapterError(
                    "read_system_status accepts no function arguments"
                ) from exc
            calls.append(
                ProviderFunctionCall(
                    provider=OPENAI_PROVIDER,
                    provider_response_id=response_id,
                    call_id=call_id,
                    name=name,
                    arguments=arguments,
                    arguments_sha256=canonical_arguments_sha256(arguments),
                )
            )

        if len(calls) > 1:
            raise ProviderAdapterError("v1 OpenAI adapter rejects multiple function calls per turn")
        return calls


def build_function_call_output(
    call: ProviderFunctionCall,
    result: dict[str, Any],
) -> dict[str, str]:
    if call.provider != OPENAI_PROVIDER:
        raise ProviderAdapterError("function-call output provider mismatch")
    try:
        output = json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ProviderAdapterError("function-call output must be strict JSON") from exc
    if len(output.encode("utf-8")) > MAX_FUNCTION_OUTPUT_BYTES:
        raise ProviderAdapterError("function-call output exceeds the v1 size limit")
    return {
        "type": "function_call_output",
        "call_id": call.call_id,
        "output": output,
    }
