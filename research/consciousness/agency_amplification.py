from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class CouplingKind(str, Enum):
    BIOLOGICAL = "BIOLOGICAL"
    ACOUSTIC = "ACOUSTIC"
    ELECTROMAGNETIC = "ELECTROMAGNETIC"
    MECHANICAL = "MECHANICAL"
    BCI = "BCI"
    SOFTWARE = "SOFTWARE"
    SOCIAL = "SOCIAL"

@dataclass(frozen=True)
class CouplingStage:
    name: str
    coupling_kind: CouplingKind
    input_power_w: float | None = None
    output_power_w: float | None = None
    externally_powered: bool = False
    bandwidth_hz: float | None = None
    latency_s: float | None = None
    evidence_ref: str | None = None

    def power_gain(self) -> float | None:
        if (
            self.input_power_w is None
            or self.output_power_w is None
            or self.input_power_w <= 0
        ):
            return None
        return self.output_power_w / self.input_power_w

@dataclass
class AgencyPath:
    path_id: str
    stages: list[CouplingStage]

    def validate(self) -> None:
        if not self.stages:
            raise ValueError("agency path requires at least one stage")
        for stage in self.stages:
            if stage.externally_powered and not stage.evidence_ref:
                raise ValueError(
                    f"externally powered stage {stage.name} requires evidence_ref"
                )

    def externally_powered_stages(self) -> list[str]:
        return [s.name for s in self.stages if s.externally_powered]

    def minimum_bandwidth_hz(self) -> float | None:
        values = [s.bandwidth_hz for s in self.stages if s.bandwidth_hz is not None]
        return min(values) if values else None

    def total_latency_s(self) -> float | None:
        values = [s.latency_s for s in self.stages if s.latency_s is not None]
        return sum(values) if values else None

    def claim_ceiling(self) -> str:
        self.validate()
        if any(s.evidence_ref is None for s in self.stages):
            return "PATHWAY_HYPOTHESIS"
        return "PHYSICALLY_SPECIFIED_CAUSAL_PATHWAY"

def same_frequency_is_not_coupling(
    source_frequency_hz: float,
    target_frequency_hz: float,
    has_mechanism: bool,
) -> str:
    if source_frequency_hz == target_frequency_hz and not has_mechanism:
        return "NUMERICAL_MATCH_ONLY"
    if has_mechanism:
        return "COUPLING_MAY_BE_TESTED"
    return "NO_COUPLING_EVIDENCE"
