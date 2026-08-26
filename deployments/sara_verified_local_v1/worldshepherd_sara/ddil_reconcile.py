from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReconciliationState(str, Enum):
    MERGED = "MERGED"
    CONFLICT = "CONFLICT"
    NO_CHANGE = "NO_CHANGE"


@dataclass(frozen=True)
class VersionedState:
    key: str
    value: Any
    logical_clock: int
    authority: int
    source_node: str


@dataclass(frozen=True)
class ReconciliationResult:
    key: str
    state: ReconciliationState
    selected: VersionedState | None
    candidates: tuple[VersionedState, ...]
    reason: str


def reconcile_key(candidates: list[VersionedState]) -> ReconciliationResult:
    """Reconcile one key while surfacing unresolved equal-authority divergence.

    Policy:
    1. newer logical clock wins over older state;
    2. for equal clocks, higher explicit authority wins;
    3. equal clock + equal authority + different values is a visible CONFLICT;
    4. identical equal-priority values merge deterministically.

    This is an internal software policy baseline, not an operational distributed
    consensus or safety-certified conflict-resolution protocol.
    """
    if not candidates:
        raise ValueError("at least one candidate is required")
    keys = {item.key for item in candidates}
    if len(keys) != 1:
        raise ValueError("all candidates must share the same key")

    ordered = sorted(
        candidates,
        key=lambda item: (item.logical_clock, item.authority, item.source_node),
        reverse=True,
    )
    newest_clock = ordered[0].logical_clock
    newest = [item for item in ordered if item.logical_clock == newest_clock]
    highest_authority = max(item.authority for item in newest)
    finalists = [item for item in newest if item.authority == highest_authority]

    distinct_values = {repr(item.value) for item in finalists}
    if len(distinct_values) > 1:
        return ReconciliationResult(
            key=ordered[0].key,
            state=ReconciliationState.CONFLICT,
            selected=None,
            candidates=tuple(sorted(finalists, key=lambda item: item.source_node)),
            reason="equal-clock equal-authority candidates disagree; human/policy resolution required",
        )

    selected = sorted(finalists, key=lambda item: item.source_node)[0]
    if all(
        item.logical_clock == selected.logical_clock
        and item.authority == selected.authority
        and item.value == selected.value
        for item in candidates
    ):
        state = ReconciliationState.NO_CHANGE
        reason = "all candidate states are equivalent"
    else:
        state = ReconciliationState.MERGED
        reason = "selected newest/highest-authority non-conflicting state"
    return ReconciliationResult(
        key=selected.key,
        state=state,
        selected=selected,
        candidates=tuple(sorted(candidates, key=lambda item: item.source_node)),
        reason=reason,
    )


def reconcile_maps(
    left: dict[str, VersionedState], right: dict[str, VersionedState]
) -> dict[str, ReconciliationResult]:
    results: dict[str, ReconciliationResult] = {}
    for key in sorted(set(left) | set(right)):
        candidates = [mapping[key] for mapping in (left, right) if key in mapping]
        results[key] = reconcile_key(candidates)
    return results
