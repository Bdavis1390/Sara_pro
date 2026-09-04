from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from pydantic import BaseModel, Field

from .hmaa_interop import InteropRunResult, run_public_contract_replay
from .hmaa_lattice_contract import (
    LatticeReadTransport,
    validate_entity_stream_request,
    validate_task_stream_request,
)


class SandboxReadCapturePlan(BaseModel):
    entity_request: dict[str, Any] = Field(default_factory=dict)
    task_request: dict[str, Any] = Field(default_factory=dict)
    max_entity_messages: int = Field(default=4, ge=0, le=100)
    max_task_messages: int = Field(default=4, ge=0, le=100)


class SandboxReadCaptureResult(BaseModel):
    live_environment_validated: bool = False
    source_label: str = "authorized-sandbox-readonly-candidate"
    captured_entity_messages: int
    captured_task_messages: int
    interop: InteropRunResult


def _take_and_close(
    values: Iterable[Mapping[str, Any]],
    limit: int,
) -> list[Mapping[str, Any]]:
    if limit == 0:
        return []
    iterator: Iterator[Mapping[str, Any]] = iter(values)
    captured: list[Mapping[str, Any]] = []
    try:
        for _ in range(limit):
            try:
                captured.append(next(iterator))
            except StopIteration:
                break
    finally:
        close = getattr(iterator, "close", None)
        if callable(close):
            close()
    return captured


def capture_readonly_stream_evidence(
    *,
    transport: LatticeReadTransport,
    mission_id: str,
    plan: SandboxReadCapturePlan,
) -> SandboxReadCaptureResult:
    if plan.max_entity_messages == 0 and plan.max_task_messages == 0:
        raise ValueError("Sandbox read capture must request at least one stream message")

    entity_request = validate_entity_stream_request(plan.entity_request)
    task_request = validate_task_stream_request(plan.task_request)

    entity_messages = _take_and_close(
        transport.stream_entities(entity_request),
        plan.max_entity_messages,
    )
    task_messages = _take_and_close(
        transport.stream_tasks(task_request),
        plan.max_task_messages,
    )

    items: list[dict[str, Any]] = []
    items.extend(
        {"stream": "entities", "message": dict(message)}
        for message in entity_messages
    )
    items.extend(
        {"stream": "tasks", "message": dict(message)}
        for message in task_messages
    )
    if not items:
        raise ValueError("Sandbox read capture produced no stream messages")

    interop = run_public_contract_replay(
        mission_id=mission_id,
        items=items,
        source_label="authorized-sandbox-readonly-candidate",
    )
    return SandboxReadCaptureResult(
        live_environment_validated=False,
        captured_entity_messages=len(entity_messages),
        captured_task_messages=len(task_messages),
        interop=interop,
    )
