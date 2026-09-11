#!/usr/bin/env python3
"""Planner adapter that supplies independently verified prior experience as context."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping

from runtime.deliberative_controller import Action, StepRecord, TaskContract
from runtime.model_roles import ModelIdentity, Transport
from runtime.verified_experience import VerifiedExperienceStore


ProfileResolver = Callable[[TaskContract], Mapping[str, Any]]


class ExperienceAugmentedPlanner:
    def __init__(
        self,
        identity: ModelIdentity,
        transport: Transport,
        store: VerifiedExperienceStore,
        profile_resolver: ProfileResolver,
        *,
        context_limit: int = 5,
    ) -> None:
        if context_limit < 0:
            raise ValueError("context_limit must be non-negative")
        self.identity = identity
        self.transport = transport
        self.store = store
        self.profile_resolver = profile_resolver
        self.context_limit = context_limit

    @staticmethod
    def _trace(trace: List[StepRecord]) -> List[Dict[str, Any]]:
        result = []
        for record in trace:
            result.append(
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
        return result

    def __call__(self, contract: TaskContract, trace: List[StepRecord]) -> Action:
        profile = self.profile_resolver(contract)
        if not isinstance(profile, Mapping):
            raise TypeError("profile_resolver must return an object")
        family = profile.get("task_family")
        tags = profile.get("tags", [])
        if not isinstance(family, str) or not family:
            raise ValueError("task profile requires non-empty task_family")
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
            raise ValueError("task profile tags must be a list of non-empty strings")

        experience = self.store.planner_context(
            task_family=family,
            tags=tags,
            limit=self.context_limit,
        )
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
                "task_family": family,
                "tags": tags,
            },
            "trace": self._trace(trace),
            "verified_experience_context": experience,
            "response_contract": {
                "tool": "string",
                "arguments": "object",
                "rationale": "short action justification",
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
