from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class DirectionalMode(str, Enum):
    TOP_DOWN = "TOP_DOWN"
    BOTTOM_UP = "BOTTOM_UP"
    MIXED = "MIXED"
    UNRESOLVED = "UNRESOLVED"

@dataclass(frozen=True)
class NetworkPhaseState:
    timestamp_ms: float
    mode: DirectionalMode
    phase_rad: float | None
    connectivity_state: str | None
    state_confidence: float

    def validate(self) -> None:
        if not 0 <= self.state_confidence <= 1:
            raise ValueError("state_confidence must be in [0,1]")

@dataclass(frozen=True)
class PerturbationWindow:
    state: NetworkPhaseState
    desired_transition: DirectionalMode
    predicted_probability: float
    model_ref: str
    safety_authorized: bool = False

    def validate(self) -> None:
        self.state.validate()
        if not 0 <= self.predicted_probability <= 1:
            raise ValueError("predicted_probability must be in [0,1]")

    def action_gate(self) -> str:
        self.validate()
        if not self.safety_authorized:
            return "BLOCK_UNAUTHORIZED"
        if self.state.state_confidence < 0.8:
            return "MEASURE_STATE_FIRST"
        if self.predicted_probability < 0.7:
            return "NO_HIGH_CONFIDENCE_TRANSITION_WINDOW"
        return "ELIGIBLE_FOR_SUPERVISED_RESEARCH_PROTOCOL"

def transition_interval_ms(
    previous_timestamp_ms: float,
    current_timestamp_ms: float,
) -> float:
    if current_timestamp_ms < previous_timestamp_ms:
        raise ValueError("timestamps must be ordered")
    return current_timestamp_ms - previous_timestamp_ms

def approximate_switch_rate_hz(interval_ms: float) -> float:
    if interval_ms <= 0:
        raise ValueError("interval_ms must be positive")
    return 1000.0 / interval_ms

def frequency_of_switching_is_not_carrier(
    switch_rate_hz: float,
    neural_carrier_hz: float,
) -> str:
    if abs(switch_rate_hz - neural_carrier_hz) < 1e-9:
        return "NUMERIC_MATCH_DOES_NOT_ESTABLISH_IDENTITY"
    return "DISTINCT_DYNAMICAL_QUANTITIES"
