from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

class ChangeType(str, Enum):
    CORRECTION = "CORRECTION"
    REVISION = "REVISION"
    RETRACTION = "RETRACTION"
    SUPERSEDED = "SUPERSEDED"
    SAFETY_UPDATE = "SAFETY_UPDATE"
    ACTIVE_EXPLOITATION = "ACTIVE_EXPLOITATION"
    SCHEMA_CHANGE = "SCHEMA_CHANGE"
    METADATA_UPDATE = "METADATA_UPDATE"
    ASSUMPTION_INVALIDATED = "ASSUMPTION_INVALIDATED"

class ImpactState(str, Enum):
    POTENTIALLY_AFFECTED = "POTENTIALLY_AFFECTED"
    AFFECTED = "AFFECTED"
    NOT_AFFECTED = "NOT_AFFECTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    REVALIDATED = "REVALIDATED"
    WITHDRAWN = "WITHDRAWN"

@dataclass(frozen=True)
class EvidenceChangeEvent:
    event_id: str
    source_node: str
    change_type: ChangeType
    prior_fingerprint: str | None
    new_fingerprint: str | None
    source_ref: str
    changed_fields: tuple[str, ...] = ()
    note: str | None = None

@dataclass
class ImpactAssessment:
    event_id: str
    claim_id: str
    state: ImpactState
    rationale: str
    evidence_refs: list[str] = field(default_factory=list)
    assessed_by: str | None = None

    def validate(self) -> None:
        if self.state in {
            ImpactState.NOT_AFFECTED,
            ImpactState.REVALIDATED,
            ImpactState.AFFECTED,
            ImpactState.WITHDRAWN,
        } and not self.evidence_refs:
            raise ValueError(
                f"{self.state.value} requires evidence_refs"
            )
        if not self.rationale.strip():
            raise ValueError("rationale is required")

def initial_impact_assessments(
    event: EvidenceChangeEvent,
    descendant_claim_ids: Iterable[str],
) -> list[ImpactAssessment]:
    return [
        ImpactAssessment(
            event_id=event.event_id,
            claim_id=claim_id,
            state=ImpactState.POTENTIALLY_AFFECTED,
            rationale="Material ancestor changed; applicability not yet assessed.",
        )
        for claim_id in descendant_claim_ids
    ]

def prime_action(assessment: ImpactAssessment) -> str:
    assessment.validate() if assessment.state not in {
        ImpactState.POTENTIALLY_AFFECTED,
        ImpactState.UNDER_REVIEW,
    } else None

    if assessment.state in {
        ImpactState.POTENTIALLY_AFFECTED,
        ImpactState.UNDER_REVIEW,
        ImpactState.AFFECTED,
        ImpactState.WITHDRAWN,
    }:
        return "BLOCK_OR_QUARANTINE"
    if assessment.state in {
        ImpactState.NOT_AFFECTED,
        ImpactState.REVALIDATED,
    }:
        return "ALLOW_WITH_AUDIT_TRAIL"
    raise ValueError(f"unhandled impact state {assessment.state}")

def summarize_event(
    assessments: Iterable[ImpactAssessment],
) -> dict[str, int]:
    counts = {state.value: 0 for state in ImpactState}
    for item in assessments:
        counts[item.state.value] += 1
    return counts

def crossmark_status_to_change_type(status: str) -> ChangeType | None:
    value = status.strip().lower()
    if "retract" in value:
        return ChangeType.RETRACTION
    if "correct" in value:
        return ChangeType.CORRECTION
    if "update" in value or "revision" in value:
        return ChangeType.REVISION
    return None

def w3c_prov_relation(change_type: ChangeType) -> str:
    if change_type in {
        ChangeType.RETRACTION,
        ChangeType.SUPERSEDED,
        ChangeType.ASSUMPTION_INVALIDATED,
    }:
        return "prov:wasInvalidatedBy"
    return "prov:wasRevisionOf"

def vex_like_status(state: ImpactState) -> str:
    mapping = {
        ImpactState.AFFECTED: "affected",
        ImpactState.NOT_AFFECTED: "not_affected",
        ImpactState.REVALIDATED: "fixed_or_revalidated",
        ImpactState.POTENTIALLY_AFFECTED: "under_investigation",
        ImpactState.UNDER_REVIEW: "under_investigation",
        ImpactState.WITHDRAWN: "affected_withdrawn",
    }
    return mapping[state]
