"""BAROS evaluator-facing *synthetic* blinded research challenge runner.

Separates challenge observations from held-out reference labels. The evaluator
must independently control fixtures and labels; this library CANNOT establish
independent authorship, clinical ground truth, data rights or signed identity.
Do not put PHI, patient identifiers, confidential scans or vendor secrets here.
No dose calculation or patient treatment authority is implemented.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
from typing import Mapping, Sequence

from .closed_loop import AdaptationThresholds, BiologicalState
from .decision_audit import make_research_decision_audit
from .phase1_evaluation import Rate, _rate


LABELS = frozenset({"qualified_trigger", "disqualified_trigger", "no_trigger"})


def _digest(payload: object) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class BlindCase:
    """No expected result or reference label is present in the input schema."""

    case_id: str
    previous: BiologicalState
    current: BiologicalState
    thresholds: AdaptationThresholds
    source_evidence_sha256: str


@dataclass(frozen=True)
class BlindPrediction:
    case_id: str
    action: str
    triggered: bool
    proposal_allowed: bool
    treatment_authority: bool
    decision_audit_sha256: str


@dataclass(frozen=True)
class BlindedSubmission:
    protocol_id: str
    challenge_sha256: str
    results: tuple[BlindPrediction, ...]
    submission_sha256: str


@dataclass(frozen=True)
class LabeledScore:
    critical_false_proceed: Rate
    eligible_proposal_recall: Rate
    spurious_no_trigger_proposals: Rate
    held_out_labels_sha256: str
    submission_sha256: str


def _submission_payload(submission: BlindedSubmission) -> dict[str, object]:
    return {
        "protocol_id": submission.protocol_id,
        "challenge_sha256": submission.challenge_sha256,
        "results": [asdict(result) for result in submission.results],
    }


def run_blinded_challenge(
    cases: Sequence[BlindCase],
    *,
    protocol_id: str,
) -> BlindedSubmission:
    """Run synthetic research cases WITHOUT ever reading reference labels."""
    if not isinstance(protocol_id, str) or not protocol_id.strip() or len(protocol_id) > 96:
        raise ValueError("protocol_id must be a short, non-empty identifier")
    cases = tuple(cases)
    if not 1 <= len(cases) <= 10_000:
        raise ValueError("challenge must contain between 1 and 10000 cases")
    if any(not isinstance(case, BlindCase) for case in cases):
        raise ValueError("all challenge cases must use the BlindCase schema")
    if len({c.case_id for c in cases}) != len(cases):
        raise ValueError("challenge case identifiers must be unique")
    if any(not isinstance(c.case_id, str) or not c.case_id.strip() for c in cases):
        raise ValueError("case identifiers must be non-empty")

    commitment_inputs = []
    outcomes = []
    for case in cases:
        audit = make_research_decision_audit(
            intended_use_id=protocol_id,
            case_token=case.case_id,
            source_evidence_sha256=case.source_evidence_sha256,
            previous=case.previous,
            current=case.current,
            thresholds=case.thresholds,
            last_valid_plan_identity="SYNTHETIC-HELD-RESEARCH-PLAN",
            standard_plan_identity="SYNTHETIC-STANDARD-RESEARCH-PLAN",
        )
        commitment_inputs.append({
            "case_id": case.case_id,
            "previous": asdict(case.previous),
            "current": asdict(case.current),
            "thresholds": asdict(case.thresholds),
            "source_evidence_sha256": case.source_evidence_sha256,
        })
        # The audit record's actual decision must never grant clinical authority.
        if audit.treatment_authority:
            raise ValueError("invalid research submission: treatment authority detected")
        outcomes.append(BlindPrediction(
            case_id=case.case_id,
            action=audit.action,
            triggered=audit.action != "NO_ADAPTATION",
            proposal_allowed=audit.proposal_allowed,
            treatment_authority=audit.treatment_authority,
            decision_audit_sha256=audit.audit_sha256,
        ))

    stub = BlindedSubmission(
        protocol_id=protocol_id,
        challenge_sha256=_digest(commitment_inputs),
        results=tuple(outcomes),
        submission_sha256="",
    )
    return BlindedSubmission(
        protocol_id=stub.protocol_id,
        challenge_sha256=stub.challenge_sha256,
        results=stub.results,
        submission_sha256=_digest(_submission_payload(stub)),
    )


def score_after_label_release(
    submission: BlindedSubmission,
    held_out_labels: Mapping[str, str],
) -> LabeledScore:
    """Score only AFTER an evaluator releases labels.

    SHA-256 prevents accidental undetected local modification, not malicious
    re-signing; no person or institution's independence is authenticated.
    The intervals describe these labeled fixtures only.
    """
    if not isinstance(submission, BlindedSubmission):
        raise ValueError("expected a BlindedSubmission")
    actual = _digest(_submission_payload(submission))
    if not hmac.compare_digest(actual, submission.submission_sha256):
        raise ValueError("submission integrity digest mismatch")
    if any(result.treatment_authority for result in submission.results):
        raise ValueError("treatment authority is disallowed")
    if len({p.case_id for p in submission.results}) != len(submission.results):
        raise ValueError("duplicate result case identifiers")
    labels = dict(held_out_labels)
    if set(labels) != {item.case_id for item in submission.results}:
        raise ValueError("released labels must cover exactly the submitted cases")
    if set(labels.values()) != LABELS:
        raise ValueError("all three blinded reference strata must be present")

    disqualified = [
        result for result in submission.results
        if labels[result.case_id] == "disqualified_trigger"
    ]
    qualified = [
        result for result in submission.results
        if labels[result.case_id] == "qualified_trigger"
    ]
    no_trigger = [
        result for result in submission.results if labels[result.case_id] == "no_trigger"
    ]
    return LabeledScore(
        critical_false_proceed=_rate(
            sum(r.proposal_allowed for r in disqualified), len(disqualified)
        ),
        eligible_proposal_recall=_rate(
            sum(r.proposal_allowed for r in qualified), len(qualified)
        ),
        spurious_no_trigger_proposals=_rate(
            sum(r.proposal_allowed for r in no_trigger), len(no_trigger)
        ),
        held_out_labels_sha256=_digest(sorted(labels.items())),
        submission_sha256=submission.submission_sha256,
    )
