from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class NetworkPerturbation:
    source_region: str
    target_region: str
    frequency_hz: float
    amplitude: float | None = None
    phase_rad: float | None = None
    bandwidth_hz: float | None = None
    field_strength: float | None = None
    connectivity_score: float | None = None
    tissue_integrity: float | None = None
    criticality_score: float | None = None
    nonequilibrium_score: float | None = None
    evidence_ref: str | None = None

    def validate(self) -> None:
        if self.frequency_hz <= 0:
            raise ValueError("frequency must be positive")
        for name in (
            "connectivity_score",
            "tissue_integrity",
            "criticality_score",
            "nonequilibrium_score",
        ):
            value = getattr(self, name)
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0,1]")

def same_frequency_different_topology(
    a: NetworkPerturbation,
    b: NetworkPerturbation,
) -> bool:
    return (
        a.frequency_hz == b.frequency_hz
        and (
            a.source_region != b.source_region
            or a.target_region != b.target_region
            or a.connectivity_score != b.connectivity_score
        )
    )

def claim_ceiling(p: NetworkPerturbation) -> str:
    p.validate()
    if p.evidence_ref is None:
        return "PERTURBATION_HYPOTHESIS"
    if p.connectivity_score is None:
        return "FREQUENCY_TARGET_ASSOCIATION_ONLY"
    if p.criticality_score is None and p.nonequilibrium_score is None:
        return "NETWORK_COUPLING_SUPPORTED_STATE_DEPENDENCE_UNTESTED"
    return "NETWORK_STATE_COUPLING_TESTABLE"

def frequency_only_model_is_insufficient(
    frequency_predicts: bool,
    topology_adds_out_of_sample_value: bool,
) -> bool:
    return topology_adds_out_of_sample_value

@dataclass(frozen=True)
class CrossFrequencyChannel:
    source_band_hz: tuple[float, float]
    target_band_hz: tuple[float, float]
    source_region: str
    target_region: str
    directed_information: float
    state: str

    def validate(self) -> None:
        if self.source_band_hz[0] >= self.source_band_hz[1]:
            raise ValueError("invalid source band")
        if self.target_band_hz[0] >= self.target_band_hz[1]:
            raise ValueError("invalid target band")
        if self.directed_information < 0:
            raise ValueError("directed information must be nonnegative")
