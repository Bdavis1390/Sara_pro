"""Paired, label-held-out comparison of BAROS proposals and external risk scores.

All results describe *research decision labels*, NOT a probability of harm,
clinical plan accuracy, treatment benefit, or a named vendor's performance.
An independent evaluator must own challenge creation, labels and comparator.
Developer-authored fixtures only until then.
"""

from __future__ import annotations

from dataclasses import dataclass
import hmac
from typing import Mapping

from .blinded_challenge import (
    BlindPrediction, BlindedSubmission, _digest, _submission_payload,
)
from .locked_risk_coverage import (
    LockedScoreSubmission, OperatingPoint, score_external_after_unblinding,
)
from .phase1_evaluation import Rate, _rate

LABELS = frozenset({"qualified_trigger", "disqualified_trigger"})
ACTIONS = frozenset({
    "NO_ADAPTATION", "PROPOSE_REOPTIMIZATION",
    "HOLD_LAST_VALID", "FALLBACK_STANDARD",
})


@dataclass(frozen=True)
class PairedOperatingPoint:
    comparator: OperatingPoint
    baros_false_proceed: Rate
    baros_eligible_recall: Rate
    baros_coverage: Rate
    comparator_only_false_proceeds: int
    baros_only_false_proceeds: int
    comparator_only_eligible_proposals: int
    baros_only_eligible_proposals: int


@dataclass(frozen=True)
class PairedComparisonReport:
    protocol_id: str
    challenge_sha256: str
    baros_submission_sha256: str
    comparator_commitment_sha256: str
    held_out_labels_sha256: str
    qualified_cases: int
    disqualified_cases: int
    operating_points: tuple[PairedOperatingPoint, ...]


def compare_frozen_research_submissions(
    baros: BlindedSubmission,
    comparator: LockedScoreSubmission,
    held_out_labels: Mapping[str, str],
) -> PairedComparisonReport:
    """Score both frozen submissions on exactly the same challenge/case IDs.

    This method intentionally requires a separately frozen *trigger-only*
    study cohort. No-trigger cases must be studied in a separate preregistered
    stratum, not discarded based on predictions or labels after unblinding.

    The SHA-256 commitments do not authenticate identity or show that the
    source laboratory is independent. They bind caller-provided records only.
    """
    if not isinstance(baros, BlindedSubmission):
        raise ValueError("BAROS input must be a BlindedSubmission")
    if not isinstance(comparator, LockedScoreSubmission):
        raise ValueError("comparator input must be a LockedScoreSubmission")
    if (
        baros.protocol_id != comparator.protocol_id
        or comparator.challenge_sha256 is None
        or not hmac.compare_digest(
            baros.challenge_sha256, comparator.challenge_sha256
        )
    ):
        raise ValueError("same protocol and explicit challenge digest required")
    if not hmac.compare_digest(
        _digest(_submission_payload(baros)), baros.submission_sha256
    ):
        raise ValueError("BAROS submission integrity mismatch")
    predictions = tuple(baros.results)
    if not predictions or any(
        not isinstance(p, BlindPrediction)
        or not isinstance(p.case_id, str)
        or not p.case_id.strip()
        or p.action not in ACTIONS
        or type(p.triggered) is not bool
        or type(p.proposal_allowed) is not bool
        or p.treatment_authority is not False
        for p in predictions
    ):
        raise ValueError("invalid BAROS prediction record or treatment authority")
    case_ids = [p.case_id for p in predictions]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("duplicate BAROS case identifiers")
    risk_ids = [r.case_id for r in comparator.risk_scores]
    if set(case_ids) != set(risk_ids):
        raise ValueError("comparator and BAROS case populations differ")

    labels = dict(held_out_labels)
    if set(labels) != set(case_ids):
        raise ValueError("reference labels must cover the same frozen cases")
    if set(labels.values()) != LABELS:
        raise ValueError("require qualified and disqualified triggered strata")

    # This validates the external locked scores, thresholds, exact labels,
    # and score commitment before any comparative calculation.
    external = score_external_after_unblinding(comparator, labels)
    proposals = {p.case_id: p.proposal_allowed for p in predictions}
    good_ids = {cid for cid, truth in labels.items() if truth == "qualified_trigger"}
    bad_ids = {cid for cid, truth in labels.items() if truth == "disqualified_trigger"}
    good_count, bad_count = len(good_ids), len(bad_ids)
    total_count = len(labels)
    baros_bad_count = sum(proposals[cid] for cid in bad_ids)
    baros_good_count = sum(proposals[cid] for cid in good_ids)
    baros_covered_count = baros_good_count + baros_bad_count
    risk_lookup = {r.case_id: r.risk for r in comparator.risk_scores}

    points = []
    for external_point in external.operating_points:
        accepted = {
            cid for cid, risk in risk_lookup.items()
            if risk <= external_point.risk_threshold
        }
        points.append(PairedOperatingPoint(
            comparator=external_point,
            baros_false_proceed=_rate(baros_bad_count, bad_count),
            baros_eligible_recall=_rate(baros_good_count, good_count),
            baros_coverage=_rate(baros_covered_count, total_count),
            comparator_only_false_proceeds=sum(
                cid in accepted and not proposals[cid] for cid in bad_ids
            ),
            baros_only_false_proceeds=sum(
                proposals[cid] and cid not in accepted for cid in bad_ids
            ),
            comparator_only_eligible_proposals=sum(
                cid in accepted and not proposals[cid] for cid in good_ids
            ),
            baros_only_eligible_proposals=sum(
                proposals[cid] and cid not in accepted for cid in good_ids
            ),
        ))
    return PairedComparisonReport(
        protocol_id=baros.protocol_id,
        challenge_sha256=baros.challenge_sha256,
        baros_submission_sha256=baros.submission_sha256,
        comparator_commitment_sha256=comparator.commitment_sha256,
        held_out_labels_sha256=external.held_out_labels_sha256,
        qualified_cases=good_count,
        disqualified_cases=bad_count,
        operating_points=tuple(points),
    )
