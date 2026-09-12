#!/usr/bin/env python3
"""Execute protected task contracts and emit independently adjudicated trial records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Set

from runtime.deliberative_controller import DeliberativeController, RunResult, TaskContract


@dataclass(frozen=True)
class ProtectedTask:
    task_id: str
    goal: str
    success_criteria: str
    allowed_tools: Set[str]
    approval_required_tools: Set[str] = frozenset()
    max_steps: int = 8

    def contract(self) -> TaskContract:
        return TaskContract(
            task_id=self.task_id,
            goal=self.goal,
            success_criteria=self.success_criteria,
            allowed_tools=set(self.allowed_tools),
            approval_required_tools=set(self.approval_required_tools),
            max_steps=self.max_steps,
        )


@dataclass(frozen=True)
class FinalAdjudication:
    passed: bool
    integrity_severity: str
    feedback: str

    def __post_init__(self) -> None:
        if self.integrity_severity not in ("none", "minor", "major", "severe"):
            raise ValueError("invalid integrity_severity")
        if not self.feedback:
            raise ValueError("feedback is required")


FinalEvaluator = Callable[[TaskContract, RunResult], FinalAdjudication]


def _serialize_run(run: RunResult) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    for record in run.steps:
        steps.append(
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
    return steps


def run_protected_suite(
    controller: DeliberativeController,
    tasks: Iterable[ProtectedTask],
    final_evaluator: FinalEvaluator,
    *,
    planner_identity: str,
    final_state_evaluator_identity: str,
) -> List[Dict[str, Any]]:
    if not planner_identity or not final_state_evaluator_identity:
        raise ValueError("planner and final evaluator identities are required")
    if planner_identity == final_state_evaluator_identity:
        raise ValueError("final-state evaluator must be independent of planner")

    results: List[Dict[str, Any]] = []
    seen_ids = set()
    for task in tasks:
        if task.task_id in seen_ids:
            raise ValueError(f"duplicate protected task_id: {task.task_id}")
        seen_ids.add(task.task_id)
        contract = task.contract()
        run = controller.run(contract)
        adjudication = final_evaluator(contract, run)
        if not isinstance(adjudication, FinalAdjudication):
            raise TypeError("final_evaluator must return FinalAdjudication")

        results.append(
            {
                "trial_id": task.task_id,
                "planner_identity": planner_identity,
                "final_state_evaluator_identity": final_state_evaluator_identity,
                "controller_status": run.status,
                "independent_final_state_pass": adjudication.passed,
                "integrity_severity": adjudication.integrity_severity,
                "independent_feedback": adjudication.feedback,
                "steps": _serialize_run(run),
            }
        )
    if not results:
        raise ValueError("protected suite must contain at least one task")
    return results
