"""Human technical-review gate for structurally ingested external QRF evidence.

The ingest engine can establish that a current campaign gate is structurally complete
and locally re-hashed. It cannot decide scientific validity or promote readiness.
This module records a human review recommendation without mutating project state.

Worldshepherd doctrine remains: AI may prepare evidence and analysis; an authorized
human reviewer must approve any technical promotion recommendation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any

from worldshepherd_sara.quantum_external_ingest import ExternalEvidenceBatchDecision


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_PLACEHOLDER = ("placeholder", "todo", "tbd", "unknown", "replace-me", "<", ">")


@dataclass(frozen=True)
class ExternalEvidenceTechnicalReview:
    review_id: str
    project_id: str
    gate_id: str
    ingest_decision_digest: str
    reviewer_identity: str
    reviewer_role: str
    reviewer_is_human: bool
    reviewed_utc: str
    technical_validity_accepted: bool
    provenance_accepted: bool
    uncertainty_or_error_reviewed: bool
    negative_evidence_reviewed: bool
    claims_control_accepted: bool
    conflict_of_interest_or_bias_considered: bool
    promotion_recommended: bool
    rationale: str
    limitations: str
    claim_control: str = (
        "A technical-review record is a human governance decision over a structurally ingested evidence package. "
        "It does not itself mutate the canonical mission-readiness state, grant deployment authority, or prove quantum advantage."
    )


@dataclass(frozen=True)
class TechnicalReviewDecision:
    accepted_review_record: bool
    promotion_recommended: bool
    project_id: str
    gate_id: str
    structurally_achieved_stage: str | None
    reasons: tuple[str, ...]
    review_record_digest: str
    next_governed_action: str
    claim_control: str


def _json_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def ingest_decision_digest(decision: ExternalEvidenceBatchDecision) -> str:
    return _json_digest(asdict(decision))


def review_record_digest(record: ExternalEvidenceTechnicalReview) -> str:
    return _json_digest(asdict(record))


def _placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(token in lowered for token in _PLACEHOLDER)


def _valid_utc(value: str) -> bool:
    if not value.strip().endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def evaluate_technical_review(
    review: ExternalEvidenceTechnicalReview,
    *,
    ingest_decision: ExternalEvidenceBatchDecision,
) -> TechnicalReviewDecision:
    reasons: list[str] = []
    expected_ingest_digest = ingest_decision_digest(ingest_decision)

    if not ingest_decision.ready_for_technical_review:
        reasons.append("ingest decision is not ready for technical review")
    if ingest_decision.project_id is None or ingest_decision.current_gate_id is None:
        reasons.append("ingest decision lacks project/current gate identity")
    if review.project_id != ingest_decision.project_id:
        reasons.append("review project_id does not match ingested project")
    if review.gate_id != ingest_decision.current_gate_id:
        reasons.append("review gate_id does not match ingested current gate")
    if not _SHA256.fullmatch(review.ingest_decision_digest.lower()):
        reasons.append("ingest_decision_digest must be sha256")
    elif review.ingest_decision_digest.lower() != expected_ingest_digest.lower():
        reasons.append("review is not bound to the supplied ingest decision digest")

    for field in ("review_id", "reviewer_identity", "reviewer_role", "rationale", "limitations"):
        if _placeholder(str(getattr(review, field))):
            reasons.append(f"{field} must be concrete and non-placeholder")
    if not review.reviewer_is_human:
        reasons.append("technical promotion review requires an identified human reviewer")
    if not _valid_utc(review.reviewed_utc):
        reasons.append("reviewed_utc must be a valid UTC timestamp ending in Z")

    mandatory_checks = {
        "technical_validity_accepted": review.technical_validity_accepted,
        "provenance_accepted": review.provenance_accepted,
        "uncertainty_or_error_reviewed": review.uncertainty_or_error_reviewed,
        "negative_evidence_reviewed": review.negative_evidence_reviewed,
        "claims_control_accepted": review.claims_control_accepted,
        "conflict_of_interest_or_bias_considered": review.conflict_of_interest_or_bias_considered,
    }
    if review.promotion_recommended:
        for field, accepted in mandatory_checks.items():
            if not accepted:
                reasons.append(f"promotion recommendation requires {field}=true")

    accepted_record = not reasons
    promotion = accepted_record and review.promotion_recommended
    if promotion:
        action = (
            f"Human recommendation is eligible for a separate canonical state-change action to "
            f"{ingest_decision.achieved_stage}; do not mutate state implicitly."
        )
    elif accepted_record:
        action = "Retain the reviewed package without promotion and address the review rationale/limitations before resubmission."
    else:
        action = "Reject or repair the technical-review record before any state-change consideration."

    return TechnicalReviewDecision(
        accepted_review_record=accepted_record,
        promotion_recommended=promotion,
        project_id=review.project_id,
        gate_id=review.gate_id,
        structurally_achieved_stage=ingest_decision.achieved_stage,
        reasons=tuple(reasons),
        review_record_digest=review_record_digest(review),
        next_governed_action=action,
        claim_control=(
            "This decision validates a human review record and may recommend a stage promotion. It performs no project-state mutation, "
            "no deployment authorization, and no automatic scientific claim acceptance beyond the explicitly reviewed evidence."
        ),
    )


def technical_review_template_as_dict() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "record": {
            "review_id": "<replace-me>",
            "project_id": "<from-ingest-decision>",
            "gate_id": "<current-gate-from-ingest-decision>",
            "ingest_decision_digest": "<sha256-of-exact-ingest-decision>",
            "reviewer_identity": "<identified-human-reviewer>",
            "reviewer_role": "<authorized-review-role>",
            "reviewer_is_human": True,
            "reviewed_utc": "<YYYY-MM-DDTHH:MM:SSZ>",
            "technical_validity_accepted": False,
            "provenance_accepted": False,
            "uncertainty_or_error_reviewed": False,
            "negative_evidence_reviewed": False,
            "claims_control_accepted": False,
            "conflict_of_interest_or_bias_considered": False,
            "promotion_recommended": False,
            "rationale": "<replace-me>",
            "limitations": "<replace-me>"
        },
        "claim_control": (
            "Template only. AI-generated completion is not human approval. Promotion must remain false unless an identified authorized human reviewer "
            "has actually reviewed the bound evidence package and all required checks."
        )
    }
