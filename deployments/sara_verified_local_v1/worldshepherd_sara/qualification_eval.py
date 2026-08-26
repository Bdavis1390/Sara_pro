from __future__ import annotations

from typing import Any

from .evidence_artifacts import ComparisonOperator, ExpectedResult


def evaluate_expected_result(expected: ExpectedResult, observed: dict[str, Any]) -> bool:
    if expected.metric not in observed:
        return False
    value = observed[expected.metric]
    target = expected.target
    operator = expected.operator

    if operator == ComparisonOperator.EQ:
        return value == target
    if operator == ComparisonOperator.NE:
        return value != target
    if operator == ComparisonOperator.LT:
        return value < target
    if operator == ComparisonOperator.LE:
        return value <= target
    if operator == ComparisonOperator.GT:
        return value > target
    if operator == ComparisonOperator.GE:
        return value >= target
    raise ValueError(f"unsupported comparison operator: {operator}")


def evaluate_all_expected_results(
    expected_results: list[ExpectedResult], observed: dict[str, Any]
) -> tuple[bool, dict[str, bool]]:
    outcomes = {
        expected.metric: evaluate_expected_result(expected, observed)
        for expected in expected_results
    }
    return all(outcomes.values()), outcomes
