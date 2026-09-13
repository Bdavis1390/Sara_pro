"""Claims-control guard for external QCRYPTO review receipts.

This module validates review metadata only. It does not perform cryptanalysis,
key recovery, wallet interaction, transaction signing, or network operations.
Its purpose is to prevent an incomplete or unattributed review from being
represented as independent validation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


REQUIRED_QUESTIONS = (
    "evidence_classes_separated",
    "source_provenance_preserved",
    "forward_looking_evidence_not_promoted",
    "implementation_distinguished_from_certification",
    "migration_treated_as_systems_problem",
    "exact_commit_reproduced",
    "limitations_clearly_stated",
)


@dataclass(frozen=True)
class ReviewReceipt:
    reviewer_identity: str
    reviewer_organization: str
    exact_commit: str
    environment: str
    review_date: str
    question_results: dict[str, bool]
    discrepancies: tuple[str, ...] = ()
    supported_claims: tuple[str, ...] = ()
    excluded_claims: tuple[str, ...] = ()
    attributable_record: str = ""


@dataclass(frozen=True)
class ReviewAssessment:
    state: str
    complete: bool
    missing_fields: tuple[str, ...]
    failed_questions: tuple[str, ...]
    warranted_label: str

    def to_dict(self) -> dict:
        return asdict(self)


def _blank(value: str) -> bool:
    return not value or not value.strip()


def assess_review(receipt: ReviewReceipt) -> ReviewAssessment:
    """Classify a reviewer receipt conservatively.

    INDEPENDENT_REPRODUCTION_RECORDED is available only when the reviewer is
    attributable, the exact commit and environment are recorded, all required
    review questions are present and pass, and an attributable review record is
    supplied. This does not imply certification, endorsement, or adoption.
    """

    missing: list[str] = []
    for field_name, value in (
        ("reviewer_identity", receipt.reviewer_identity),
        ("reviewer_organization", receipt.reviewer_organization),
        ("exact_commit", receipt.exact_commit),
        ("environment", receipt.environment),
        ("review_date", receipt.review_date),
        ("attributable_record", receipt.attributable_record),
    ):
        if _blank(value):
            missing.append(field_name)

    absent_questions = [q for q in REQUIRED_QUESTIONS if q not in receipt.question_results]
    missing.extend(f"question:{q}" for q in absent_questions)

    failed = tuple(
        q for q in REQUIRED_QUESTIONS
        if q in receipt.question_results and receipt.question_results[q] is not True
    )

    complete = not missing and not failed
    if complete:
        state = "INDEPENDENT_REPRODUCTION_RECORDED"
        label = "INDEPENDENTLY REPRODUCED — METHODOLOGY/SOFTWARE BEHAVIOR ONLY"
    elif receipt.reviewer_identity and receipt.exact_commit:
        state = "EXTERNAL_REVIEW_INCOMPLETE"
        label = "EXTERNAL REVIEW IN PROGRESS"
    else:
        state = "NO_VALID_EXTERNAL_REVIEW"
        label = "NOT INDEPENDENTLY VALIDATED"

    return ReviewAssessment(
        state=state,
        complete=complete,
        missing_fields=tuple(missing),
        failed_questions=failed,
        warranted_label=label,
    )
