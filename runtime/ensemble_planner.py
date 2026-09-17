#!/usr/bin/env python3
"""Bounded multi-planner ensemble with an independent action selector.

Multiple distinct planners propose one action each. A selector with a distinct
identity chooses among admitted proposals or abstains. Low-confidence or malformed
selection fails closed and is handled by the deliberative controller as a planner
error. The ensemble never expands tool permissions or step budgets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, Sequence, Tuple

from runtime.deliberative_controller import Action, Planner, StepRecord, TaskContract


@dataclass(frozen=True)
class Proposal:
    planner_identity: str
    action: Action


@dataclass(frozen=True)
class Selection:
    selected_planner_identity: str
    confidence: float
    feedback: str
    abstain: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("selection confidence must be between 0 and 1")
        if not self.feedback:
            raise ValueError("selection feedback is required")


Selector = Callable[[TaskContract, List[StepRecord], Sequence[Proposal]], Selection]


class EnsemblePlanner:
    def __init__(
        self,
        planners: Mapping[str, Planner],
        selector: Selector,
        *,
        selector_identity: str,
        min_successful_proposals: int = 2,
        min_selection_confidence: float = 0.5,
    ) -> None:
        if len(planners) < 2:
            raise ValueError("ensemble requires at least two distinct planner identities")
        if len(set(planners)) != len(planners):
            raise ValueError("planner identities must be unique")
        if not selector_identity:
            raise ValueError("selector_identity is required")
        if selector_identity in planners:
            raise ValueError("selector identity must differ from every planner identity")
        if min_successful_proposals < 2 or min_successful_proposals > len(planners):
            raise ValueError("min_successful_proposals must be between 2 and planner count")
        if not 0.0 <= min_selection_confidence <= 1.0:
            raise ValueError("min_selection_confidence must be between 0 and 1")
        self.planners: Dict[str, Planner] = dict(planners)
        self.selector = selector
        self.selector_identity = selector_identity
        self.min_successful_proposals = min_successful_proposals
        self.min_selection_confidence = min_selection_confidence
        self.last_errors: Dict[str, str] = {}

    def __call__(self, contract: TaskContract, trace: List[StepRecord]) -> Action:
        proposals: List[Proposal] = []
        errors: Dict[str, str] = {}
        for identity in sorted(self.planners):
            planner = self.planners[identity]
            try:
                action = planner(contract, list(trace))
            except Exception as exc:
                errors[identity] = f"{type(exc).__name__}: {exc}"
                continue
            if not isinstance(action, Action):
                errors[identity] = "TypeError: planner must return Action"
                continue
            if action.tool not in contract.allowed_tools:
                errors[identity] = f"proposed disallowed tool {action.tool!r}"
                continue
            proposals.append(Proposal(identity, action))

        self.last_errors = errors
        if len(proposals) < self.min_successful_proposals:
            raise RuntimeError(
                f"ensemble admitted {len(proposals)} proposals; "
                f"requires {self.min_successful_proposals}; errors={errors}"
            )

        selection = self.selector(contract, list(trace), tuple(proposals))
        if not isinstance(selection, Selection):
            raise TypeError("selector must return Selection")
        if selection.abstain:
            raise RuntimeError(f"ensemble selector abstained: {selection.feedback}")
        if selection.confidence < self.min_selection_confidence:
            raise RuntimeError(
                f"ensemble selector confidence {selection.confidence:.3f} below "
                f"minimum {self.min_selection_confidence:.3f}: {selection.feedback}"
            )
        by_identity = {proposal.planner_identity: proposal.action for proposal in proposals}
        if selection.selected_planner_identity not in by_identity:
            raise ValueError("selector chose a planner identity that was not admitted")
        chosen = by_identity[selection.selected_planner_identity]
        return Action(
            tool=chosen.tool,
            arguments=dict(chosen.arguments),
            rationale=(
                chosen.rationale
                + (" | " if chosen.rationale else "")
                + f"ensemble selected by {self.selector_identity}: {selection.feedback}"
            ),
        )
