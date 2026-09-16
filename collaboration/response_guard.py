"""Claims-controlled collaborator response classification for Worldshepherd.

This module tracks the *state of evidence* after outreach without storing private
message bodies and without converting a response into relationship, hiring,
partnership, or spending authority.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Dict, List, Tuple

RESPONSE_SCHEMA = "WS-COLLAB-RESPONSE-V1"

RESPONSE_CLASSES: Tuple[str, ...] = (
    "NO_RESPONSE_YET",
    "ROUTED_TO_PUBLIC_FORUM",
    "PAID_REVIEW_AVAILABLE",
    "SCOPE_DISCUSSION_AVAILABLE",
    "COLLABORATION_INTEREST_EXPRESSED",
    "DECLINED",
    "UNDELIVERABLE_OR_CHANNEL_CLOSED",
)

_NEXT_ACTION = {
    "NO_RESPONSE_YET": "MONITOR_ONLY",
    "ROUTED_TO_PUBLIC_FORUM": "ENGAGE_REFERRED_PUBLIC_FORUM",
    "PAID_REVIEW_AVAILABLE": "HUMAN_BUDGET_AND_SCOPE_REVIEW",
    "SCOPE_DISCUSSION_AVAILABLE": "HUMAN_SCOPE_REVIEW",
    "COLLABORATION_INTEREST_EXPRESSED": "HUMAN_RELATIONSHIP_REVIEW",
    "DECLINED": "CLOSE_OR_DEFER",
    "UNDELIVERABLE_OR_CHANNEL_CLOSED": "FIND_ALTERNATE_PUBLIC_CHANNEL",
}


@dataclass(frozen=True)
class ResponseEvidence:
    candidate_id: str
    candidate_digest: str
    response_class: str
    response_evidence_reference: str
    observed_at: str
    source_channel: str

    candidate_binding_verified: bool = False
    response_source_verified: bool = False
    response_evidence_bound: bool = False
    freshness_verified: bool = False
    human_interpretation_reviewed: bool = False


@dataclass(frozen=True)
class ResponseDecision:
    schema: str
    status: str
    response_record_valid: bool
    response_class: str
    next_action: str
    missing_predicates: List[str]
    digest: str
    human_followup_required: bool
    budget_commitment_authorized: bool
    outreach_expansion_authorized: bool
    teammate_relationship_established: bool
    employment_relationship_established: bool
    partnership_established: bool
    claims_boundary: Dict[str, bool]


def canonical_response_payload(evidence: ResponseEvidence) -> Dict[str, object]:
    """Return privacy-minimized semantic material for audit hashing.

    Deliberately excludes message body, personal notes, prices, addresses, phone
    numbers, and other unnecessary communications content. Those remain in the
    authoritative source system and are referenced by opaque evidence reference.
    """
    return {
        "schema": RESPONSE_SCHEMA,
        "candidate_id": evidence.candidate_id,
        "candidate_digest": evidence.candidate_digest,
        "response_class": evidence.response_class,
        "response_evidence_reference": evidence.response_evidence_reference,
        "observed_at": evidence.observed_at,
        "source_channel": evidence.source_channel,
    }


def response_digest(evidence: ResponseEvidence) -> str:
    raw = json.dumps(
        canonical_response_payload(evidence),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_response(evidence: ResponseEvidence) -> ResponseDecision:
    missing: List[str] = []
    if evidence.response_class not in RESPONSE_CLASSES:
        missing.append("unsupported response class")
    for field in (
        "candidate_id",
        "candidate_digest",
        "response_evidence_reference",
        "observed_at",
        "source_channel",
    ):
        if not getattr(evidence, field):
            missing.append(f"{field} must be non-empty")
    required = {
        "candidate_binding_verified": "candidate binding not verified",
        "response_source_verified": "response source not verified",
        "response_evidence_bound": "response evidence not bound",
        "freshness_verified": "response freshness not verified",
        "human_interpretation_reviewed": "human interpretation not reviewed",
    }
    missing.extend(reason for field, reason in required.items() if not getattr(evidence, field))

    valid = not missing
    response_class = evidence.response_class if evidence.response_class in RESPONSE_CLASSES else "UNSUPPORTED"
    next_action = _NEXT_ACTION.get(response_class, "BLOCKED") if valid else "BLOCKED"

    human_followup = valid and response_class in {
        "ROUTED_TO_PUBLIC_FORUM",
        "PAID_REVIEW_AVAILABLE",
        "SCOPE_DISCUSSION_AVAILABLE",
        "COLLABORATION_INTEREST_EXPRESSED",
    }

    return ResponseDecision(
        schema=RESPONSE_SCHEMA,
        status="EVIDENCED_RESPONSE_FOR_HUMAN_REVIEW" if valid else "INSUFFICIENT_RESPONSE_EVIDENCE",
        response_record_valid=valid,
        response_class=response_class,
        next_action=next_action,
        missing_predicates=missing,
        digest=response_digest(evidence),
        human_followup_required=human_followup,
        budget_commitment_authorized=False,
        outreach_expansion_authorized=False,
        teammate_relationship_established=False,
        employment_relationship_established=False,
        partnership_established=False,
        claims_boundary={
            "response_implies_consent_to_join": False,
            "quote_implies_purchase_authority": False,
            "routing_implies_endorsement": False,
            "interest_implies_relationship": False,
            "private_message_content_stored": False,
        },
    )


def response_record(evidence: ResponseEvidence) -> Dict[str, object]:
    return {"evidence": asdict(evidence), "decision": asdict(evaluate_response(evidence))}
