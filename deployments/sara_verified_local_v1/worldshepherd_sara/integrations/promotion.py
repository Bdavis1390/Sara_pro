from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence


REQUIRED_EVIDENCE_CATEGORIES: tuple[str, ...] = (
    "runtime_version_inventory",
    "configuration_digest",
    "bounded_interface_test",
    "telemetry_and_provenance",
    "failure_or_degraded_behavior",
    "operator_authorization",
)


@dataclass(frozen=True)
class PromotionReadinessAssessment:
    surface: str
    submitted_claim_status: str
    ready_for_human_review: bool
    auto_promotion_allowed: bool
    missing_categories: tuple[str, ...]
    evidence_ref_count: int
    decision: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_promotion_readiness(
    *,
    surface: str,
    submitted_claim_status: str,
    evidence_by_category: Mapping[str, Sequence[str]],
) -> PromotionReadinessAssessment:
    """Assess whether an NVIDIA evidence package is complete enough for human review.

    This function never promotes a capability and never treats completeness as
    validation. It only determines whether all required evidence categories have
    at least one non-empty reference. Explicit human/authority review is always
    required after this gate.
    """

    if not surface.strip():
        raise ValueError("surface must not be empty")
    if not submitted_claim_status.strip():
        raise ValueError("submitted_claim_status must not be empty")

    normalized: dict[str, tuple[str, ...]] = {}
    for category in REQUIRED_EVIDENCE_CATEGORIES:
        refs = evidence_by_category.get(category, ())
        normalized[category] = tuple(ref.strip() for ref in refs if ref.strip())

    missing = tuple(
        category for category in REQUIRED_EVIDENCE_CATEGORIES if not normalized[category]
    )
    ref_count = sum(len(refs) for refs in normalized.values())
    ready = not missing

    return PromotionReadinessAssessment(
        surface=surface.strip(),
        submitted_claim_status=submitted_claim_status.strip(),
        ready_for_human_review=ready,
        auto_promotion_allowed=False,
        missing_categories=missing,
        evidence_ref_count=ref_count,
        decision=(
            "READY_FOR_HUMAN_REVIEW"
            if ready
            else "INCOMPLETE_EVIDENCE_PACKAGE"
        ),
    )
