from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.ai_execution_envelope import build_ai_execution_envelope
from worldshepherd_sara.ai_provider_protocol import ProviderAdapterError
from worldshepherd_sara.openai_responses_adapter import (
    OpenAIResponsesReadOnlyAdapter,
    build_function_call_output,
)
from worldshepherd_sara.prime_action_authorization import VerifiedPrimeActionAuthorization


def _envelope(*, payload=None, tools=None, side_effect_class="READ_ONLY", reversible=True):
    return build_ai_execution_envelope(
        action_id="ACTION-OAI-001",
        provider="OPENAI",
        provider_operation="RESPONSES_CREATE",
        model="gpt-test",
        tools=tools if tools is not None else ["read_system_status"],
        resource_scope=["system:status"],
        requested_authority=1,
        reversible=reversible,
        side_effect_class=side_effect_class,
        request_payload=payload or {"input": "Read the bounded system status."},
        policy_id="POLICY-READONLY-001",
        policy_sha256="sha256:" + "2" * 64,
        execution_id="AI-EXEC-OAI-001",
        created_at=datetime.now(timezone.utc),
    )


def _authorization(envelope):
    now = datetime.now(timezone.utc)
    return VerifiedPrimeActionAuthorization(
        authorization_id="ACT-AUTH-OAI-001",
        action_id=envelope.action_id,
        prime_id="PRIME-001",
        provider=envelope.provider,
        provider_operation=envelope.provider_operation,
        model_allowlist=[envelope.model],
        tool_allowlist=list(envelope.tools),
        resource_scope=list(envelope.resource_scope),
        requested_authority=envelope.requested_authority,
        reversible=envelope.reversible,
        side_effect_class=envelope.side_effect_class,
        policy_id=envelope.policy_id,
        policy_sha256=envelope.policy_sha256,
        policy_disposition="AUTO_ELIGIBLE",
        request_sha256=envelope.request_sha256,
        human_approval_required=False,
        human_decision_id=None,
        human_decision_sha256=None,
        key_id="PS-ACT-K1",
        key_fingerprint_sha256="f" * 64,
        nonce="nonce-openai-readonly-0001",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )


def test_build_request_compiles_only_governed_read_only_fields():
    envelope = _envelope(
        payload={
            "input": "Read the bounded system status.",
            "instructions": "Use only the provided read-only tool.",
            "max_output_tokens": 256,
        }
    )
    request = OpenAIResponsesReadOnlyAdapter().build_request(
        envelope, _authorization(envelope)
    )
    assert request["model"] == "gpt-test"
    assert request["parallel_tool_calls"] is False
    assert request["tools"][0]["name"] == "read_system_status"
    assert request["tools"][0]["strict"] is True
    assert request["tools"][0]["parameters"]["additionalProperties"] is False
    assert request["tool_choice"] == {
        "type": "allowed_tools",
        "mode": "auto",
        "tools": [{"type": "function", "name": "read_system_status"}],
    }


def test_hidden_provider_tool_configuration_is_rejected():
    envelope = _envelope(
        payload={
            "input": "status",
            "tools": [{"type": "function", "name": "send_email"}],
        }
    )
    with pytest.raises(ProviderAdapterError, match="unsupported or invalid"):
        OpenAIResponsesReadOnlyAdapter().build_request(
            envelope, _authorization(envelope)
        )


def test_adapter_refuses_unauthorized_model_and_non_read_only_scope():
    envelope = _envelope()
    auth = _authorization(envelope).model_copy(update={"model_allowlist": ["other-model"]})
    with pytest.raises(ProviderAdapterError, match="model"):
        OpenAIResponsesReadOnlyAdapter().build_request(envelope, auth)

    reversible_action = _envelope(side_effect_class="REVERSIBLE", reversible=True)
    with pytest.raises(ProviderAdapterError, match="restricted to reversible READ_ONLY"):
        OpenAIResponsesReadOnlyAdapter().build_request(
            reversible_action, _authorization(reversible_action)
        )


def test_adapter_permits_exactly_one_proof_tool():
    envelope = _envelope(tools=[])
    with pytest.raises(ProviderAdapterError, match="exactly"):
        OpenAIResponsesReadOnlyAdapter().build_request(
            envelope, _authorization(envelope)
        )


def test_parse_one_valid_function_call_and_build_output():
    envelope = _envelope()
    response = {
        "id": "resp_001",
        "output": [
            {
                "type": "function_call",
                "call_id": "call_001",
                "name": "read_system_status",
                "arguments": "{}",
            }
        ],
    }
    calls = OpenAIResponsesReadOnlyAdapter().parse_function_calls(envelope, response)
    assert len(calls) == 1
    assert calls[0].arguments == {}
    assert calls[0].arguments_sha256.startswith("sha256:")
    assert build_function_call_output(calls[0], {"status": "ok"}) == {
        "type": "function_call_output",
        "call_id": "call_001",
        "output": '{"status":"ok"}',
    }


def test_parse_rejects_unknown_tool_arguments_and_multiple_calls():
    envelope = _envelope()
    adapter = OpenAIResponsesReadOnlyAdapter()

    with pytest.raises(ProviderAdapterError, match="outside"):
        adapter.parse_function_calls(
            envelope,
            {
                "id": "resp_002",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_002",
                        "name": "send_email",
                        "arguments": "{}",
                    }
                ],
            },
        )

    with pytest.raises(ProviderAdapterError, match="accepts no"):
        adapter.parse_function_calls(
            envelope,
            {
                "id": "resp_003",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_003",
                        "name": "read_system_status",
                        "arguments": '{"unexpected":true}',
                    }
                ],
            },
        )

    with pytest.raises(ProviderAdapterError, match="multiple"):
        adapter.parse_function_calls(
            envelope,
            {
                "id": "resp_004",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_a",
                        "name": "read_system_status",
                        "arguments": "{}",
                    },
                    {
                        "type": "function_call",
                        "call_id": "call_b",
                        "name": "read_system_status",
                        "arguments": "{}",
                    },
                ],
            },
        )


def test_parse_rejects_nonstandard_json_duplicate_keys_and_oversize_output():
    envelope = _envelope()
    adapter = OpenAIResponsesReadOnlyAdapter()

    for raw in ('{"x":NaN}', '{"x":1,"x":2}'):
        with pytest.raises(ProviderAdapterError, match="strict JSON"):
            adapter.parse_function_calls(
                envelope,
                {
                    "id": "resp_strict",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_strict",
                            "name": "read_system_status",
                            "arguments": raw,
                        }
                    ],
                },
            )

    valid = adapter.parse_function_calls(
        envelope,
        {
            "id": "resp_output",
            "output": [
                {
                    "type": "function_call",
                    "call_id": "call_output",
                    "name": "read_system_status",
                    "arguments": "{}",
                }
            ],
        },
    )[0]
    with pytest.raises(ProviderAdapterError, match="size limit"):
        build_function_call_output(valid, {"blob": "x" * (64 * 1024)})
