"""Cross-ecosystem post-quantum migration-horizon classifier.

This module compares protocol migration milestones with an external planning
horizon. It is a defensive planning control only: roadmap dates are not Q-day,
and project roadmaps are not treated as delivered capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class EcosystemTransition:
    ecosystem: str
    source: str
    target_year: int
    scope: str
    deployed_account_layer: bool = False
    full_protocol_quantum_resilience: bool = False
    roadmap_status: str = "planning"


@dataclass(frozen=True)
class EcosystemHorizonAssessment:
    ecosystem: str
    margin_years: int
    state: str
    scope_state: str
    urgency: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_transition(transition: EcosystemTransition, *, risk_horizon_year: int) -> EcosystemHorizonAssessment:
    margin = risk_horizon_year - transition.target_year
    reasons: list[str] = []

    if margin < 0:
        state = "TARGET_AFTER_RISK_HORIZON"
        urgency = "ACCELERATE_AND_PARALLELIZE_MIGRATION"
        reasons.append("The stated transition target falls after the supplied planning horizon.")
    elif margin == 0:
        state = "TARGET_AT_RISK_HORIZON"
        urgency = "NO_SCHEDULE_SLACK"
        reasons.append("The stated transition target consumes the supplied planning horizon.")
    else:
        state = "TARGET_BEFORE_RISK_HORIZON"
        urgency = "VALIDATE_SCOPE_AND_DELIVERY"
        reasons.append("The stated transition target is nominally before the supplied planning horizon.")

    if transition.full_protocol_quantum_resilience:
        scope_state = "FULL_PROTOCOL_SCOPE"
    elif transition.deployed_account_layer:
        scope_state = "ACCOUNT_LAYER_DEPLOYED_PROTOCOL_INCOMPLETE"
        reasons.append("Account-layer PQ support does not establish full-protocol quantum resilience.")
    else:
        scope_state = "ROADMAP_OR_PARTIAL_SCOPE"
        reasons.append("The represented milestone is roadmap/partial scope rather than full-protocol completion.")

    if transition.roadmap_status.lower() != "delivered":
        reasons.append("Target year is planning evidence, not a guaranteed delivery date.")

    return EcosystemHorizonAssessment(
        ecosystem=transition.ecosystem,
        margin_years=margin,
        state=state,
        scope_state=scope_state,
        urgency=urgency,
        reasons=tuple(reasons),
    )


def portfolio_state(transitions: tuple[EcosystemTransition, ...], *, risk_horizon_year: int) -> dict:
    assessments = tuple(assess_transition(item, risk_horizon_year=risk_horizon_year) for item in transitions)
    outside = sum(item.state == "TARGET_AFTER_RISK_HORIZON" for item in assessments)
    at_horizon = sum(item.state == "TARGET_AT_RISK_HORIZON" for item in assessments)
    incomplete_scope = sum(item.scope_state != "FULL_PROTOCOL_SCOPE" for item in assessments)
    if outside:
        state = "MULTI_ECOSYSTEM_MIGRATION_DEFICIT"
    elif at_horizon:
        state = "MULTI_ECOSYSTEM_NO_SLACK"
    else:
        state = "NOMINALLY_WITHIN_HORIZON_SCOPE_REVIEW_REQUIRED"
    return {
        "portfolio_state": state,
        "outside_horizon_count": outside,
        "at_horizon_count": at_horizon,
        "incomplete_scope_count": incomplete_scope,
        "assessments": [item.to_dict() for item in assessments],
    }
