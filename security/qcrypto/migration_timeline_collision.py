"""Defensive migration-timeline collision classifier.

This module compares protocol migration/sunset schedules with external planning
horizons. It does not claim that a vendor roadmap will be achieved or that a
cryptographically relevant quantum computer exists. A negative margin is a
schedule-risk signal only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProtocolTransitionSchedule:
    name: str
    source: str
    years_to_full_transition: float
    consensus_activated: bool = False
    schedule_status: str = "Draft"


@dataclass(frozen=True)
class ExternalRiskHorizon:
    name: str
    source: str
    target_year: int
    demonstrated: bool = False
    evidence_class: str = "vendor_roadmap"


@dataclass(frozen=True)
class TimelineCollisionAssessment:
    collision_state: str
    best_case_margin_years: float
    schedule_state: str
    horizon_state: str
    urgency: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_timeline_collision(
    schedule: ProtocolTransitionSchedule,
    horizon: ExternalRiskHorizon,
    *,
    current_year: int,
) -> TimelineCollisionAssessment:
    """Compare a transition schedule with an external planning horizon.

    ``best_case_margin_years`` assumes the protocol schedule starts immediately.
    If the proposal is not activated, the real margin can only be smaller. A
    negative result therefore means even immediate activation would not finish
    the stated transition before the supplied planning horizon.
    """

    years_to_horizon = horizon.target_year - current_year
    margin = years_to_horizon - schedule.years_to_full_transition
    reasons: list[str] = []

    if margin < 0:
        collision_state = "BEST_CASE_TRANSITION_EXCEEDS_RISK_HORIZON"
        urgency = "ACCELERATE_PARALLEL_MIGRATION_AND_ACTIVATION_PLANNING"
        reasons.append("Even immediate schedule start would finish after the supplied planning horizon.")
    elif margin == 0:
        collision_state = "BEST_CASE_TRANSITION_MEETS_RISK_HORIZON_WITHOUT_SLACK"
        urgency = "NO_SCHEDULE_SLACK"
        reasons.append("Immediate schedule start would consume the entire supplied planning horizon.")
    else:
        collision_state = "BEST_CASE_TRANSITION_WITHIN_RISK_HORIZON"
        urgency = "MONITOR_AND_VALIDATE_MIGRATION_CAPACITY"
        reasons.append("The nominal transition fits inside the supplied horizon if started immediately.")

    schedule_state = "CONSENSUS_ACTIVE" if schedule.consensus_activated else "NOT_CONSENSUS_ACTIVE"
    horizon_state = "DEMONSTRATED_CAPABILITY" if horizon.demonstrated else "FORWARD_PLANNING_EVIDENCE"

    if not schedule.consensus_activated:
        reasons.append("The protocol schedule is not consensus-active, so the calculated margin is an optimistic upper bound.")
    if not horizon.demonstrated:
        reasons.append("The external horizon is forward-looking planning evidence, not demonstrated cryptanalytic capability or Q-day.")

    return TimelineCollisionAssessment(
        collision_state=collision_state,
        best_case_margin_years=margin,
        schedule_state=schedule_state,
        horizon_state=horizon_state,
        urgency=urgency,
        reasons=tuple(reasons),
    )
