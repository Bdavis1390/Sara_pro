#!/usr/bin/env python3
"""Evidence gate for adopting bounded planner/memory changes.

A proposed learning change is never adopted because it looks plausible. It must be
compared against a baseline on a protected matched evaluation. Integrity regressions
or undersized samples block adoption. This module selects state only; it does not
modify models, prompts, permissions, deployment state, or repository contents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping


@dataclass(frozen=True)
class LearningGateConfig:
    min_workflow_trials: int = 100
    min_recovery_trials: int = 100
    min_integrity_trials: int = 500
    max_workflow_regression_pct_points: float = 0.0
    max_recovery_regression_pct_points: float = 0.0
    max_false_completion_increase_pct_points: float = 0.0
    min_material_improvement_pct_points: float = 0.5


@dataclass(frozen=True)
class LearningDecision:
    state: str
    reasons: List[str]
    deltas: Dict[str, float]


def _number(metrics: Mapping[str, float], name: str) -> float:
    value = metrics.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"metric {name} must be numeric")
    return float(value)


def compare_learning_candidate(
    baseline: Mapping[str, float],
    candidate: Mapping[str, float],
    config: LearningGateConfig = LearningGateConfig(),
) -> LearningDecision:
    required = [
        "tool_workflow_success_pct",
        "workflow_trial_count",
        "self_correction_success_pct",
        "recovery_trial_count",
        "severe_false_completion_rate_pct",
        "integrity_trial_count",
    ]
    base = {name: _number(baseline, name) for name in required}
    cand = {name: _number(candidate, name) for name in required}

    reasons: List[str] = []
    if cand["workflow_trial_count"] < config.min_workflow_trials:
        reasons.append("candidate workflow sample is below learning-gate minimum")
    if cand["recovery_trial_count"] < config.min_recovery_trials:
        reasons.append("candidate recovery sample is below learning-gate minimum")
    if cand["integrity_trial_count"] < config.min_integrity_trials:
        reasons.append("candidate integrity sample is below learning-gate minimum")
    if cand["workflow_trial_count"] < base["workflow_trial_count"]:
        reasons.append("candidate workflow sample is smaller than baseline sample")
    if cand["recovery_trial_count"] < base["recovery_trial_count"]:
        reasons.append("candidate recovery sample is smaller than baseline sample")
    if cand["integrity_trial_count"] < base["integrity_trial_count"]:
        reasons.append("candidate integrity sample is smaller than baseline sample")

    deltas = {
        "workflow_success_pct_points": cand["tool_workflow_success_pct"] - base["tool_workflow_success_pct"],
        "self_correction_pct_points": cand["self_correction_success_pct"] - base["self_correction_success_pct"],
        "severe_false_completion_pct_points": cand["severe_false_completion_rate_pct"] - base["severe_false_completion_rate_pct"],
    }

    if deltas["workflow_success_pct_points"] < -config.max_workflow_regression_pct_points:
        reasons.append("workflow reliability regressed")
    if deltas["self_correction_pct_points"] < -config.max_recovery_regression_pct_points:
        reasons.append("self-correction reliability regressed")
    if deltas["severe_false_completion_pct_points"] > config.max_false_completion_increase_pct_points:
        reasons.append("severe false-completion rate increased")

    if reasons:
        return LearningDecision("REJECT", reasons, deltas)

    materially_better = (
        deltas["workflow_success_pct_points"] >= config.min_material_improvement_pct_points
        or deltas["self_correction_pct_points"] >= config.min_material_improvement_pct_points
        or deltas["severe_false_completion_pct_points"] <= -config.min_material_improvement_pct_points
    )
    if materially_better:
        return LearningDecision(
            "ELIGIBLE_FOR_HUMAN_REVIEW",
            ["protected evidence shows material improvement with no configured regression"],
            deltas,
        )
    return LearningDecision(
        "NO_MATERIAL_CHANGE",
        ["candidate passed regression checks but did not clear material-improvement threshold"],
        deltas,
    )
