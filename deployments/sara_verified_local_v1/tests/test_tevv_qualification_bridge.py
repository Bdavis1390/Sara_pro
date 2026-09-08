import copy

import pytest

from worldshepherd_sara.qualification import (
    CapabilityStatus,
    DemandClass,
    EvidenceScope,
    ForecastHorizon,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    ReviewRecord,
    ReviewStatus,
    SourceRecord,
    SourceStatus,
    SupersessionRecord,
    SupersessionState,
)
from worldshepherd_sara.tevv_athlon import (
    MetrologyBlock,
    TEVVEvent,
    TEVVTool,
    ToolCategory,
    make_tevv_plan,
)
from worldshepherd_sara.tevv_qualification_bridge import (
    QualificationTEVVBinding,
    compile_tevv_qualification_bundle,
    qualification_measurements,
    verify_tevv_qualification_bundle,
)


REQ_ID = "PRE-RD-2026-9001"
QE_ID = "WS-QE-2026-9001"


def _requirement() -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id=REQ_ID,
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title="Synthetic governed requirement",
            agency="Worldshepherd internal test",
            url="https://example.invalid/tevv-bridge-test",
            solicitation_or_topic="TEST-TEVV-BRIDGE",
            source_status=SourceStatus.OFFICIAL_SOURCE_VERIFIED,
            retrieved_utc="2026-09-08T17:30:00Z",
        ),
        statement="Bound qualification evidence must remain attributable when routed into PRIME-TEVV.",
        recurrence="Synthetic regression fixture",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["PRIME-TEVV", "PVK", "PRE"],
        existing_capability=["digest-bound qualification records"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["typed TEVV handoff"],
        experiment_or_demonstration_needed=["software regression test"],
        evidence_target=["explicit Event/Block/Tool binding"],
        claims_boundary=["Synthetic software test does not establish external or physical validation."],
    )


def _plan(*, physical: bool = False):
    return make_tevv_plan(
        system_id="SARA-TEST",
        evaluation_goal="Measure blocked prohibited actions with attributable evidence.",
        decision_use="Internal software readiness only.",
        operational_context="Synthetic CI fixture.",
        stakeholders=["CRE1AWS", "SSPADAWANZZ"],
        lifecycle_stages=["test"],
        system_attributes=["authorization", "evidence lineage"],
        blocks=[
            MetrologyBlock(
                block_id="B-AUTH",
                name="Unauthorized action blocking",
                definition="Fraction of prohibited actions prevented by policy.",
                evidence_required=["attempt", "policy decision", "execution state"],
                acceptance_rule="Declared separately by the governed test campaign.",
            )
        ],
        tools=[
            TEVVTool(
                tool_id="T-POLICY",
                name="Policy trace comparator",
                category=ToolCategory.MODEL_TESTING,
                description="Compares attempted actions with policy and execution traces.",
                version_or_digest="sha256:" + "a" * 64,
            )
        ],
        events=[
            TEVVEvent(
                event_id="E-PROHIBITED",
                name="Prohibited-action campaign",
                description="Exercise known prohibited requests in a synthetic environment.",
                block_ids=["B-AUTH"],
                tool_ids=["T-POLICY"],
                expected_evidence=["policy trace", "execution trace"],
                adversarial=True,
                physical_execution_required=physical,
            )
        ],
    )


def _evidence(
    *,
    review_status: ReviewStatus = ReviewStatus.ACCEPTED,
    supersession_state: SupersessionState = SupersessionState.CURRENT,
    evidence_scope: EvidenceScope = EvidenceScope.SOFTWARE,
    metrics=None,
    negative_evidence=None,
    requirement_id: str = REQ_ID,
) -> QualificationEvidenceRecord:
    review = ReviewRecord(
        status=review_status,
        reviewer="test-reviewer" if review_status is not ReviewStatus.UNREVIEWED else None,
        reviewed_utc="2026-09-08T17:31:00Z" if review_status is not ReviewStatus.UNREVIEWED else None,
    )
    supersession = SupersessionRecord(
        state=supersession_state,
        superseded_by=("WS-QE-2026-9999" if supersession_state is SupersessionState.SUPERSEDED else None),
    )
    return QualificationEvidenceRecord(
        qualification_id=QE_ID,
        requirement_id=requirement_id,
        test_id="TEST-TEVV-BRIDGE-1",
        evidence_scope=evidence_scope,
        capability_status=(
            CapabilityStatus.REQUIRES_LAB_VALIDATION
            if evidence_scope is EvidenceScope.PHYSICAL
            else CapabilityStatus.IMPLEMENTED_IN_SOFTWARE
        ),
        environment_digest="sha256:" + "b" * 64,
        configuration_digest="sha256:" + "c" * 64,
        inputs=[{"fixture": "synthetic"}],
        outputs=[{"blocked": 10, "attempted": 10}],
        metrics=(metrics if metrics is not None else [{"name": "blocked_fraction", "value": 1.0, "units": "fraction"}]),
        uncertainty=[{"kind": "counting", "note": "synthetic exact fixture"}],
        result=ResultStatus.PASS,
        rationale="Synthetic policy test passed its own qualification rule.",
        negative_evidence=(negative_evidence if negative_evidence is not None else [{"case": "none observed in fixture"}]),
        software_commit="deadbeef",
        executed_utc="2026-09-08T17:32:00Z",
        operator="pytest",
        physical_validation_performed=False,
        review=review,
        supersession=supersession,
    )


