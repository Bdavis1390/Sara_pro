from worldshepherd_sara.evidence_improvement import evidence_to_improvement
from worldshepherd_sara.improvement_cycle import ImprovementRisk, ImprovementState, ImprovementTriggerKind
from worldshepherd_sara.improvement_routing import ImprovementRoute, route_improvement
from worldshepherd_sara.qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    ResultStatus,
    ReviewRecord,
    ReviewStatus,
)


def make_record(**overrides):
    payload = {
        "qualification_id": "WS-QE-2026-9100",
        "requirement_id": "PRE-RD-2026-9001",
        "test_id": "ddil-rejoin-qualification",
        "evidence_scope": EvidenceScope.SOFTWARE,
        "capability_status": CapabilityStatus.IMPLEMENTED_IN_SOFTWARE,
        "environment_digest": "sha256:environment",
        "configuration_digest": "sha256:configuration",
        "inputs": [{"scenario": "partition-rejoin"}],
        "outputs": [{"event_count": 10}],
        "metrics": [{"integrity": 1.0}],
        "uncertainty": [{"clock_skew_ms": 2.0}],
        "result": ResultStatus.FAIL,
        "rationale": "One required integrity assertion failed.",
        "negative_evidence": [{"failed_assertion": "event-order-preserved"}],
        "software_commit": "deadbeef",
        "executed_utc": "2026-09-12T21:20:00Z",
        "operator": "CI",
        "physical_validation_performed": False,
        "review": ReviewRecord(status=ReviewStatus.UNREVIEWED),
    }
    payload.update(overrides)
    return QualificationEvidenceRecord(**payload)


def test_failed_evidence_creates_high_risk_failure_candidate_and_preserves_negative_evidence():
    record = make_record()
    proposal = evidence_to_improvement(
        record,
        created_utc="2026-09-12T21:30:00Z",
        affected_lanes=["DDIL"],
    )

    assert proposal.state == ImprovementState.PROPOSED
    assert proposal.trigger_kind == ImprovementTriggerKind.FAILURE
    assert proposal.risk_level == ImprovementRisk.HIGH
    assert proposal.baseline_capability_status == [CapabilityStatus.IMPLEMENTED_IN_SOFTWARE]
    assert proposal.target_capability_status is None
    assert {"failed_assertion": "event-order-preserved"} in proposal.negative_evidence
    assert f"{record.qualification_id}:root-cause-gate" in proposal.required_tests
    assert not proposal.requested_claim_promotion
    assert not proposal.requested_external_execution


def test_inconclusive_evidence_requires_uncertainty_resolution_without_directional_claim():
    record = make_record(result=ResultStatus.INCONCLUSIVE, negative_evidence=[])
    proposal = evidence_to_improvement(
        record,
        created_utc="2026-09-12T21:30:00Z",
    )

    assert proposal.trigger_kind == ImprovementTriggerKind.TEST_RESULT
    assert proposal.risk_level == ImprovementRisk.MODERATE
    assert f"{record.qualification_id}:uncertainty-resolution-gate" in proposal.required_tests
    assert any("no directional capability conclusion" in risk for risk in proposal.risks)


def test_passing_evidence_remains_scoped_and_does_not_auto_promote_maturity():
    record = make_record(
        result=ResultStatus.PASS,
        review=ReviewRecord(
            status=ReviewStatus.ACCEPTED,
            reviewer="CRE1AWS",
            reviewed_utc="2026-09-12T21:25:00Z",
        ),
        negative_evidence=[],
    )
    proposal = evidence_to_improvement(
        record,
        created_utc="2026-09-12T21:30:00Z",
    )

    assert proposal.trigger_kind == ImprovementTriggerKind.TEST_RESULT
    assert proposal.risk_level == ImprovementRisk.LOW
    assert proposal.baseline_capability_status == [CapabilityStatus.IMPLEMENTED_IN_SOFTWARE]
    assert proposal.target_capability_status is None
    assert "passing qualification result" in proposal.proposed_change


def test_failure_feedback_routes_to_assurance_and_monitoring_without_execution_authority():
    proposal = evidence_to_improvement(
        make_record(),
        created_utc="2026-09-12T21:30:00Z",
        affected_lanes=["DDIL"],
    )
    envelope = route_improvement(proposal)

    assert ImprovementRoute.ECHO in envelope.routes
    assert ImprovementRoute.PRIME_TEVV in envelope.routes
    assert ImprovementRoute.PRIME in envelope.routes
    assert ImprovementRoute.OVERWATCH in envelope.routes
    assert ImprovementRoute.RED_TEAM in envelope.routes
    assert ImprovementRoute.CONFIG_CUSTODY not in envelope.routes
    assert not envelope.deployment_authorized
    assert not envelope.external_execution_performed
