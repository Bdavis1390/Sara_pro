from dataclasses import replace

from collaboration.response_guard import (
    ResponseEvidence,
    canonical_response_payload,
    evaluate_response,
    response_digest,
)


def valid_response(response_class="ROUTED_TO_PUBLIC_FORUM"):
    return ResponseEvidence(
        candidate_id="candidate:example",
        candidate_digest="candidate-digest-example",
        response_class=response_class,
        response_evidence_reference="source-system:opaque-reference",
        observed_at="2026-09-16T18:00:00Z",
        source_channel="email",
        candidate_binding_verified=True,
        response_source_verified=True,
        response_evidence_bound=True,
        freshness_verified=True,
        human_interpretation_reviewed=True,
    )


def assert_no_relationship_or_spend_authority(decision):
    assert decision.budget_commitment_authorized is False
    assert decision.outreach_expansion_authorized is False
    assert decision.teammate_relationship_established is False
    assert decision.employment_relationship_established is False
    assert decision.partnership_established is False


def test_public_forum_routing_is_evidence_not_relationship():
    decision = evaluate_response(valid_response("ROUTED_TO_PUBLIC_FORUM"))
    assert decision.response_record_valid is True
    assert decision.next_action == "ENGAGE_REFERRED_PUBLIC_FORUM"
    assert decision.human_followup_required is True
    assert_no_relationship_or_spend_authority(decision)
    assert decision.claims_boundary["routing_implies_endorsement"] is False


def test_paid_review_offer_never_authorizes_budget():
    decision = evaluate_response(valid_response("PAID_REVIEW_AVAILABLE"))
    assert decision.response_record_valid is True
    assert decision.next_action == "HUMAN_BUDGET_AND_SCOPE_REVIEW"
    assert_no_relationship_or_spend_authority(decision)
    assert decision.claims_boundary["quote_implies_purchase_authority"] is False


def test_interest_still_requires_human_relationship_review():
    decision = evaluate_response(valid_response("COLLABORATION_INTEREST_EXPRESSED"))
    assert decision.response_record_valid is True
    assert decision.next_action == "HUMAN_RELATIONSHIP_REVIEW"
    assert decision.human_followup_required is True
    assert_no_relationship_or_spend_authority(decision)
    assert decision.claims_boundary["interest_implies_relationship"] is False


def test_decline_is_valid_evidence_but_never_relationship():
    decision = evaluate_response(valid_response("DECLINED"))
    assert decision.response_record_valid is True
    assert decision.next_action == "CLOSE_OR_DEFER"
    assert decision.human_followup_required is False
    assert_no_relationship_or_spend_authority(decision)


def test_unknown_response_class_fails_closed():
    decision = evaluate_response(valid_response("PARTNER_CONFIRMED"))
    assert decision.response_record_valid is False
    assert decision.response_class == "UNSUPPORTED"
    assert decision.next_action == "BLOCKED"
    assert "unsupported response class" in decision.missing_predicates
    assert_no_relationship_or_spend_authority(decision)


def test_each_evidence_verification_predicate_is_required():
    base = valid_response()
    for field in (
        "candidate_binding_verified",
        "response_source_verified",
        "response_evidence_bound",
        "freshness_verified",
        "human_interpretation_reviewed",
    ):
        decision = evaluate_response(replace(base, **{field: False}))
        assert decision.response_record_valid is False, field
        assert decision.next_action == "BLOCKED"
        assert_no_relationship_or_spend_authority(decision)


def test_digest_binds_semantic_reference_without_storing_message_body():
    base = valid_response()
    payload = canonical_response_payload(base)
    assert set(payload) == {
        "schema",
        "candidate_id",
        "candidate_digest",
        "response_class",
        "response_evidence_reference",
        "observed_at",
        "source_channel",
    }
    assert "body" not in payload
    assert "price" not in payload
    assert "email_address" not in payload

    original = response_digest(base)
    assert response_digest(replace(base, response_evidence_reference="source-system:other")) != original
    assert response_digest(replace(base, response_class="PAID_REVIEW_AVAILABLE")) != original


def test_missing_reference_fails_closed():
    decision = evaluate_response(replace(valid_response(), response_evidence_reference=""))
    assert decision.response_record_valid is False
    assert "response_evidence_reference must be non-empty" in decision.missing_predicates
    assert_no_relationship_or_spend_authority(decision)
