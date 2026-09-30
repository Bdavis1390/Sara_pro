"""WS-SEMCAP-01 metrics. Numerical evaluation only; no program qualification."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemcapMeasurements:
    baseline_bits: int
    semantic_bits: int
    baseline_mission_utility: float
    semantic_mission_utility: float
    latency_ms: float
    power_w: float
    missed_critical_events: int
    false_semantic_selections: int
    reconstruction_fidelity: float
    provenance_completeness: float

    def validate(self) -> None:
        if self.baseline_bits <= 0 or self.semantic_bits < 0:
            raise ValueError("invalid bit counts")
        if self.baseline_mission_utility <= 0:
            raise ValueError("baseline mission utility must be positive")
        if self.latency_ms < 0 or self.power_w < 0:
            raise ValueError("latency/power cannot be negative")
        if self.missed_critical_events < 0 or self.false_semantic_selections < 0:
            raise ValueError("event counts cannot be negative")
        for value in (self.reconstruction_fidelity, self.provenance_completeness):
            if not 0.0 <= value <= 1.0:
                raise ValueError("normalized metrics must be in [0,1]")

    @property
    def reduction(self) -> float:
        self.validate()
        return 1.0 - (self.semantic_bits / self.baseline_bits)

    @property
    def utility_retention(self) -> float:
        self.validate()
        return self.semantic_mission_utility / self.baseline_mission_utility


def evaluate_thresholds(m: SemcapMeasurements, *, min_reduction: float, min_utility_retention: float,
                        max_latency_ms: float, max_power_w: float,
                        min_reconstruction_fidelity: float, min_provenance_completeness: float) -> dict[str, bool]:
    """Evaluate declared experiment thresholds; thresholds are not certification criteria."""
    m.validate()
    return {
        "Q_C_reduction": m.reduction >= min_reduction,
        "Q_X_utility": m.utility_retention >= min_utility_retention,
        "Q_latency": m.latency_ms <= max_latency_ms,
        "Q_power": m.power_w <= max_power_w,
        "Q_critical_events": m.missed_critical_events == 0,
        "Q_X_reconstruction": m.reconstruction_fidelity >= min_reconstruction_fidelity,
        "Q_E_provenance": m.provenance_completeness >= min_provenance_completeness,
    }
