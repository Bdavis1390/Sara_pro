from __future__ import annotations
from dataclasses import dataclass

from competence_evidence import CompetenceLedger
from agi_qualification import AGIStatus

DEFAULT_TASK_FAMILIES = {
    "quantitative_reasoning",
    "science",
    "coding",
    "research_information_synthesis",
    "communication_writing",
    "planning_operations",
    "data_analysis",
    "legal_administrative_reasoning",
    "visual_multimodal_reasoning",
    "novel_skill_acquisition",
}

@dataclass(frozen=True)
class InternalGateResult:
    metacognition: bool
    identifiability_awareness: bool
    epistemic_action: bool
    causal_world_model: bool
    cross_domain_transfer: bool
    online_adaptation: bool
    calibration: bool
    governed_autonomy: bool
    state_continuity: bool
    representation_shift: bool

    def all_pass(self) -> bool:
        return all(self.__dict__.values())

@dataclass(frozen=True)
class QualificationReport:
    status: AGIStatus
    family_coverage: float
    missing: tuple[str, ...]

def run_qualification(
    ledger: CompetenceLedger,
    candidate_system: str,
    internal: InternalGateResult,
    preregistered_families: set[str] | None = None,
    project_most_threshold: float = 0.60,
) -> QualificationReport:
    families = preregistered_families or DEFAULT_TASK_FAMILIES
    coverage = ledger.family_coverage(candidate_system, families)
    external = ledger.external_gate_summary(candidate_system)
    missing: list[str] = []

    # DeepMind says "most"; Worldshepherd adopts 60% as a stricter,
    # explicit project policy rather than silently choosing 50%+epsilon.
    if coverage < project_most_threshold:
        missing.append(
            f"broad human-referenced family coverage {coverage:.1%} < "
            f"{project_most_threshold:.0%}"
        )

    for key, passed in external.items():
        if not passed:
            missing.append(f"missing external gate: {key}")

    if not internal.all_pass():
        for key, passed in internal.__dict__.items():
            if not passed:
                missing.append(f"failed internal gate: {key}")

    if missing:
        if coverage >= 0.40 and sum(internal.__dict__.values()) >= 6:
            status = AGIStatus.AGI_CANDIDATE_NOT_CERTIFIED
        else:
            status = AGIStatus.PRE_AGI
        return QualificationReport(status, coverage, tuple(missing))

    return QualificationReport(
        AGIStatus.COMPETENT_AGI,
        coverage,
        (),
    )
