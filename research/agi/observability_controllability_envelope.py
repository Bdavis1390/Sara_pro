from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class OCRegime(str, Enum):
    HIGH_O_HIGH_C = "HIGH_O_HIGH_C"
    HIGH_O_LOW_C = "HIGH_O_LOW_C"
    LOW_O_HIGH_C_HAZARD = "LOW_O_HIGH_C_HAZARD"
    LOW_O_LOW_C = "LOW_O_LOW_C"

@dataclass(frozen=True)
class StateDimension:
    name: str
    observability: float
    potential_controllability: float
    authorized_controllability: float
    safe_controllability: float
    consequence: float
    safety_shield: bool = False

    def validate(self) -> None:
        for name in (
            "observability",
            "potential_controllability",
            "authorized_controllability",
            "safe_controllability",
            "consequence",
        ):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0,1]")
        if self.authorized_controllability > self.potential_controllability:
            raise ValueError("authorized control cannot exceed potential control")
        if self.safe_controllability > self.authorized_controllability:
            raise ValueError("safe control cannot exceed authorized control")

    def regime(self, threshold: float = 0.5) -> OCRegime:
        self.validate()
        high_o = self.observability >= threshold
        high_c = self.safe_controllability >= threshold
        if high_o and high_c:
            return OCRegime.HIGH_O_HIGH_C
        if high_o and not high_c:
            return OCRegime.HIGH_O_LOW_C
        if not high_o and high_c:
            return OCRegime.LOW_O_HIGH_C_HAZARD
        return OCRegime.LOW_O_LOW_C

def governance_gate(
    state: StateDimension,
    observability_margin: float = 0.1,
    high_consequence_threshold: float = 0.6,
) -> str:
    state.validate()
    if state.consequence < high_consequence_threshold:
        return "STANDARD_POLICY_EVALUATION"

    observability_bound = min(1.0, state.observability + observability_margin)
    if (
        state.authorized_controllability > observability_bound
        and not state.safety_shield
    ):
        return "BLOCK_CONTROL_OUTRUNS_OBSERVABILITY"

    if state.regime() == OCRegime.LOW_O_HIGH_C_HAZARD and not state.safety_shield:
        return "BLOCK_LOW_OBSERVABILITY_HIGH_CONTROL"

    if state.safety_shield:
        return "ALLOW_ONLY_THROUGH_VALIDATED_SAFETY_SHIELD"

    return "ELIGIBLE_FOR_CLOSED_LOOP_CONTROL"

@dataclass(frozen=True)
class DualAction:
    name: str
    task_value: float
    epistemic_value: float
    risk: float
    cost: float
    authorized: bool

def dual_utility(
    action: DualAction,
    epistemic_weight: float = 1.0,
    risk_weight: float = 1.0,
    cost_weight: float = 1.0,
) -> float:
    if not action.authorized:
        return float("-inf")
    return (
        action.task_value
        + epistemic_weight * action.epistemic_value
        - risk_weight * action.risk
        - cost_weight * action.cost
    )

def choose_dual_action(
    actions: list[DualAction],
    epistemic_weight: float = 1.0,
) -> tuple[str, float]:
    if not actions:
        raise ValueError("actions required")
    scored = [
        (a.name, dual_utility(a, epistemic_weight))
        for a in actions
    ]
    return max(scored, key=lambda x: x[1])
