from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Sequence

@dataclass(frozen=True)
class ResonanceContext:
    person_id: str
    target: str
    state_id: str
    task: str
    timepoint: str | None = None

@dataclass(frozen=True)
class FrequencyProbe:
    context: ResonanceContext
    frequency_hz: float
    network_engagement: float
    behavioral_score: float | None = None
    safety_ok: bool = True
    evidence_ref: str | None = None

def choose_local_optimum(
    probes: Sequence[FrequencyProbe],
    require_safety: bool = True,
) -> FrequencyProbe:
    if not probes:
        raise ValueError("at least one frequency probe is required")

    contexts = {p.context for p in probes}
    if len(contexts) != 1:
        raise ValueError(
            "frequency probes must share person/target/state/task context"
        )

    eligible = [
        p for p in probes
        if (p.safety_ok or not require_safety)
    ]
    if not eligible:
        raise ValueError("no safe candidate frequencies")

    return max(
        eligible,
        key=lambda p: (
            p.network_engagement,
            float("-inf") if p.behavioral_score is None else p.behavioral_score,
        ),
    )

def universal_frequency_claim_supported(
    per_context_optima: Iterable[FrequencyProbe],
    tolerance_hz: float = 0.0,
) -> bool:
    values = [p.frequency_hz for p in per_context_optima]
    if len(values) < 2:
        return False
    return max(values) - min(values) <= tolerance_hz

def context_transfer_allowed(
    source: ResonanceContext,
    target: ResonanceContext,
) -> str:
    if source == target:
        return "SAME_CONTEXT"
    if source.person_id != target.person_id:
        return "RECALIBRATE_FOR_PERSON"
    if source.target != target.target:
        return "RECALIBRATE_FOR_TARGET"
    if source.state_id != target.state_id:
        return "RECALIBRATE_FOR_STATE"
    if source.task != target.task:
        return "RECALIBRATE_FOR_TASK"
    return "RECALIBRATE_FOR_TIME"

def adaptive_update_required(
    previous_state_id: str,
    current_state_id: str,
) -> bool:
    return previous_state_id != current_state_id
