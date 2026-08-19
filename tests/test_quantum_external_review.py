from worldshepherd_sara.quantum_external_ingest import ExternalEvidenceBatchDecision
from worldshepherd_sara.quantum_external_review import (
    ExternalEvidenceTechnicalReview,
    evaluate_technical_review,
    ingest_decision_digest,
    technical_review_template_as_dict,
)


def _ingest(*, ready: bool = True) -> ExternalEvidenceBatchDecision:
    return ExternalEvidenceBatchDecision(
        project_id="SARA-QRF",
        current_gate_id="SARA-QRF-EXT-01",
        records_received=1,
        records_accepted_for_campaign_evaluation=1 if ready else 0,
        record_decisions=(),
        achieved_stage="single_external_hardware" if ready else "integrated_simulation",
        next_gate_id="SARA-QRF-EXT-02" if ready else "SARA-QRF-EXT-01",
        campaign_gate_satisfied=ready,
        ready_for_technical_review=ready,
        claim_control="fixture ingest decision",
    )


def _review(ingest: ExternalEvidenceBatchDecision, **overrides) -> ExternalEvidenceTechnicalReview:
    payload = dict(
        review_id="WS-REVIEW-FIXTURE-001",
        project_id="SARA-QRF",
        gate_id="SARA-QRF-EXT-01",
        ingest_decision_digest=ingest_decision_digest(ingest),
        reviewer_identity="fixture-human-reviewer",
        reviewer_role="authorized_human_reviewer_fixture",
        reviewer_is_human=True,
        reviewed_utc="2026-08-17T17:00:00Z",
        technical_validity_accepted=True,
        provenance_accepted=True,
        uncertainty_or_error_reviewed=True,
        negative_evidence_reviewed=True,
        claims_control_accepted=True,
        conflict_of_interest_or_bias_considered=True,
        promotion_recommended=True,
        rationale="fixture evidence meets the frozen technical-review contract",
        limitations="software fixture only; not a real QPU review",
    )
    payload.update(overrides)
    return ExternalEvidenceTechnicalReview(**payload)


def test_valid_human_review_can_recommend_but_not_mutate_promotion():
    ingest = _ingest()
    decision = evaluate_technical_review(_review(ingest), ingest_decision=ingest)

    assert decision.accepted_review_record is True
    assert decision.promotion_recommended is True
    assert decision.structurally_achieved_stage == "single_external_hardware"
    assert "separate canonical state-change action" in decision.next_governed_action
    assert decision.review_record_digest.startswith("sha256:")


def test_ai_or_unidentified_nonhuman_review_cannot_recommend_promotion():
    ingest = _ingest()
    decision = evaluate_technical_review(
        _review(ingest, reviewer_is_human=False, reviewer_identity="AI-agent"),
        ingest_decision=ingest,
    )

    assert decision.accepted_review_record is False
    assert decision.promotion_recommended is False
    assert any("identified human reviewer" in reason for reason in decision.reasons)


def test_review_must_bind_to_exact_ingest_decision_digest():
    ingest = _ingest()
    decision = evaluate_technical_review(
        _review(ingest, ingest_decision_digest="sha256:" + "a" * 64),
        ingest_decision=ingest,
    )

    assert decision.accepted_review_record is False
    assert any("not bound to the supplied ingest decision digest" in reason for reason in decision.reasons)


def test_promotion_requires_all_review_checks():
    ingest = _ingest()
    decision = evaluate_technical_review(
        _review(ingest, negative_evidence_reviewed=False),
        ingest_decision=ingest,
    )

    assert decision.accepted_review_record is False
    assert decision.promotion_recommended is False
    assert any("negative_evidence_reviewed=true" in reason for reason in decision.reasons)


def test_structurally_unready_ingest_cannot_be_promoted_by_review():
    ingest = _ingest(ready=False)
    decision = evaluate_technical_review(_review(ingest), ingest_decision=ingest)

    assert decision.accepted_review_record is False
    assert decision.promotion_recommended is False
    assert any("not ready for technical review" in reason for reason in decision.reasons)


def test_review_template_is_not_human_approval():
    payload = technical_review_template_as_dict()
    assert payload["record"]["reviewer_is_human"] is True
    assert payload["record"]["promotion_recommended"] is False
    assert "AI-generated completion is not human approval" in payload["claim_control"]
