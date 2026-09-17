from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from .cbm_twin import HealthFinding
from .prime import ActionState


class ReleaseGate(str, Enum):
    HELD = "HELD"
    DENIED = "DENIED"
    APPLIED = "APPLIED"
    OVERRIDDEN = "OVERRIDDEN"


class ReleaseGateDecision(BaseModel):
    readiness: str
    degraded_metrics: list[str]
    authorization_state: ActionState
    gate: ReleaseGate
    release_allowed: bool
    reviewer: str | None = None
    rationale: list[str]


def evaluate_release_gate(
    findings: tuple[HealthFinding, ...],
    *,
    reviewer: str | None = None,
    release_requested: bool = False,
    explicit_degraded_override: bool = False,
) -> ReleaseGateDecision:
    """Gate a software configuration release using health and review state."""

    degraded_metrics = sorted(
        {finding.metric for finding in findings if finding.status != "NOMINAL"}
    )
    readiness = "DEGRADED" if degraded_metrics else "READY"

    if explicit_degraded_override and not release_requested:
        raise ValueError("degraded override requires an explicit release request")
    if release_requested and not reviewer:
        raise ValueError("configuration release requires an identified reviewer")
    if explicit_degraded_override and not degraded_metrics:
        raise ValueError("degraded override is invalid when health is nominal")

    if not release_requested:
        state = ActionState.DENIED if reviewer else ActionState.PROPOSED
        gate = ReleaseGate.DENIED if reviewer else ReleaseGate.HELD
        return ReleaseGateDecision(
            readiness=readiness,
            degraded_metrics=degraded_metrics,
            authorization_state=state,
            gate=gate,
            release_allowed=False,
            reviewer=reviewer,
            rationale=[
                "No approved configuration release is active.",
                "The current configuration must remain unchanged.",
            ],
        )

    if degraded_metrics and not explicit_degraded_override:
        return ReleaseGateDecision(
            readiness=readiness,
            degraded_metrics=degraded_metrics,
            authorization_state=ActionState.DENIED,
            gate=ReleaseGate.DENIED,
            release_allowed=False,
            reviewer=reviewer,
            rationale=[
                "Ordinary release is blocked while health is degraded.",
                "A separately recorded degraded-state override is required.",
            ],
        )

    if degraded_metrics:
        return ReleaseGateDecision(
            readiness=readiness,
            degraded_metrics=degraded_metrics,
            authorization_state=ActionState.OVERRIDDEN,
            gate=ReleaseGate.OVERRIDDEN,
            release_allowed=True,
            reviewer=reviewer,
            rationale=[
                "Health is degraded.",
                "An identified reviewer explicitly authorized the degraded-state override.",
            ],
        )

    return ReleaseGateDecision(
        readiness=readiness,
        degraded_metrics=[],
        authorization_state=ActionState.APPROVED,
        gate=ReleaseGate.APPLIED,
        release_allowed=True,
        reviewer=reviewer,
        rationale=[
            "Health is nominal.",
            "An identified reviewer approved the configuration release.",
        ],
    )
