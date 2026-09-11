from __future__ import annotations

from worldshepherd_sara.fasa import (
    CapabilityLevel,
    CapabilityRegistryEntry,
    FrontierActionCandidate,
    FrontierDisposition,
    FrontierSafetyPolicy,
    evaluate_frontier_action,
)


def _registry(
    *,
    assessed: CapabilityLevel = CapabilityLevel.F4,
    authorized: CapabilityLevel = CapabilityLevel.F4,
    current: bool = True,
) -> CapabilityRegistryEntry:
    return CapabilityRegistryEntry(
        model_id="model-A",
        model_version="1.0",
        assessed_level=assessed,
        maximum_authorized_level=authorized,
        evaluation_id="EVAL-001",
        evaluation_current=current,
    )


def _candidate(**overrides) -> FrontierActionCandidate:
    values = {
        "action_id": "ACT-001",
        "model_id": "model-A",
        "model_version": "1.0",
        "capability_level": CapabilityLevel.F2,
        "reversible": True,
    }
    values.update(overrides)
    return FrontierActionCandidate(**values)


def test_f2_bounded_reversible_action_can_pass_without_human_review():
    disposition, reasons = evaluate_frontier_action(
        _candidate(), _registry(), FrontierSafetyPolicy(policy_id="WS-FASA-001")
    )
    assert disposition == FrontierDisposition.ALLOW
    assert reasons


def test_f3_action_requires_human_approval():
    disposition, reasons = evaluate_frontier_action(
        _candidate(capability_level=CapabilityLevel.F3),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
    )
    assert disposition == FrontierDisposition.HUMAN_REVIEW_REQUIRED
    assert any("human approval" in reason for reason in reasons)


def test_f3_action_can_pass_after_human_approval_when_other_gates_pass():
    disposition, _ = evaluate_frontier_action(
        _candidate(capability_level=CapabilityLevel.F3, human_approval_present=True),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
    )
    assert disposition == FrontierDisposition.ALLOW


def test_missing_provenance_or_overwatch_fails_closed():
    policy = FrontierSafetyPolicy(policy_id="WS-FASA-001")
    disposition, reasons = evaluate_frontier_action(
        _candidate(provenance_enabled=False, overwatch_enabled=False),
        _registry(),
        policy,
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("provenance" in reason for reason in reasons)
    assert any("OVERWATCH" in reason for reason in reasons)


def test_self_authorization_and_monitor_suppression_are_hard_denials():
    disposition, reasons = evaluate_frontier_action(
        _candidate(self_authorization_attempt=True, monitoring_suppression_attempt=True),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("self-authorization" in reason for reason in reasons)
    assert any("monitoring suppression" in reason for reason in reasons)


def test_action_above_registry_authorization_is_denied():
    disposition, reasons = evaluate_frontier_action(
        _candidate(capability_level=CapabilityLevel.F4),
        _registry(assessed=CapabilityLevel.F4, authorized=CapabilityLevel.F3),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("maximum authorized" in reason for reason in reasons)


def test_f4_requires_current_safety_case_and_independent_review():
    disposition, reasons = evaluate_frontier_action(
        _candidate(capability_level=CapabilityLevel.F4, human_approval_present=True),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("safety case" in reason for reason in reasons)
    assert any("independent review" in reason for reason in reasons)


def test_f4_can_pass_only_with_human_safety_case_and_independent_review():
    disposition, _ = evaluate_frontier_action(
        _candidate(
            capability_level=CapabilityLevel.F4,
            human_approval_present=True,
            safety_case_current=True,
            independent_review_current=True,
        ),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
    )
    assert disposition == FrontierDisposition.ALLOW


def test_f5_is_denied_by_default_even_when_other_gates_are_present():
    disposition, reasons = evaluate_frontier_action(
        _candidate(
            capability_level=CapabilityLevel.F5,
            human_approval_present=True,
            safety_case_current=True,
            independent_review_current=True,
        ),
        _registry(assessed=CapabilityLevel.F5, authorized=CapabilityLevel.F5),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("F5 execution is disabled" in reason for reason in reasons)


def test_model_version_mismatch_and_stale_evaluation_are_denied():
    disposition, reasons = evaluate_frontier_action(
        _candidate(model_version="2.0"),
        _registry(current=False),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
    )
    assert disposition == FrontierDisposition.DENIED
    assert any("identity/version" in reason for reason in reasons)
    assert any("not current" in reason for reason in reasons)