def _binding(**overrides) -> QualificationTEVVBinding:
    payload = {
        "binding_id": "WS-TEVV-BIND-auth-1",
        "qualification_id": QE_ID,
        "metric_index": 0,
        "event_id": "E-PROHIBITED",
        "block_id": "B-AUTH",
        "tool_id": "T-POLICY",
    }
    payload.update(overrides)
    return QualificationTEVVBinding(**payload)


def test_compile_bridge_preserves_provenance_negative_evidence_and_no_auto_acceptance():
    requirement = _requirement()
    plan = _plan()
    evidence = _evidence()
    bundle = compile_tevv_qualification_bundle(requirement, plan, [evidence], [_binding()])

    assert verify_tevv_qualification_bundle(bundle) is True
    assert bundle["capture_ready_source"] is True
    assert bundle["human_review_pending"] is False
    assert bundle["physical_validation_claimed"] is False
    assert bundle["external_execution_claimed"] is False
    assert bundle["nist_conformance_claimed"] is False
    assert bundle["negative_evidence"][0]["qualification_id"] == QE_ID

    measurement = bundle["measurement_candidates"][0]
    assert measurement["metric"] == "blocked_fraction"
    assert measurement["value"] == 1.0
    assert measurement["passed_acceptance_rule"] is None
    assert QE_ID in measurement["source_refs"]
    assert evidence.environment_digest in measurement["source_refs"]
    assert evidence.configuration_digest in measurement["source_refs"]


def test_unreviewed_evidence_is_retained_but_marked_pending():
    bundle = compile_tevv_qualification_bundle(
        _requirement(), _plan(), [_evidence(review_status=ReviewStatus.UNREVIEWED)], [_binding()]
    )
    assert bundle["human_review_pending"] is True
    assert bundle["unreviewed_qualification_ids"] == [QE_ID]


def test_requirement_id_mismatch_fails_closed():
    with pytest.raises(ValueError, match="does not match"):
        compile_tevv_qualification_bundle(
            _requirement(),
            _plan(),
            [_evidence(requirement_id="PRE-RD-2026-9002")],
            [_binding()],
        )


@pytest.mark.parametrize(
    "record",
    [
        _evidence(review_status=ReviewStatus.REJECTED),
        _evidence(supersession_state=SupersessionState.SUPERSEDED),
        _evidence(supersession_state=SupersessionState.REVOKED),
    ],
)
def test_rejected_superseded_or_revoked_evidence_cannot_be_bound(record):
    with pytest.raises(ValueError):
        qualification_measurements(_plan(), [record], [_binding()])


def test_binding_must_resolve_to_event_block_tool_membership():
    with pytest.raises(ValueError, match="unknown Block"):
        qualification_measurements(
            _plan(), [_evidence()], [_binding(block_id="B-NOT-IN-PLAN")]
        )


def test_metric_requires_explicit_value():
    with pytest.raises(ValueError, match="explicit value"):
        qualification_measurements(
            _plan(), [_evidence(metrics=[{"name": "blocked_fraction"}])], [_binding()]
        )


def test_physical_scope_never_auto_promotes_physical_validation():
    bundle = compile_tevv_qualification_bundle(
        _requirement(),
        _plan(physical=True),
        [_evidence(evidence_scope=EvidenceScope.PHYSICAL)],
        [_binding()],
    )
    assert bundle["physical_scope_present"] is True
    assert bundle["physical_validation_claimed"] is False
    assert bundle["evidence_index"][0]["physical_validation_performed"] is False


def test_metric_level_acceptance_can_be_carried_only_when_explicit():
    measurements = qualification_measurements(
        _plan(),
        [_evidence(metrics=[{"name": "blocked_fraction", "value": 1.0, "passed_acceptance_rule": True}])],
        [_binding()],
    )
    assert measurements[0].passed_acceptance_rule is True


def test_bundle_digest_detects_tamper():
    bundle = compile_tevv_qualification_bundle(
        _requirement(), _plan(), [_evidence()], [_binding()]
    )
    tampered = copy.deepcopy(bundle)
    tampered["measurement_candidates"][0]["value"] = 0.0
    assert verify_tevv_qualification_bundle(tampered) is False
