import pytest
from pydantic import ValidationError

from worldshepherd_sara.improvement_cycle import (
    ImprovementAssessment,
    ImprovementProposal,
    ImprovementRisk,
    ImprovementState,
    ImprovementTriggerKind,
    apply_assessment,
    assess_improvement,
    record_human_decision,
    supersede_improvement,
)
from worldshepherd_sara.qualification import CapabilityStatus, ResultStatus, ReviewStatus


def make_proposal(**overrides):
    payload = {
        "improvement_id": "WS-IR-2026-0001",
        "trigger_kind": ImprovementTriggerKind.NEW_EVIDENCE,
        "title": "Cross-lane evidence feedback",
        "source_refs": ["WS-OMEGA-abcdef0123456789", "PRE-RD-2026-0001"],
        "affected_lanes": ["PRE", "ECHO", "PRIME"],
        "baseline_artifacts": ["worldshepherd_sara/recursive_discovery.py"],
        "baseline_capability_status": [CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        "target_capability_status": CapabilityStatus.IMPLEMENTED_IN_SOFTWARE,
        "proposed_change": "Route qualified discoveries into an auditable improvement record.",
        "expected_benefit": "Convert discoveries into testable, reversible improvement proposals.",
        "assumptions": ["Existing qualification and authorization controls remain authoritative."],
        "risks": ["A weak source could produce a low-value proposal."],
        "risk_level": ImprovementRisk.MODERATE,
        "required_tests": ["test_schema", "test_fail_closed"],
        "success_metrics": ["schema validates", "claim and execution boundaries fail closed"],
        "reversible": True,
        "generated_by": "SARA",
        "created_utc": "2026-09-12T19:30:00Z",
    }
    payload.update(overrides)
    return ImprovementProposal(**payload)


def test_proposal_fails_closed_on_self_authorized_claim_promotion():
    with pytest.raises(ValidationError):
        make_proposal(requested_claim_promotion=True)


def test_proposal_fails_closed_on_self_authorized_external_execution():
    with pytest.raises(ValidationError):
        make_proposal(requested_external_execution=True)


def test_missing_or_inconclusive_tests_keep_proposal_validating():
    proposal = make_proposal()
    assessment = assess_improvement(
        proposal,
        {"test_schema": ResultStatus.INCONCLUSIVE},
    )
    assert assessment.disposition == ImprovementState.VALIDATING
    assert assessment.inconclusive_tests == ["test_schema"]
    assert assessment.missing_tests == ["test_fail_closed"]
    assert not assessment.claim_promotion_performed
    assert not assessment.external_execution_performed


def test_failed_required_test_quarantines_proposal():
    proposal = make_proposal()
    assessment = assess_improvement(
        proposal,
        {
            "test_schema": ResultStatus.PASS,
            "test_fail_closed": ResultStatus.FAIL,
        },
    )
    assert assessment.disposition == ImprovementState.QUARANTINED
    updated = apply_assessment(proposal, assessment)
    assert updated.state == ImprovementState.QUARANTINED


def test_all_required_tests_only_advance_to_human_review():
    proposal = make_proposal()
    assessment = assess_improvement(
        proposal,
        {
            "test_schema": ResultStatus.PASS,
            "test_fail_closed": ResultStatus.PASS,
        },
    )
    assert assessment.disposition == ImprovementState.HUMAN_REVIEW_REQUIRED
    updated = apply_assessment(proposal, assessment)
    assert updated.state == ImprovementState.HUMAN_REVIEW_REQUIRED
    assert updated.review.status == ReviewStatus.UNREVIEWED


def test_accepted_human_decision_requires_qualification_and_authorization():
    proposal = make_proposal(state=ImprovementState.HUMAN_REVIEW_REQUIRED)
    with pytest.raises(ValueError):
        record_human_decision(
            proposal,
            accepted=True,
            reviewer="CRE1AWS",
            reviewed_utc="2026-09-12T19:40:00Z",
            rationale="Validation complete.",
            qualification_refs=[],
            authorization_ref="PRIME-AUTH-1",
        )
    with pytest.raises(ValueError):
        record_human_decision(
            proposal,
            accepted=True,
            reviewer="CRE1AWS",
            reviewed_utc="2026-09-12T19:40:00Z",
            rationale="Validation complete.",
            qualification_refs=["WS-QE-2026-0001"],
            authorization_ref=None,
        )


def test_human_accepted_proposal_can_be_promoted_as_record_not_executed():
    proposal = make_proposal(state=ImprovementState.HUMAN_REVIEW_REQUIRED)
    promoted = record_human_decision(
        proposal,
        accepted=True,
        reviewer="CRE1AWS",
        reviewed_utc="2026-09-12T19:40:00Z",
        rationale="Evidence and bounded authorization accepted.",
        qualification_refs=["WS-QE-2026-0001"],
        authorization_ref="PRIME-AUTH-1",
    )
    assert promoted.state == ImprovementState.PROMOTED
    assert promoted.review.status == ReviewStatus.ACCEPTED
    assert promoted.review.reviewer == "CRE1AWS"
    assert not promoted.requested_external_execution


def test_human_rejection_preserves_record():
    proposal = make_proposal(state=ImprovementState.HUMAN_REVIEW_REQUIRED)
    rejected = record_human_decision(
        proposal,
        accepted=False,
        reviewer="CRE1AWS",
        reviewed_utc="2026-09-12T19:40:00Z",
        rationale="Benefit did not justify residual risk.",
        qualification_refs=["WS-QE-2026-0001"],
    )
    assert rejected.state == ImprovementState.REJECTED
    assert rejected.review.status == ReviewStatus.REJECTED


def test_promoted_improvement_can_be_superseded_without_erasure():
    proposal = make_proposal(state=ImprovementState.HUMAN_REVIEW_REQUIRED)
    promoted = record_human_decision(
        proposal,
        accepted=True,
        reviewer="CRE1AWS",
        reviewed_utc="2026-09-12T19:40:00Z",
        rationale="Evidence and bounded authorization accepted.",
        qualification_refs=["WS-QE-2026-0001"],
        authorization_ref="PRIME-AUTH-1",
    )
    superseded = supersede_improvement(promoted, superseded_by="WS-IR-2026-0002")
    assert superseded.state == ImprovementState.SUPERSEDED
    assert {"superseded_by": "WS-IR-2026-0002"} in superseded.negative_evidence


def test_public_transition_revalidates_existing_forbidden_execution_flag():
    proposal = make_proposal()
    invalid = proposal.model_copy(update={"requested_external_execution": True})
    assessment = assess_improvement(
        invalid,
        {
            "test_schema": ResultStatus.PASS,
            "test_fail_closed": ResultStatus.FAIL,
        },
    )
    with pytest.raises(ValidationError):
        apply_assessment(invalid, assessment)


def test_human_transition_revalidates_existing_forbidden_claim_flag():
    proposal = make_proposal(state=ImprovementState.HUMAN_REVIEW_REQUIRED)
    invalid = proposal.model_copy(update={"requested_claim_promotion": True})
    with pytest.raises(ValidationError):
        record_human_decision(
            invalid,
            accepted=True,
            reviewer="CRE1AWS",
            reviewed_utc="2026-09-12T19:40:00Z",
            rationale="Evidence accepted.",
            qualification_refs=["WS-QE-2026-0001"],
            authorization_ref="PRIME-AUTH-1",
        )


def test_assessment_is_bound_to_unmodified_proposal():
    proposal = make_proposal()
    assessment = assess_improvement(
        proposal,
        {"test_schema": ResultStatus.PASS, "test_fail_closed": ResultStatus.PASS},
    )
    changed = proposal.model_copy(update={"proposed_change": "Changed after testing"})
    with pytest.raises(ValueError, match="bound to the exact current proposal"):
        apply_assessment(changed, assessment)


def test_legacy_assessment_without_proposal_binding_fails_closed():
    proposal = make_proposal()
    assessment = assess_improvement(
        proposal,
        {"test_schema": ResultStatus.PASS, "test_fail_closed": ResultStatus.PASS},
    )
    unbound = assessment.model_copy(update={"proposal_digest": ""})
    with pytest.raises(ValueError, match="bound to the exact current proposal"):
        apply_assessment(proposal, unbound)


def test_forged_review_ready_disposition_cannot_hide_failed_test():
    proposal = make_proposal()
    assessment = assess_improvement(
        proposal,
        {"test_schema": ResultStatus.PASS, "test_fail_closed": ResultStatus.FAIL},
    )
    forged = assessment.model_copy(update={"disposition": ImprovementState.HUMAN_REVIEW_REQUIRED})
    with pytest.raises(ValueError, match="assessment result, disposition or digest mismatch"):
        apply_assessment(proposal, forged)


def test_forged_review_ready_without_all_required_tests_is_rejected():
    proposal = make_proposal()
    assessment = assess_improvement(proposal, {"test_schema": ResultStatus.PASS})
    forged = assessment.model_copy(
        update={"disposition": ImprovementState.HUMAN_REVIEW_REQUIRED}
    )
    with pytest.raises(ValueError, match="assessment result, disposition or digest mismatch"):
        apply_assessment(proposal, forged)


def test_assessment_rejects_duplicate_or_unknown_test_identifiers():
    proposal = make_proposal()
    assessment = assess_improvement(
        proposal,
        {"test_schema": ResultStatus.PASS, "test_fail_closed": ResultStatus.PASS},
    )
    duplicated = assessment.model_copy(
        update={"passed_tests": ["test_schema", "test_schema", "test_fail_closed"]}
    )
    with pytest.raises(ValueError, match="unknown or duplicate"):
        apply_assessment(proposal, duplicated)
    unexpected = assessment.model_copy(
        update={"passed_tests": ["test_schema", "test_fail_closed", "not_required"]}
    )
    with pytest.raises(ValueError, match="unknown or duplicate"):
        apply_assessment(proposal, unexpected)


def test_assessment_rejects_digest_metadata_and_omitted_results():
    proposal = make_proposal()
    assessment = assess_improvement(
        proposal,
        {"test_schema": ResultStatus.PASS, "test_fail_closed": ResultStatus.PASS},
    )
    altered_digest = assessment.model_copy(update={"assessment_digest": "0" * 64})
    with pytest.raises(ValueError, match="assessment result, disposition or digest mismatch"):
        apply_assessment(proposal, altered_digest)
    omitted = assessment.model_copy(update={"passed_tests": ["test_schema"]})
    with pytest.raises(ValueError, match="does not account for every required test"):
        apply_assessment(proposal, omitted)


def test_assessment_rejects_unfounded_execution_and_claim_flags():
    proposal = make_proposal()
    assessment = assess_improvement(
        proposal,
        {"test_schema": ResultStatus.PASS, "test_fail_closed": ResultStatus.PASS},
    )
    forged = assessment.model_copy(update={"external_execution_performed": True})
    with pytest.raises(ValueError, match="assessment result, disposition or digest mismatch"):
        apply_assessment(proposal, forged)
    forged = assessment.model_copy(update={"claim_promotion_performed": True})
    with pytest.raises(ValueError, match="assessment result, disposition or digest mismatch"):
        apply_assessment(proposal, forged)
