#!/usr/bin/env python3
"""Bounded propose -> execute -> verify -> repair controller.

The controller is model/provider agnostic. It accepts planner, tool, and verifier
callbacks supplied by the host application. Tool access is deny-by-default through
an explicit allowlist, and selected tools can require human approval before use.
Planner, tool, and verifier exceptions are preserved as structured run evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Set


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    goal: str
    success_criteria: str
    allowed_tools: Set[str]
    approval_required_tools: Set[str] = field(default_factory=set)
    max_steps: int = 8

    def __post_init__(self) -> None:
        if not self.task_id or not self.goal or not self.success_criteria:
            raise ValueError("task_id, goal, and success_criteria are required")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be positive")
        if not self.approval_required_tools.issubset(self.allowed_tools):
            raise ValueError("approval_required_tools must be a subset of allowed_tools")


@dataclass
class Action:
    tool: str
    arguments: Dict[str, Any]
    rationale: str = ""


@dataclass
class Verification:
    success: bool
    recoverable: bool
    feedback: str


@dataclass
class StepRecord:
    step: int
    action: Action
    tool_result: Any = None
    verification: Optional[Verification] = None
    status: str = "PENDING"


@dataclass
class RunResult:
    task_id: str
    status: str
    steps: List[StepRecord]
    final_result: Any = None
    final_feedback: str = ""


Planner = Callable[[TaskContract, List[StepRecord]], Action]
Verifier = Callable[[TaskContract, Action, Any, List[StepRecord]], Verification]
Tool = Callable[..., Any]
ApprovalCheck = Callable[[TaskContract, Action], bool]


def _error_payload(exc: Exception) -> Dict[str, str]:
    return {"error": type(exc).__name__, "message": str(exc)}


class DeliberativeController:
    """Execute a task under explicit tool, approval, verification, and step boundaries."""

    def __init__(
        self,
        tools: Mapping[str, Tool],
        planner: Planner,
        verifier: Verifier,
        approval_check: Optional[ApprovalCheck] = None,
    ) -> None:
        self.tools = dict(tools)
        self.planner = planner
        self.verifier = verifier
        self.approval_check = approval_check or (lambda contract, action: False)

    def run(self, contract: TaskContract) -> RunResult:
        trace: List[StepRecord] = []

        for step_number in range(1, contract.max_steps + 1):
            try:
                action = self.planner(contract, list(trace))
            except Exception as exc:
                record = StepRecord(
                    step=step_number,
                    action=Action(tool="__planner_error__", arguments={}),
                    tool_result=_error_payload(exc),
                    status="PLANNER_ERROR",
                )
                trace.append(record)
                return RunResult(
                    task_id=contract.task_id,
                    status="PLANNER_ERROR",
                    steps=trace,
                    final_result=record.tool_result,
                    final_feedback=f"planner failed: {type(exc).__name__}: {exc}",
                )
            if not isinstance(action, Action):
                record = StepRecord(
                    step=step_number,
                    action=Action(tool="__planner_contract_error__", arguments={}),
                    tool_result={"error": "TypeError", "message": "planner must return Action"},
                    status="PLANNER_ERROR",
                )
                trace.append(record)
                return RunResult(
                    task_id=contract.task_id,
                    status="PLANNER_ERROR",
                    steps=trace,
                    final_result=record.tool_result,
                    final_feedback="planner must return Action",
                )

            record = StepRecord(step=step_number, action=action)

            if action.tool not in contract.allowed_tools:
                record.status = "POLICY_BLOCKED"
                trace.append(record)
                return RunResult(
                    task_id=contract.task_id,
                    status="POLICY_BLOCKED",
                    steps=trace,
                    final_feedback=f"tool {action.tool!r} is not allowed by the task contract",
                )

            if action.tool not in self.tools:
                record.status = "TOOL_UNAVAILABLE"
                trace.append(record)
                return RunResult(
                    task_id=contract.task_id,
                    status="TOOL_UNAVAILABLE",
                    steps=trace,
                    final_feedback=f"tool {action.tool!r} is not registered",
                )

            if action.tool in contract.approval_required_tools:
                try:
                    approved = bool(self.approval_check(contract, action))
                except Exception as exc:
                    record.status = "APPROVAL_CHECK_ERROR"
                    record.tool_result = _error_payload(exc)
                    trace.append(record)
                    return RunResult(
                        task_id=contract.task_id,
                        status="APPROVAL_CHECK_ERROR",
                        steps=trace,
                        final_result=record.tool_result,
                        final_feedback=f"approval check failed: {type(exc).__name__}: {exc}",
                    )
                if not approved:
                    record.status = "APPROVAL_REQUIRED"
                    trace.append(record)
                    return RunResult(
                        task_id=contract.task_id,
                        status="APPROVAL_REQUIRED",
                        steps=trace,
                        final_feedback=f"human approval required for tool {action.tool!r}",
                    )

            try:
                result = self.tools[action.tool](**action.arguments)
            except Exception as exc:
                record.tool_result = _error_payload(exc)
                verification = Verification(
                    success=False,
                    recoverable=True,
                    feedback=f"tool execution failed: {type(exc).__name__}: {exc}",
                )
            else:
                record.tool_result = result
                try:
                    verification = self.verifier(contract, action, result, list(trace))
                except Exception as exc:
                    record.status = "VERIFIER_ERROR"
                    record.verification = Verification(
                        success=False,
                        recoverable=False,
                        feedback=f"verifier failed: {type(exc).__name__}: {exc}",
                    )
                    trace.append(record)
                    return RunResult(
                        task_id=contract.task_id,
                        status="VERIFIER_ERROR",
                        steps=trace,
                        final_result=record.tool_result,
                        final_feedback=record.verification.feedback,
                    )
                if not isinstance(verification, Verification):
                    record.status = "VERIFIER_ERROR"
                    record.verification = Verification(
                        success=False,
                        recoverable=False,
                        feedback="verifier must return Verification",
                    )
                    trace.append(record)
                    return RunResult(
                        task_id=contract.task_id,
                        status="VERIFIER_ERROR",
                        steps=trace,
                        final_result=record.tool_result,
                        final_feedback=record.verification.feedback,
                    )

            record.verification = verification
            record.status = "SUCCESS" if verification.success else "NEEDS_REPAIR"
            trace.append(record)

            if verification.success:
                return RunResult(
                    task_id=contract.task_id,
                    status="SUCCESS",
                    steps=trace,
                    final_result=record.tool_result,
                    final_feedback=verification.feedback,
                )

            if not verification.recoverable:
                record.status = "FAILED"
                return RunResult(
                    task_id=contract.task_id,
                    status="FAILED",
                    steps=trace,
                    final_result=record.tool_result,
                    final_feedback=verification.feedback,
                )

        return RunResult(
            task_id=contract.task_id,
            status="MAX_STEPS_EXCEEDED",
            steps=trace,
            final_result=trace[-1].tool_result if trace else None,
            final_feedback=(
                trace[-1].verification.feedback
                if trace and trace[-1].verification is not None
                else "step budget exhausted"
            ),
        )
