from __future__ import annotations

import pytest

from worldshepherd_sara.astra_solver import (
    DEFAULT_OPENAI_MODEL,
    AstraInferenceAuthorization,
    AstraRuntimeConfig,
    AstraSolver,
    AstraTask,
)
from worldshepherd_sara.qualification import CapabilityStatus


def test_astra_defaults_to_documented_model_and_network_off() -> None:
    config = AstraRuntimeConfig()
    assert config.model_id == DEFAULT_OPENAI_MODEL == "gpt-5.6-sol"
    assert config.network_enabled is False
    assert config.allowed_tools == []


def test_prepare_is_zero_network_and_provenance_bearing() -> None:
    solver = AstraSolver()
    task = AstraTask(
        task_id="WS-ASTRA-TEST-0001",
        prompt="Review this synthetic requirement for evidence gaps.",
        evidence_refs=["fixture://synthetic-requirement"],
        claims_control_labels=[CapabilityStatus.SIMULATED_ONLY],
    )

    prepared = solver.prepare(task)

    assert prepared.network_call_performed is False
    assert prepared.model_id == "gpt-5.6-sol"
    assert prepared.request_payload["store"] is False
    assert prepared.request_payload["metadata"]["worldshepherd_task_id"] == task.task_id
    assert prepared.input_digest.startswith("sha256:")


def test_unallowlisted_tool_fails_closed() -> None:
    solver = AstraSolver()
    task = AstraTask(
        task_id="WS-ASTRA-TEST-0002",
        prompt="Do not execute tools.",
        requested_tools=["web_search"],
    )

    with pytest.raises(PermissionError, match="outside the Astra profile allowlist"):
        solver.prepare(task)


def test_execute_fails_when_network_disabled() -> None:
    called = False

    def transport(_: dict) -> dict:
        nonlocal called
        called = True
        return {"id": "resp_fake", "output_text": "should not be reached"}

    solver = AstraSolver(transport=transport)
    task = AstraTask(task_id="WS-ASTRA-TEST-0003", prompt="Analyze only.")
    authorization = AstraInferenceAuthorization(
        authorization_id="AUTH-0003",
        authorized_by="CRE1AWS",
        allow_model_inference=True,
        allowed_model_ids=["gpt-5.6-sol"],
    )

    with pytest.raises(PermissionError, match="network inference is disabled"):
        solver.execute(task, authorization)
    assert called is False


def test_execute_requires_explicit_authorization() -> None:
    solver = AstraSolver(
        AstraRuntimeConfig(network_enabled=True),
        transport=lambda _: {"id": "resp_fake", "output_text": "ok"},
    )
    task = AstraTask(task_id="WS-ASTRA-TEST-0004", prompt="Analyze only.")

    with pytest.raises(PermissionError, match="explicit SARA model-inference authorization"):
        solver.execute(task, None)


def test_authorized_injected_transport_returns_digest_bearing_result() -> None:
    calls: list[dict] = []

    def transport(payload: dict) -> dict:
        calls.append(payload)
        return {
            "id": "resp_test_123",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "Evidence gap: physical coupon data absent."}
                    ],
                }
            ],
        }

    solver = AstraSolver(
        AstraRuntimeConfig(network_enabled=True),
        transport=transport,
    )
    task = AstraTask(
        task_id="WS-ASTRA-TEST-0005",
        prompt="Identify the strongest disconfirming evidence requirement.",
        evidence_refs=["fixture://meta-alloy-synthetic"],
        claims_control_labels=[CapabilityStatus.REQUIRES_LAB_VALIDATION],
    )
    authorization = AstraInferenceAuthorization(
        authorization_id="AUTH-0005",
        authorized_by="CRE1AWS",
        allow_model_inference=True,
        allowed_model_ids=["gpt-5.6-sol"],
    )

    result = solver.execute(task, authorization)

    assert len(calls) == 1
    assert calls[0]["model"] == "gpt-5.6-sol"
    assert calls[0]["store"] is False
    assert result.response_id == "resp_test_123"
    assert result.network_call_performed is True
    assert result.output_digest.startswith("sha256:")
    assert result.input_digest.startswith("sha256:")
    assert result.claims_control_labels == [CapabilityStatus.REQUIRES_LAB_VALIDATION]
