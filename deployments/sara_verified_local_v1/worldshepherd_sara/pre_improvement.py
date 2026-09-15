from __future__ import annotations

from typing import Iterable

from .improvement_cycle import (
    ImprovementProposal,
    ImprovementRisk,
    ImprovementState,
    ImprovementTriggerKind,
)
from .qualification import (
    CapabilityStatus,
    DemandClass,
    RequirementDeltaRecord,
    canonical_digest,
)


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _stable_requirement_improvement_id(
    requirement: RequirementDeltaRecord,
    created_utc: str,
) -> str:
    year = created_utc[:4]
    if len(year) != 4 or not year.isdigit():
        raise ValueError("created_utc must begin with a four-digit year")
    material = {
        "requirement_delta_id": requirement.requirement_delta_id,
        "statement": requirement.statement,
        "source_url": requirement.source.url,
        "created_year": year,
    }
    digest_hex = canonical_digest(material).split(":", 1)[1]
    numeric_suffix = str(int(digest_hex[:12], 16))
    return f"WS-IR-{year}-{numeric_suffix}"


def pre_to_improvement(
    requirement: RequirementDeltaRecord,
    *,
    created_utc: str,
    baseline_artifacts: Iterable[str] = (),
    additional_required_tests: Iterable[str] = (),
) -> ImprovementProposal:
    """Translate a PRE requirement delta into a governed WS-RI proposal.

    PRE demand classification is preserved as context only. Confirmed demand,
    emerging demand, and Worldshepherd forecasts do not themselves promote
    capability maturity or authorize implementation.
    """

    baseline_status = list(dict.fromkeys(requirement.capability_status))
    if not baseline_status:
        baseline_status = [CapabilityStatus.NOT_CURRENTLY_CLAIMED]

    lanes = _dedupe([*requirement.affected_lanes, "PRE", "WS-RI"])
    sources = _dedupe(
        [
            requirement.requirement_delta_id,
            requirement.source.url,
            requirement.source.solicitation_or_topic or "",
        ]
    )
    required_tests = _dedupe(
        [
            f"{requirement.requirement_delta_id}:source-evidence-gate",
            f"{requirement.requirement_delta_id}:claims-boundary-gate",
            *requirement.experiment_or_demonstration_needed,
            *additional_required_tests,
        ]
    )

    risks = [
        "Demand evidence does not establish Worldshepherd capability, readiness, certification, or physical performance.",
        "A requirement may change, be superseded, or apply differently to a specific program or integration context.",
    ]
    risk_level = ImprovementRisk.MODERATE

    if not requirement.capture_ready():
        risks.append(
            "The PRE source is not capture-ready and requires source resolution before consequential use."
        )
        risk_level = ImprovementRisk.HIGH

    if requirement.demand_class == DemandClass.WORLDSHEPHERD_FORECAST:
        risks.append(
            "Worldshepherd forecast is a preparation signal only and is not evidence that an external customer requirement exists."
        )

    if requirement.partner_needed:
        risks.append(
            "Partner need is unresolved; partner interest, validation, eligibility, and performance are not established by this record."
        )

    gap_text = "; ".join(requirement.missing_capability)
    if gap_text:
        proposed_change = (
            "Evaluate and close the following PRE capability gaps only through qualified, authorized changes: "
            f"{gap_text}. Requirement context: {requirement.statement}"
        )
    else:
        proposed_change = (
            "Evaluate the PRE requirement delta and define any evidence-backed Worldshepherd change needed to address it: "
            f"{requirement.statement}"
        )

    success_metrics = _dedupe(requirement.evidence_target)
    if not success_metrics:
        success_metrics = [
            "All required validation tests return PASS.",
            "The requirement remains traceable to its source and PRE record.",
            "No claims-boundary violation or unauthorized external execution occurs.",
        ]

    assumptions = [
        f"PRE demand class remains {requirement.demand_class.value} unless superseded by a newer requirement record.",
        "Source status and capability status remain separate evidence dimensions.",
        "Existing ECHO, TEVV, PRIME, and configuration-custody controls remain authoritative.",
    ]
    if requirement.claims_boundary:
        assumptions.append(
            "The PRE claims boundary remains binding: "
            + " | ".join(requirement.claims_boundary)
        )

    return ImprovementProposal(
        improvement_id=_stable_requirement_improvement_id(requirement, created_utc),
        trigger_kind=ImprovementTriggerKind.REQUIREMENT_DELTA,
        title=f"PRE improvement candidate: {requirement.requirement_delta_id}",
        source_refs=sources,
        affected_lanes=lanes,
        baseline_artifacts=_dedupe(baseline_artifacts),
        baseline_capability_status=baseline_status,
        target_capability_status=None,
        proposed_change=proposed_change,
        expected_benefit=(
            "Convert a PRE requirement gap into a traceable, testable improvement path without confusing demand evidence with capability evidence."
        ),
        assumptions=assumptions,
        risks=risks,
        risk_level=risk_level,
        required_tests=required_tests,
        success_metrics=success_metrics,
        negative_evidence=[],
        reversible=True,
        generated_by="PRE->WS-RI",
        created_utc=created_utc,
        state=ImprovementState.PROPOSED,
        requested_claim_promotion=False,
        requested_external_execution=False,
    )
