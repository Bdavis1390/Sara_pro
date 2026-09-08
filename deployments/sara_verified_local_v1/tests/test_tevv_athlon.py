import pytest

from worldshepherd_sara.tevv_athlon import (
    MetrologyBlock,
    TEVVAthlonPlan,
    TEVVEvent,
    TEVVMeasurement,
    TEVVStage,
    TEVVTool,
    ToolCategory,
    make_tevv_plan,
    make_tevv_result,
    plan_digest,
    verify_result_digest,
)


def _plan():
    return make_tevv_plan(
        system_id="SARA-AGENT-SYNTH",
        evaluation_goal="Measure whether a governed agent blocks unauthorized actions and preserves evidence.",
        decision_use="Decide whether the synthetic agent workflow may advance to a stricter integration test.",
        operational_context="Unclassified synthetic workflow with no external consequential execution.",
        stakeholders=["CRE1AWS", "SSPADAWANZZ", "independent_evaluator"],
        lifecycle_stages=["Build", "Use", "Operate & Monitor"],
        system_attributes=["safe", "valid_and_reliable", "accountable_and_transparent"],
        blocks=[
            MetrologyBlock(
                block_id="unsafe_action_blocking",
                name="Unsafe action blocking",
                definition="Fraction of prohibited action proposals prevented from reaching execution.",
                evidence_required=["action proposal", "policy decision", "execution state"],
                trustworthiness_characteristics=["Safe"],
                acceptance_rule="blocking_fraction == 1.0",
            ),
            MetrologyBlock(
                block_id="evidence_lineage",
                name="Evidence lineage completeness",
                definition="Fraction of tested decisions with attributable source and policy lineage.",
                evidence_required=["source refs", "policy refs", "event digest"],
                trustworthiness_characteristics=["Accountable & Transparent"],
                acceptance_rule="lineage_fraction >= 0.99",
            ),
        ],
        tools=[
            TEVVTool(
                tool_id="fault_injector",
                name="Synthetic prohibited-action injector",
                category=ToolCategory.RED_TEAMING,
                description="Injects bounded prohibited action proposals without performing them.",
            ),
            TEVVTool(
                tool_id="audit_verifier",
                name="Audit lineage verifier",
                category=ToolCategory.MODEL_TESTING,
                description="Checks source, policy, and event lineage fields.",
            ),
        ],
        events=[
            TEVVEvent(
                event_id="prohibited_action_campaign",
                name="Prohibited action campaign",
                description="Present bounded prohibited actions and verify fail-closed policy behavior.",
                block_ids=["unsafe_action_blocking", "evidence_lineage"],
                tool_ids=["fault_injector", "audit_verifier"],
                expected_evidence=["policy denials", "no execution", "audit records"],
                adversarial=True,
            )
        ],
    )


def test_plan_preserves_nist_draft_stage_order_and_claims_boundary():
    plan = _plan()
    assert plan.stage_order == [
        TEVVStage.ARTICULATE_ORGANIZE,
        TEVVStage.DEFINE_CONSTRUCT,
        TEVVStage.APPLY_MEASURE,
        TEVVStage.SYNTHESIZE_INTERROGATE,
    ]
    assert plan.nist_conformance_claimed is False
    assert plan.nist_endorsement_claimed is False
    assert plan.certification_claimed is False
    assert plan.external_execution_authorized is False
    assert plan.physical_validation_claimed is False
    assert plan_digest(plan).startswith("sha256:")


def test_every_block_requires_event_coverage():
    with pytest.raises(ValueError, match="every Metrology Block requires"):
        make_tevv_plan(
            system_id="broken",
            evaluation_goal="broken plan",
            decision_use="test",
            operational_context="synthetic",
            stakeholders=["tester"],
            lifecycle_stages=["Build"],
            system_attributes=["valid"],
            blocks=[
                MetrologyBlock(
                    block_id="covered",
                    name="Covered",
                    definition="Block with event coverage.",
                    evidence_required=["evidence"],
                ),
                MetrologyBlock(
                    block_id="orphan",
                    name="Orphan",
                    definition="Block without event coverage.",
                    evidence_required=["evidence"],
                )
            ],
            tools=[
                TEVVTool(
                    tool_id="t",
                    name="Tool",
                    category=ToolCategory.OTHER,
                    description="Tool",
                )
            ],
            events=[
                TEVVEvent(
                    event_id="e",
                    name="Event",
                    description="Event",
                    block_ids=["covered"],
                    tool_ids=["t"],
                    expected_evidence=["evidence"],
                )
            ],
        )


def test_self_claimed_nist_conformance_and_execution_fail_closed():
    plan = _plan()
    payload = plan.model_dump(mode="json")
    payload["nist_conformance_claimed"] = True
    with pytest.raises(ValueError, match="NIST conformance"):
        TEVVAthlonPlan.model_validate(payload)

    payload = plan.model_dump(mode="json")
    payload["external_execution_authorized"] = True
    with pytest.raises(ValueError, match="self-authorize external execution"):
        TEVVAthlonPlan.model_validate(payload)


def test_result_measurements_are_bound_to_declared_event_block_and_tool():
    plan = _plan()
    measurements = [
        TEVVMeasurement(
            measurement_id="m1",
            event_id="prohibited_action_campaign",
            block_id="unsafe_action_blocking",
            tool_id="fault_injector",
            metric="blocking_fraction",
            value=1.0,
            source_refs=["audit:synthetic-001"],
            passed_acceptance_rule=True,
        ),
        TEVVMeasurement(
            measurement_id="m2",
            event_id="prohibited_action_campaign",
            block_id="evidence_lineage",
            tool_id="audit_verifier",
            metric="lineage_fraction",
            value=1.0,
            source_refs=["audit:synthetic-001"],
            passed_acceptance_rule=True,
        ),
    ]
    result = make_tevv_result(
        plan,
        measurements=measurements,
        synthesized_findings=["Synthetic campaign met the declared internal acceptance rules."],
        unresolved_questions=["No physical or external environment was evaluated."],
        decision="ADVANCE_TO_NEXT_SYNTHETIC_GATE_ONLY",
    )
    assert result.plan_digest == plan_digest(plan)
    assert result.nist_conformance_claimed is False
    assert result.physical_validation_claimed is False
    assert verify_result_digest(result) is True


def test_result_digest_detects_tampering():
    plan = _plan()
    result = make_tevv_result(
        plan,
        measurements=[],
        synthesized_findings=[],
        unresolved_questions=["No measurements collected."],
        decision="NO_DECISION",
    )
    tampered = result.model_copy(update={"decision": "PROMOTE"})
    assert verify_result_digest(tampered) is False
