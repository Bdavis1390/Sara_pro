"""Protocol-locked external uncertainty-score benchmarking for BAROS research.

Independent baseline scores must come from an evaluator's actual method.
This module DOES NOT implement MC dropout, entropy, mutual information,
biomarker inference or a published paper's classifier. It only freezes
externally supplied risk scores / thresholds before held-out reference labels
are released, then computes descriptive risk-versus-coverage results.

SYNTHETIC / NON-CLINICAL until an authorized evaluator supplies real data.
No treatment authority is conferred.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import math
from typing import Mapping, Sequence

from .phase1_evaluation import Rate, _rate

ALLOWED_TRUTH = frozenset({"qualified_trigger", "disqualified_trigger"})


def _commit(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class RiskScore:
    case_id: str
    risk: float


@dataclass(frozen=True)
class LockedScoreSubmission:
    protocol_id: str
    comparator_id: str
    risk_scores: tuple[RiskScore, ...]
    thresholds: tuple[float, ...]
    commitment_sha256: str


@dataclass(frozen=True)
class OperatingPoint:
    risk_threshold: float
    proposal_coverage: Rate
    critical_false_proceed: Rate
    eligible_proposal_recall: Rate
    selective_failure_rate: Rate | None


@dataclass(frozen=True)
class RiskCoverageReport:
    protocol_id: str
    comparator_id: str
    cases: int
    disqualified: int
    eligible: int
    locked_commitment_sha256: str
    held_out_labels_sha256: str
    operating_points: tuple[OperatingPoint, ...]


def _submission_body(submission: LockedScoreSubmission) -> dict[str, object]:
    return {
        "protocol_id": submission.protocol_id,
        "comparator_id": submission.comparator_id,
        "risk_scores": [asdict(x) for x in submission.risk_scores],
        "thresholds": list(submission.thresholds),
    }


def lock_external_risk_scores(
    scores: Sequence[RiskScore],
    *,
    thresholds: Sequence[float],
    protocol_id: str,
    comparator_id: str,
) -> LockedScoreSubmission:
    """Commit risk scores and decision thresholds BEFORE evaluator unblinding."""
    for name, value in (("protocol_id", protocol_id), ("comparator_id", comparator_id)):
        if not isinstance(value, str) or not (0 < len(value.strip()) <= 96):
            raise ValueError(f"{name} must be a non-empty, short identifier")
    scores = tuple(scores)
    if not 1 <= len(scores) <= 10_000:
        raise ValueError("risk score list must contain 1..10000 cases")
    if any(not isinstance(x, RiskScore) for x in scores):
        raise ValueError("risk score entries must be RiskScore instances")
    names = [x.case_id for x in scores]
    if len(set(names)) != len(names) or any(not isinstance(x, str) or not x.strip() for x in names):
        raise ValueError("risk-score case IDs must be non-empty and unique")
    for score in scores:
        if isinstance(score.risk, bool) or not isinstance(score.risk, (int, float)):
            raise ValueError("risk values must be finite numbers within [0, 1]")
        if not math.isfinite(score.risk) or not 0.0 <= score.risk <= 1.0:
            raise ValueError("risk values must be finite numbers within [0, 1]")
    thresholds = tuple(thresholds)
    if not thresholds or len(thresholds) > 1001:
        raise ValueError("require a bounded list of predeclared thresholds")
    if any(isinstance(x, bool) or not isinstance(x, (int, float))
           or not math.isfinite(x) or not 0.0 <= x <= 1.0 for x in thresholds):
        raise ValueError("thresholds must be finite and within [0, 1]")
    if len(set(thresholds)) != len(thresholds) or tuple(sorted(thresholds)) != thresholds:
        raise ValueError("thresholds must be strictly ascending with no duplicates")
    stub = LockedScoreSubmission(protocol_id, comparator_id, scores, thresholds, "")
    return LockedScoreSubmission(
        protocol_id, comparator_id, scores, thresholds, _commit(_submission_body(stub))
    )


def score_external_after_unblinding(
    submission: LockedScoreSubmission,
    held_out_labels: Mapping[str, str],
) -> RiskCoverageReport:
    """Score evaluator-held labels at the already committed thresholds.

    This function must not be used to select thresholds on a held-out dataset.
    A preexisting SHA-256 digest is NOT a signature or evidence of independent
    label custody. Risk here means *disqualified reference case among proposals*,
    not probability of patient harm.
    """
    if not isinstance(submission, LockedScoreSubmission):
        raise ValueError("expected LockedScoreSubmission")
    try:
        expected_digest = _commit(_submission_body(submission))
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("invalid locked submission") from exc
    if not hmac.compare_digest(expected_digest, submission.commitment_sha256):
        raise ValueError("locked score commitment mismatch")
    # Re-run all score/threshold validation to reject forged objects that
    # happen to carry a self-consistent digest.
    reconstructed = lock_external_risk_scores(
        submission.risk_scores,
        thresholds=submission.thresholds,
        protocol_id=submission.protocol_id,
        comparator_id=submission.comparator_id,
    )
    if not hmac.compare_digest(reconstructed.commitment_sha256, submission.commitment_sha256):
        raise ValueError("invalid locked score fields")

    labels = dict(held_out_labels)
    if set(labels) != {x.case_id for x in submission.risk_scores}:
        raise ValueError("held-out labels must cover exactly the frozen cases")
    if set(labels.values()) != ALLOWED_TRUTH:
        raise ValueError("require both qualified and disqualified trigger strata")
    disqualified = sum(x == "disqualified_trigger" for x in labels.values())
    eligible = len(labels) - disqualified
    outputs = []
    for threshold in submission.thresholds:
        accepted = [x for x in submission.risk_scores if x.risk <= threshold]
        accepted_disqualified = sum(labels[x.case_id] == "disqualified_trigger" for x in accepted)
        accepted_qualified = len(accepted) - accepted_disqualified
        outputs.append(OperatingPoint(
            risk_threshold=threshold,
            proposal_coverage=_rate(len(accepted), len(labels)),
            critical_false_proceed=_rate(accepted_disqualified, disqualified),
            eligible_proposal_recall=_rate(accepted_qualified, eligible),
            # When nothing is proposed, selective risk is undefined, not zero.
            selective_failure_rate=(
                _rate(accepted_disqualified, len(accepted)) if accepted else None
            ),
        ))
    return RiskCoverageReport(
        protocol_id=submission.protocol_id,
        comparator_id=submission.comparator_id,
        cases=len(labels),
        disqualified=disqualified,
        eligible=eligible,
        locked_commitment_sha256=submission.commitment_sha256,
        held_out_labels_sha256=_commit(sorted(labels.items())),
        operating_points=tuple(outputs),
    )
