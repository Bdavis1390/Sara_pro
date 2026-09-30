import json
from dataclasses import replace
from pathlib import Path

from collaboration.candidate_guard import (
    CANDIDATE_SCHEMA,
    CandidateEvidence,
    candidate_digest,
    candidate_from_mapping,
    evaluate_candidate,
    evaluate_candidate_registry,
    registry_digest,
)


def candidate(**overrides):
    value = CandidateEvidence(
        candidate_id="web3:example",
        display_name="Example Candidate",
        candidate_type="PERSON",
        source_lane="WEB3",
        technical_domains=("post-quantum cryptography",),
        worldshepherd_lanes=("QCRYPTO",),
        evidence_refs=("https://example.test/a", "https://example.test/b"),
        contact_surfaces=("https://example.test/profile",),
        observed_at="2026-09-15",
        last_verified_at="2026-09-15",
        public_evidence_only=True,
        identity_evidence_verified=True,
        technical_work_verified=True,
        freshness_verified=True,
        collaboration_surface_public=True,
        conflict_screen_complete=False,
        no_known_conflict=False,
    )
    return replace(value, **overrides)


def test_evidenced_candidate_requires_human_review_and_never_authorizes_outreach():
    d = evaluate_candidate(candidate())
    assert d.schema == CANDIDATE_SCHEMA
    assert d.status == "EVIDENCED_CANDIDATE_FOR_HUMAN_REVIEW"
    assert d.candidate_review_ready is True
    assert d.outreach_review_ready is False
    assert d.human_review_required is True
    assert d.outreach_authorized is False
    assert d.teammate_relationship_established is False
    assert d.employment_offer_authorized is False
    assert d.partnership_authorized is False


def test_outreach_review_readiness_still_does_not_authorize_contact():
    d = evaluate_candidate(
        candidate(conflict_screen_complete=True, no_known_conflict=True)
    )
    assert d.status == "EVIDENCED_CANDIDATE_FOR_OUTREACH_HUMAN_REVIEW"
    assert d.outreach_review_ready is True
    assert d.outreach_authorized is False
    assert d.partnership_authorized is False


def test_two_distinct_public_sources_are_required():
    d = evaluate_candidate(candidate(evidence_refs=("https://example.test/a",)))
    assert d.candidate_review_ready is False
    assert "at least two distinct public evidence references required" in d.missing_predicates


def test_identity_technical_work_and_freshness_are_fail_closed():
    base = candidate()
    for field in (
        "identity_evidence_verified",
        "technical_work_verified",
        "freshness_verified",
    ):
        d = evaluate_candidate(replace(base, **{field: False}))
        assert d.candidate_review_ready is False, field
        assert d.missing_predicates, field


def test_candidate_digest_commits_semantic_identity_sources_and_lane_mapping():
    value = candidate()
    assert candidate_digest(value) == candidate_digest(value)
    assert candidate_digest(replace(value, display_name="Different")) != candidate_digest(value)
    assert candidate_digest(
        replace(value, evidence_refs=("https://example.test/a", "https://example.test/c"))
    ) != candidate_digest(value)
    assert candidate_digest(replace(value, worldshepherd_lanes=("SARA_INTEROP",))) != candidate_digest(value)


def test_verification_flags_do_not_rewrite_candidate_identity_digest():
    value = candidate()
    changed = replace(value, conflict_screen_complete=True, no_known_conflict=True)
    assert candidate_digest(changed) == candidate_digest(value)


def test_registry_rejects_duplicate_candidate_ids():
    a = candidate()
    b = replace(a, display_name="Second semantic record")
    d = evaluate_candidate_registry([a, b])
    assert d.registry_valid is False
    assert "duplicate candidate_id" in d.issues
    assert d.outreach_authorized is False
    assert d.partnership_authorized is False


def test_registry_digest_is_order_independent():
    a = candidate(candidate_id="web3:a", display_name="A")
    b = candidate(candidate_id="web3:b", display_name="B")
    assert registry_digest([a, b]) == registry_digest([b, a])


def test_seed_file_parses_and_webp3_is_not_silently_promoted():
    payload = json.loads(
        Path("collaboration/web3_candidate_seed_2026-09-15.json").read_text()
    )
    records = [candidate_from_mapping(item) for item in payload["candidates"]]
    d = evaluate_candidate_registry(records)
    assert d.registry_valid is True
    assert len(records) >= 5
    assert all(item.source_lane == "WEB3" for item in records)
    resolution = payload["source_resolution"]["webp3"]
    assert resolution["status"] == "AMBIGUOUS_OR_LOW_RELEVANCE"
    assert "Do not promote" in resolution["note"]


def test_seed_candidates_are_review_candidates_not_preapproved_teammates():
    payload = json.loads(
        Path("collaboration/web3_candidate_seed_2026-09-15.json").read_text()
    )
    decisions = [
        evaluate_candidate(candidate_from_mapping(item)) for item in payload["candidates"]
    ]
    assert decisions
    assert all(decision.candidate_review_ready for decision in decisions)
    assert all(decision.outreach_authorized is False for decision in decisions)
    assert all(decision.teammate_relationship_established is False for decision in decisions)
    assert all(decision.partnership_authorized is False for decision in decisions)
