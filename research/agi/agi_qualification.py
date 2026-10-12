from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class AGIStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    PRE_AGI = "PRE_AGI"
    AGI_CANDIDATE_NOT_CERTIFIED = "AGI_CANDIDATE_NOT_CERTIFIED"
    COMPETENT_AGI = "COMPETENT_AGI"

REQUIRED_CLASSES = (
    "generality",
    "novel_skill_acquisition",
    "metacognition",
    "causal_world_model",
    "long_horizon_reliability",
    "tool_computer_use",
    "cross_domain_transfer",
    "online_adaptation",
    "calibration_epistemic_integrity",
    "governed_autonomy",
)

REQUIRED_INDEPENDENT_EVIDENCE = (
    "human_referenced_generality",
    "novel_interactive_learning",
    "long_horizon",
    "real_computer_tool_use",
)

@dataclass(frozen=True)
class CapabilityClassResult:
    name: str
    passed: bool
    human_referenced: bool
    independent: bool
    evidence_refs: tuple[str, ...] = ()
    notes: str = ""

@dataclass
class AGICandidate:
    candidate_id: str
    results: list[CapabilityClassResult] = field(default_factory=list)
    independent_evidence_classes: set[str] = field(default_factory=set)
    consciousness_claimed: bool = False

    def result_map(self) -> dict[str, CapabilityClassResult]:
        return {r.name:r for r in self.results}

def qualify(candidate: AGICandidate) -> tuple[AGIStatus, list[str]]:
    reasons: list[str] = []
    results = candidate.result_map()

    for required in REQUIRED_CLASSES:
        result = results.get(required)
        if result is None:
            reasons.append(f"missing required class: {required}")
        elif not result.passed:
            reasons.append(f"failed required class: {required}")

    for evidence_class in REQUIRED_INDEPENDENT_EVIDENCE:
        if evidence_class not in candidate.independent_evidence_classes:
            reasons.append(f"missing independent evidence: {evidence_class}")

    generality = results.get("generality")
    if generality is not None:
        if not generality.human_referenced:
            reasons.append("generality is not human referenced")
        if not generality.independent:
            reasons.append("generality is not independently evaluated")

    if reasons:
        passed_count = sum(
            1 for required in REQUIRED_CLASSES
            if results.get(required) is not None and results[required].passed
        )
        if passed_count >= 6:
            return AGIStatus.AGI_CANDIDATE_NOT_CERTIFIED, reasons
        return AGIStatus.PRE_AGI, reasons

    return AGIStatus.COMPETENT_AGI, []

def benchmark_saturation_is_not_agi(
    one_benchmark_score: float,
    independent_broad_generality_passed: bool,
) -> bool:
    if not 0 <= one_benchmark_score <= 1:
        raise ValueError("score must be in [0,1]")
    return one_benchmark_score >= 0.99 and not independent_broad_generality_passed
