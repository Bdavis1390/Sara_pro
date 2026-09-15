"""Lineage verification for WS-CAE continuity state transitions."""

from __future__ import annotations

from dataclasses import dataclass

from .continuity_transition import ContinuityTransition, validate_transition


@dataclass(frozen=True)
class LineageAssessment:
    valid: bool
    subject_id: str
    genesis_content_id: str
    tip_content_ids: tuple[str, ...]
    fork_points: tuple[str, ...]
    issues: tuple[str, ...]


def assess_lineage(
    transitions: tuple[ContinuityTransition, ...],
    *,
    genesis_content_id: str,
) -> LineageAssessment:
    issues: list[str] = []
    if not transitions:
        return LineageAssessment(True, "", genesis_content_id, (genesis_content_id,), tuple(), tuple())

    subjects = {t.subject_id for t in transitions}
    if len(subjects) != 1:
        issues.append("lineage contains more than one subject_id")
    subject = next(iter(subjects)) if subjects else ""

    for index, transition in enumerate(transitions):
        for issue in validate_transition(transition):
            issues.append(f"transition[{index}]: {issue}")

    successors: dict[str, set[str]] = {}
    incoming: dict[str, set[str]] = {}
    for transition in transitions:
        successors.setdefault(transition.previous_content_id, set()).add(transition.new_content_id)
        incoming.setdefault(transition.new_content_id, set()).add(transition.previous_content_id)

    forks = tuple(sorted(state for state, targets in successors.items() if len(targets) > 1))
    if forks:
        issues.append("lineage contains one or more fork points")

    for state, parents in incoming.items():
        if len(parents) > 1:
            issues.append(f"state has multiple predecessors: {state}")

    reachable = {genesis_content_id}
    changed = True
    while changed:
        changed = False
        for previous, targets in successors.items():
            if previous in reachable:
                before = len(reachable)
                reachable.update(targets)
                changed |= len(reachable) != before

    referenced_states = set(successors) | set(incoming)
    unreachable = referenced_states - reachable
    if unreachable:
        issues.append("lineage contains states not reachable from genesis")

    for transition in transitions:
        if transition.new_content_id == genesis_content_id:
            issues.append("lineage cycles back to genesis")
            break

    tips = tuple(sorted(state for state in reachable if not successors.get(state)))
    if not tips:
        issues.append("lineage has no terminal state")

    return LineageAssessment(
        valid=not issues,
        subject_id=subject,
        genesis_content_id=genesis_content_id,
        tip_content_ids=tips,
        fork_points=forks,
        issues=tuple(issues),
    )
