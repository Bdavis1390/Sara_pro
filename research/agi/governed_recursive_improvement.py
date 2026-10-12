from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class PromotionState(str, Enum):
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    SANDBOX_ELIGIBLE = "SANDBOX_ELIGIBLE"
    CANARY_ELIGIBLE = "CANARY_ELIGIBLE"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    PROMOTION_ELIGIBLE = "PROMOTION_ELIGIBLE"
    BLOCKED = "BLOCKED"

GOVERNANCE_ROOTS = {
    "PRIME_AUTHORIZATION",
    "HUMAN_APPROVAL_POLICY",
    "ECHO_AUDIT_INTEGRITY",
    "ROLLBACK_POLICY",
    "CLAIMS_CONTROL",
    "EVIDENCE_INVALIDATION",
    "OCOE_SAFETY_GATE",
}

@dataclass(frozen=True)
class QualityVector:
    performance: float
    generalization: float
    observability: float
    calibration: float
    evidence_integrity: float
    safety: float
    provenance: float
    maintainability: float
    efficiency: float
    rollback_readiness: float

    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0,1]")

@dataclass(frozen=True)
class ImprovementProposal:
    proposal_id: str
    lane: str
    target_component: str
    parent: QualityVector
    predicted_child: QualityVector
    measured_child: QualityVector | None
    evidence_refs: tuple[str, ...]
    benchmark_ref: str | None
    rollback_ref: str | None
    blast_radius_known: bool
    high_consequence: bool
    human_approved: bool = False
    sandboxed: bool = False
    canary_validated: bool = False

def critical_regression(parent: QualityVector, child: QualityVector) -> list[str]:
    parent.validate(); child.validate()
    critical = (
        "observability",
        "calibration",
        "evidence_integrity",
        "safety",
        "provenance",
        "rollback_readiness",
    )
    return [
        name for name in critical
        if getattr(child, name) + 1e-9 < getattr(parent, name)
    ]

def useful_gain(parent: QualityVector, child: QualityVector, minimum: float = 0.01) -> bool:
    parent.validate(); child.validate()
    dimensions = (
        "performance",
        "generalization",
        "observability",
        "calibration",
        "evidence_integrity",
        "safety",
        "provenance",
        "maintainability",
        "efficiency",
        "rollback_readiness",
    )
    return any(
        getattr(child, name) - getattr(parent, name) >= minimum
        for name in dimensions
    )

def promotion_gate(p: ImprovementProposal) -> tuple[PromotionState, list[str]]:
    reasons: list[str] = []
    p.parent.validate()
    p.predicted_child.validate()

    if p.target_component in GOVERNANCE_ROOTS and not p.human_approved:
        return PromotionState.HUMAN_APPROVAL_REQUIRED, [
            "governance-root changes cannot self-promote"
        ]

    if not p.evidence_refs:
        reasons.append("missing evidence lineage")
    if p.benchmark_ref is None:
        reasons.append("missing benchmark or preregistered evaluation")
    if p.rollback_ref is None:
        reasons.append("missing rollback")
    if not p.blast_radius_known:
        reasons.append("unknown dependency blast radius")

    if reasons:
        return PromotionState.BLOCKED, reasons

    if not p.sandboxed:
        return PromotionState.SANDBOX_ELIGIBLE, []

    if p.measured_child is None:
        return PromotionState.BLOCKED, ["no measured child quality vector"]

    regressions = critical_regression(p.parent, p.measured_child)
    if regressions:
        return PromotionState.BLOCKED, [
            "critical regression: " + ", ".join(regressions)
        ]

    if not useful_gain(p.parent, p.measured_child):
        return PromotionState.BLOCKED, ["no material measured improvement"]

    if p.high_consequence and not p.human_approved:
        return PromotionState.HUMAN_APPROVAL_REQUIRED, [
            "high-consequence promotion requires human approval"
        ]

    if not p.canary_validated:
        return PromotionState.CANARY_ELIGIBLE, []

    return PromotionState.PROMOTION_ELIGIBLE, []

def improvement_is_real(
    parent: QualityVector,
    child: QualityVector,
) -> bool:
    return not critical_regression(parent, child) and useful_gain(parent, child)
