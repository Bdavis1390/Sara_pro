#!/usr/bin/env python3
"""Provider-agnostic planner/verifier role adapters for the bounded controller.

This module intentionally separates the model used to propose actions from the
model or service used to verify them. A host application supplies a transport
callback, so credentials and provider-specific SDKs stay outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional

from runtime.deliberative_controller import Action, StepRecord, TaskContract, Verification


Transport = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class ModelIdentity:
    provider: str
    model: str
    revision: str = ""

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("provider and model are required")

    @property
    def key(self) -> str:
        revision = f"@{self.revision}" if self.revision else ""
        return f"{self.provider}:{self.model}{revision}"


def _trace_summary(trace: List[StepRecord]) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    for record in trace:
        summary.append(
            {
                "step": record.step,
                "tool": record.action.tool,
                "arguments": record.action.arguments,
                "status": record.status,
                "tool_result": record.tool_result,
                "verification": (
                    None
                    if record.verification is None
                    else {
                        "success": record.verification.success,
                        "recoverable": record.verification.recoverable,
                        "feedback": record.verification.feedback,
                    }
                ),
            }
        )
    return summary


class JSONModelPlanner:
    """Convert structured model output into a controller Action."""

    def __init__(self, identity: ModelIdentity, transport: Transport) -> None:
        self.identity = identity
        self.transport = transport

    def __call__(self, contract: TaskContract, trace: List[StepRecord]) -> Action:
        payload = {
            "role": "planner",
            "model_identity": self.identity.key,
            "task": {
                "task_id": contract.task_id,
                "goal": contract.goal,
                "success_criteria": contract.success_criteria,
                "allowed_tools": sorted(contract.allowed_tools),
                "approval_required_tools": sorted(contract.approval_required_tools),
                "remaining_step_budget": max(0, contract.max_steps - len(trace)),
            },
            "trace": _trace_summary(trace),
            "response_contract": {
                "tool": "string",
                "arguments": "object",
                "rationale": "short action justification only; do not include private chain-of-thought",
            },
        }
        response = self.transport("planner", payload)
        if not isinstance(response, Mapping):
            raise TypeError("planner transport must return an object")
        tool = response.get("tool")
        arguments = response.get("arguments")
        rationale = response.get("rationale", "")
        if not isinstance(tool, str) or not tool:
            raise ValueError("planner response requires non-empty tool")
        if not isinstance(arguments, dict):
            raise ValueError("planner response arguments must be an object")
        if not isinstance(rationale, str):
            raise ValueError("planner response rationale must be a string")
        return Action(tool=tool, arguments=dict(arguments), rationale=rationale)


class JSONModelVerifier:
    """Convert an independent structured verifier response into Verification."""

    def __init__(
        self,
        identity: ModelIdentity,
        transport: Transport,
        *,
        planner_identity: Optional[ModelIdentity] = None,
        require_distinct_identity: bool = True,
    ) -> None:
        self.identity = identity
        self.transport = transport
        if require_distinct_identity and planner_identity is not None:
            if planner_identity.key == identity.key:
                raise ValueError("verifier identity must differ from planner identity")

    def __call__(
        self,
        contract: TaskContract,
        action: Action,
        result: Any,
        trace: List[StepRecord],
    ) -> Verification:
        payload = {
            "role": "verifier",
            "model_identity": self.identity.key,
            "task": {
                "task_id": contract.task_id,
                "goal": contract.goal,
                "success_criteria": contract.success_criteria,
            },
            "action": {
                "tool": action.tool,
                "arguments": action.arguments,
            },
            "tool_result": result,
            "prior_trace": _trace_summary(trace),
            "response_contract": {
                "success": "boolean",
                "recoverable": "boolean",
                "feedback": "concise evidence-based explanation",
            },
        }
        response = self.transport("verifier", payload)
        if not isinstance(response, Mapping):
            raise TypeError("verifier transport must return an object")
        success = response.get("success")
        recoverable = response.get("recoverable")
        feedback = response.get("feedback")
        if not isinstance(success, bool) or not isinstance(recoverable, bool):
            raise ValueError("verifier response requires boolean success and recoverable")
        if not isinstance(feedback, str) or not feedback:
            raise ValueError("verifier response requires non-empty feedback")
        if success and recoverable:
            # A successful result is terminal; marking it recoverable is ambiguous.
            recoverable = False
        return Verification(success=success, recoverable=recoverable, feedback=feedback)
