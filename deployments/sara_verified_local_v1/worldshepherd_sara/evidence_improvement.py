from __future__ import annotations

from typing import Iterable

from .improvement_cycle import (
    ImprovementProposal,
    ImprovementRisk,
    ImprovementState,
    ImprovementTriggerKind,
)
from .qualification import (
    QualificationEvidenceRecord,
    ResultStatus,
    ReviewStatus,
    canonical_digest,
)


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _stable_evidence_improvement_id(
    record: QualificationEvidenceRecord,
    created_utc: str,
) -> str:
    year = created_utc[:4]
    if len(year) != 4 or not year.isdigit():
        raise ValueError("created_utc must begin with a four-digit year")
    material = {
        "qualification_id": record.qualification_id,
        "requirement_id": record.requirement_id,
        "result": record.result.value,
        "created_year": year,
    }
    digest_hex = canonical_digest(material).split(":", 1)[1]
    numeric_suffix = str(int(digest_hex[:12], 16))
    return f"WS-IR-{year}-{numeric_suffix}"


def evidence_to_improvement(
    record: QualificationEvidenceRecord,
    *,
    created_utc: str,
    affected_lanes: Iterable[str] = (),
    baseline_artifacts: Iterable[str] = (),
    additional_required_tests: Iterable[str] = (),
) -> ImprovementProposal:
    """Translate qualification/TEVV evidence into a governed WS-RI proposal.

    A PASS remains evidence for the tested scope only. A FAIL or INCONCLUSIVE
    result creates a remediation/uncertainty candidate but does not authorize a
    fix, invalidate unrelated evidence, or promote any capability claim.
    """

    if record.result == ResultStatus.FAIL:
        trigger = ImprovementTriggerKind.FAILURE
        risk_level = ImprovementRisk.HIGH
        action_text = (
            "Investigate and remediate the failed qualification result through a reversible, "
            "re-tested change path."
        )
    elif record.result == ResultStatus.INCONCLUSIVE:
        trigger = ImprovementTriggerKind.TEST_RESULT
        risk_level = ImprovementRisk.MODERATE
        action_text = (
            "Resolve the inconclusive qualification result by reducing uncertainty and repeating "
            "the required test under a controlled configuration."
        )
    else:
        trigger = ImprovementTriggerKind.TEST_RESULT
        risk_level = ImprovementRisk.LOW
        action_text = (
            "Evaluate whether the passing qualification result warrants any bounded baseline update, "
            "while preserving the exact tested scope and configuration."
        )

    lanes = _dedupe([*affected_lanes, "PRIME-TEVV", "ECHO", "WS-RI"])
    sources = _dedupe(
        [
            record.qualification_id,
            record.requirement_id,
            record.test_id,
            record.software_commit or "",
        ]
    )

    required_tests = [
        f"{record.qualification_id}:evidence-review-gate",
        f"{record.qualification_id}:regression-gate",
    ]
    if record.result == ResultStatus.FAIL:
        required_tests.append(f"{record.qualification_id}:root-cause-gate")
    elif record.result == ResultStatus.INCONCLUSIVE:
        required_tests.append(f"{record.qualification_id}:uncertainty-resolution-gate")
    required_tests = _dedupe([*required_tests, *additional_required_tests])

    risks = [
        "Qualification evidence applies only to the recorded test scope, configuration, environment, inputs, and uncertainty.",
        "This translation does not establish broader readiness, certification, partner validation, or physical performance beyond the evidence record.",
    ]
    if record.review.status == ReviewStatus.UNREVIEWED:
        risks.append("Qualification evidence has not yet received recorded human review.")
    if record.result == ResultStatus.FAIL:
        risks.append("A failed required test may indicate a regression, invalid assumption, configuration defect, or unmodeled condition.")
    if record.result == ResultStatus.INCONCLUSIVE:
        risks.append("Uncertainty is unresolved; no directional capability conclusion should be drawn from the result.")

    success_metrics = [
        "Required remediation or uncertainty-resolution gates return PASS.",
        "The original qualification record remains traceable and unmodified.",
        "No unrelated capability state or claim is promoted from the result.",
        "Any resulting configuration change is separately authorized and regression-tested.",
    ]

    return ImprovementProposal(
        improvement_id=_stable_evidence_improvement_id(record, created_utc),
        trigger_kind=trigger,
        title=f"Qualification feedback: {record.qualification_id}",
        source_refs=sources,
        affected_lanes=lanes,
        baseline_artifacts=_dedupe(baseline_artifacts),
        baseline_capability_status=[record.capability_status],
        target_capability_status=None,
        proposed_change=(
            f"{action_text} Requirement={record.requirement_id}; test={record.test_id}; "
            f"result={record.result.value}."
        ),
        expected_benefit=(
            "Feed measured qualification results back into Worldshepherd change control without erasing failures, expanding scope, or inflating maturity."
        ),
        assumptions=[
            "The qualification record digest inputs accurately identify the tested environment and configuration.",
            "Existing evidence lifecycle, ECHO custody, PRIME authorization, and configuration custody remain authoritative.",
        ],
        risks=risks,
        risk_level=risk_level,
        required_tests=required_tests,
        success_metrics=success_metrics,
        negative_evidence=[dict(item) for item in record.negative_evidence],
        reversible=True,
        generated_by="QE/TEVV->WS-RI",
        created_utc=created_utc,
        state=ImprovementState.PROPOSED,
        requested_claim_promotion=False,
        requested_external_execution=False,
    )
