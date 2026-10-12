"""Worldshepherd collaborator candidate evidence guard.

This module records public, technical evidence for possible collaborators. It does
not recruit people, infer consent, authorize outreach, establish employment, or
create a partnership. Candidate status is an internal research state only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Dict, Iterable, List, Mapping, Tuple

CANDIDATE_SCHEMA = "WS-COLLAB-CANDIDATE-V1"
REGISTRY_SCHEMA = "WS-COLLAB-REGISTRY-V1"
_ALLOWED_SOURCE_LANES = frozenset({"WEB3", "WEBP3", "OTHER"})
_ALLOWED_CANDIDATE_TYPES = frozenset({"PERSON", "TEAM", "ORG"})


@dataclass(frozen=True)
class CandidateEvidence:
    candidate_id: str
    display_name: str
    candidate_type: str
    source_lane: str
    technical_domains: Tuple[str, ...]
    worldshepherd_lanes: Tuple[str, ...]
    evidence_refs: Tuple[str, ...]
    contact_surfaces: Tuple[str, ...]
    observed_at: str
    last_verified_at: str
    source_resolution_note: str = ""

    public_evidence_only: bool = True
    identity_evidence_verified: bool = False
    technical_work_verified: bool = False
    freshness_verified: bool = False
    collaboration_surface_public: bool = False
    conflict_screen_complete: bool = False
    no_known_conflict: bool = False
    explicit_collaboration_interest_evidenced: bool = False


@dataclass(frozen=True)
class CandidateDecision:
    schema: str
    status: str
    candidate_review_ready: bool
    outreach_review_ready: bool
    missing_predicates: List[str]
    digest: str
    human_review_required: bool
    outreach_authorized: bool
    teammate_relationship_established: bool
    employment_offer_authorized: bool
    partnership_authorized: bool
    claims_boundary: Dict[str, bool]


@dataclass(frozen=True)
class CandidateRegistryDecision:
    schema: str
    status: str
    registry_valid: bool
    candidate_count: int
    review_ready_ids: List[str]
    outreach_review_ready_ids: List[str]
    issues: List[str]
    digest: str
    outreach_authorized: bool
    partnership_authorized: bool


def canonical_candidate_payload(candidate: CandidateEvidence) -> Dict[str, object]:
    """Return semantic candidate facts committed by the candidate digest."""
    return {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": candidate.candidate_id,
        "display_name": candidate.display_name,
        "candidate_type": candidate.candidate_type,
        "source_lane": candidate.source_lane,
        "technical_domains": sorted(set(candidate.technical_domains)),
        "worldshepherd_lanes": sorted(set(candidate.worldshepherd_lanes)),
        "evidence_refs": sorted(set(candidate.evidence_refs)),
        "contact_surfaces": sorted(set(candidate.contact_surfaces)),
        "observed_at": candidate.observed_at,
        "last_verified_at": candidate.last_verified_at,
        "source_resolution_note": candidate.source_resolution_note,
    }


def candidate_digest(candidate: CandidateEvidence) -> str:
    raw = json.dumps(
        canonical_candidate_payload(candidate),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _semantic_issues(candidate: CandidateEvidence) -> List[str]:
    issues: list[str] = []
    for field in ("candidate_id", "display_name", "observed_at", "last_verified_at"):
        if not getattr(candidate, field):
            issues.append(f"{field} must be non-empty")
    if candidate.candidate_type not in _ALLOWED_CANDIDATE_TYPES:
        issues.append("unsupported candidate type")
    if candidate.source_lane not in _ALLOWED_SOURCE_LANES:
        issues.append("unsupported source lane")
    if not candidate.technical_domains:
        issues.append("technical domains missing")
    if not candidate.worldshepherd_lanes:
        issues.append("Worldshepherd lane mapping missing")
    if len(set(candidate.evidence_refs)) < 2:
        issues.append("at least two distinct public evidence references required")
    return issues


def evaluate_candidate(candidate: CandidateEvidence) -> CandidateDecision:
    missing = _semantic_issues(candidate)
    checks = (
        (candidate.public_evidence_only, "candidate evidence is not restricted to public sources"),
        (candidate.identity_evidence_verified, "candidate identity evidence not verified"),
        (candidate.technical_work_verified, "technical work not verified"),
        (candidate.freshness_verified, "candidate evidence freshness not verified"),
    )
    missing.extend(reason for passed, reason in checks if not passed)
    candidate_ready = not missing

    outreach_review_ready = candidate_ready
    if not candidate.collaboration_surface_public:
        outreach_review_ready = False
    if not candidate.conflict_screen_complete:
        outreach_review_ready = False
    if not candidate.no_known_conflict:
        outreach_review_ready = False

    if candidate_ready and outreach_review_ready:
        status = "EVIDENCED_CANDIDATE_FOR_OUTREACH_HUMAN_REVIEW"
    elif candidate_ready:
        status = "EVIDENCED_CANDIDATE_FOR_HUMAN_REVIEW"
    else:
        status = "INSUFFICIENT_PUBLIC_CANDIDATE_EVIDENCE"

    return CandidateDecision(
        schema=CANDIDATE_SCHEMA,
        status=status,
        candidate_review_ready=candidate_ready,
        outreach_review_ready=outreach_review_ready,
        missing_predicates=missing,
        digest=candidate_digest(candidate),
        human_review_required=True,
        outreach_authorized=False,
        teammate_relationship_established=False,
        employment_offer_authorized=False,
        partnership_authorized=False,
        claims_boundary={
            "consent_inferred": False,
            "availability_inferred": False,
            "employment_relationship_established": False,
            "partnership_relationship_established": False,
            "outreach_execution_authority": False,
            "private_data_collection_authority": False,
        },
    )


def candidate_from_mapping(value: Mapping[str, object]) -> CandidateEvidence:
    """Parse a JSON-style public candidate record into the strict evidence type."""
    return CandidateEvidence(
        candidate_id=str(value.get("candidate_id", "")),
        display_name=str(value.get("display_name", "")),
        candidate_type=str(value.get("candidate_type", "")),
        source_lane=str(value.get("source_lane", "")),
        technical_domains=tuple(str(item) for item in value.get("technical_domains", []) or []),
        worldshepherd_lanes=tuple(str(item) for item in value.get("worldshepherd_lanes", []) or []),
        evidence_refs=tuple(str(item) for item in value.get("evidence_refs", []) or []),
        contact_surfaces=tuple(str(item) for item in value.get("contact_surfaces", []) or []),
        observed_at=str(value.get("observed_at", "")),
        last_verified_at=str(value.get("last_verified_at", "")),
        source_resolution_note=str(value.get("source_resolution_note", "")),
        public_evidence_only=bool(value.get("public_evidence_only", True)),
        identity_evidence_verified=bool(value.get("identity_evidence_verified", False)),
        technical_work_verified=bool(value.get("technical_work_verified", False)),
        freshness_verified=bool(value.get("freshness_verified", False)),
        collaboration_surface_public=bool(value.get("collaboration_surface_public", False)),
        conflict_screen_complete=bool(value.get("conflict_screen_complete", False)),
        no_known_conflict=bool(value.get("no_known_conflict", False)),
        explicit_collaboration_interest_evidenced=bool(
            value.get("explicit_collaboration_interest_evidenced", False)
        ),
    )


def registry_digest(candidates: Iterable[CandidateEvidence]) -> str:
    payloads = [canonical_candidate_payload(candidate) for candidate in candidates]
    payloads.sort(key=lambda item: str(item["candidate_id"]))
    raw = json.dumps(
        {"schema": REGISTRY_SCHEMA, "candidates": payloads},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_candidate_registry(
    candidates: Iterable[CandidateEvidence],
) -> CandidateRegistryDecision:
    records = list(candidates)
    issues: list[str] = []
    if not records:
        issues.append("candidate registry is empty")

    ids = [candidate.candidate_id for candidate in records]
    if len(set(ids)) != len(ids):
        issues.append("duplicate candidate_id")

    digests = [candidate_digest(candidate) for candidate in records]
    if len(set(digests)) != len(digests):
        issues.append("duplicate semantic candidate record")

    decisions = [evaluate_candidate(candidate) for candidate in records]
    ready_ids = [
        candidate.candidate_id
        for candidate, decision in zip(records, decisions)
        if decision.candidate_review_ready
    ]
    outreach_review_ids = [
        candidate.candidate_id
        for candidate, decision in zip(records, decisions)
        if decision.outreach_review_ready
    ]

    valid = not issues
    return CandidateRegistryDecision(
        schema=REGISTRY_SCHEMA,
        status="COLLABORATOR_REGISTRY_INTERNALLY_CONSISTENT" if valid else "COLLABORATOR_REGISTRY_REVIEW_REQUIRED",
        registry_valid=valid,
        candidate_count=len(records),
        review_ready_ids=sorted(ready_ids),
        outreach_review_ready_ids=sorted(outreach_review_ids),
        issues=issues,
        digest=registry_digest(records),
        outreach_authorized=False,
        partnership_authorized=False,
    )
