"""Evidence-gated readiness states for Worldshepherd Federal PQC mapping.

The states in this module describe Worldshepherd engineering evidence only.
They do not represent Federal compliance, certification, authorization, award
eligibility, or government approval.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlEvidence:
    requirement_id: str
    mapped: bool = False
    implementation_artifact: bool = False
    internal_test_passed: bool = False
    independent_review_recorded: bool = False


@dataclass(frozen=True)
class ReadinessResult:
    requirement_id: str
    state: str
    warranted_claim: str
    excluded_claim: str = "FEDERAL_COMPLIANCE_NOT_ESTABLISHED"


def assess_control(evidence: ControlEvidence) -> ReadinessResult:
    if evidence.independent_review_recorded:
        if not (evidence.mapped and evidence.implementation_artifact and evidence.internal_test_passed):
            return ReadinessResult(
                evidence.requirement_id,
                "INVALID_EVIDENCE_SEQUENCE",
                "Evidence sequence is incomplete; do not promote the control.",
            )
        return ReadinessResult(
            evidence.requirement_id,
            "INDEPENDENTLY_REPRODUCED",
            "Independent reproduction of the Worldshepherd control behavior is recorded.",
        )

    if evidence.internal_test_passed:
        if not (evidence.mapped and evidence.implementation_artifact):
            return ReadinessResult(
                evidence.requirement_id,
                "INVALID_EVIDENCE_SEQUENCE",
                "Internal test result lacks the required mapping or implementation artifact.",
            )
        return ReadinessResult(
            evidence.requirement_id,
            "PROVEN_INTERNALLY",
            "Worldshepherd control behavior has a passing internal test at a recorded revision.",
        )

    if evidence.implementation_artifact:
        if not evidence.mapped:
            return ReadinessResult(
                evidence.requirement_id,
                "INVALID_EVIDENCE_SEQUENCE",
                "Implementation artifact is not tied to a mapped requirement.",
            )
        return ReadinessResult(
            evidence.requirement_id,
            "IMPLEMENTED_IN_SOFTWARE",
            "A Worldshepherd implementation artifact exists for the mapped requirement.",
        )

    if evidence.mapped:
        return ReadinessResult(
            evidence.requirement_id,
            "DESIGN_MAPPING",
            "The public requirement is mapped to Worldshepherd responsibilities and evidence targets.",
        )

    return ReadinessResult(
        evidence.requirement_id,
        "UNMAPPED",
        "No Worldshepherd requirement mapping has been recorded.",
    )
