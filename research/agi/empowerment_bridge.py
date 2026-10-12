from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from math import log2
from typing import Mapping, Sequence

class EmpowermentClass(str, Enum):
    POTENTIAL = "POTENTIAL"
    DEMONSTRATED = "DEMONSTRATED"
    AUTHORIZED = "AUTHORIZED"
    SAFE = "SAFE"

def mutual_information(joint: Mapping[tuple[str, str], float]) -> float:
    p_a: dict[str, float] = {}
    p_s: dict[str, float] = {}
    for (a, s), p in joint.items():
        if p < 0:
            raise ValueError("probabilities must be nonnegative")
        p_a[a] = p_a.get(a, 0.0) + p
        p_s[s] = p_s.get(s, 0.0) + p
    total = sum(joint.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError("joint distribution must sum to 1")
    mi = 0.0
    for (a, s), p in joint.items():
        if p == 0:
            continue
        denom = p_a[a] * p_s[s]
        mi += p * log2(p / denom)
    return mi

@dataclass(frozen=True)
class AgencyCapability:
    name: str
    potential_bits: float
    demonstrated_bits: float
    authorized_bits: float
    safe_bits: float

    def validate(self) -> None:
        values = [
            self.potential_bits,
            self.demonstrated_bits,
            self.authorized_bits,
            self.safe_bits,
        ]
        if any(v < 0 for v in values):
            raise ValueError("empowerment cannot be negative")
        if self.demonstrated_bits > self.potential_bits:
            raise ValueError("demonstrated cannot exceed potential")
        if self.authorized_bits > self.potential_bits:
            raise ValueError("authorized cannot exceed potential")
        if self.safe_bits > self.authorized_bits:
            raise ValueError("safe cannot exceed authorized")

    def governance_gap(self) -> float:
        self.validate()
        return max(0.0, self.demonstrated_bits - self.safe_bits)

def safe_agency_index(
    capability: AgencyCapability,
    epistemic_calibration: float,
    provenance_coverage: float,
    causal_model_score: float,
) -> float:
    capability.validate()
    for x in (epistemic_calibration, provenance_coverage, causal_model_score):
        if not 0 <= x <= 1:
            raise ValueError("quality factors must be in [0,1]")
    if capability.potential_bits == 0:
        control_fraction = 0.0
    else:
        control_fraction = capability.safe_bits / capability.potential_bits
    return (
        control_fraction
        * epistemic_calibration
        * provenance_coverage
        * causal_model_score
    )

def agency_readiness(
    world_model: bool,
    uncertainty_model: bool,
    intervention_model: bool,
    feedback_loop: bool,
    provenance: bool,
    authorization: bool,
) -> str:
    required = [
        world_model,
        uncertainty_model,
        intervention_model,
        feedback_loop,
        provenance,
        authorization,
    ]
    if all(required):
        return "BOUNDED_GENERAL_AGENCY_TESTABLE"
    if sum(required) >= 4:
        return "PARTIAL_AGENT_ARCHITECTURE"
    return "TOOL_OR_REACTIVE_SYSTEM"
