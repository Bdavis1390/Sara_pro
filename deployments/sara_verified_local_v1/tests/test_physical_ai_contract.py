from worldshepherd_sara.physical_ai_contract import (
    DegradedState,
    PhysicalActionDecision,
    PhysicalActionPolicy,
    PhysicalActionRequest,
    evaluate_physical_action,
    transition_allowed,
)


def policy() -> PhysicalActionPolicy:
    return PhysicalActionPolicy(
        policy_id="WS-PA-POLICY-001",
        allowed_action_types=["navigate", "safe_hold", "recover", "dock"],
        denied_action_types=["unsafe_override"],
        human_approval_action_types=["dock"],
        bounded_local_action_types=["navigate", "safe_hold"],
        minimum_confidence=0.80,
        minimum_battery_soc=0.25,
        maximum_telemetry_age_s=2.0,
        maximum_auto_authority=1,
        require_reversible=True,
        require_model_digest=True,
        require_configuration_digest=True,
    )


def request(**overrides) -> PhysicalActionRequest:
    values = {
        "asset_id": "ugv-001",
        "mission_id": "WS-PHYAI-DEMO-001",
        "action_id": "ACT-001",
        "action_type": "navigate",
        "confidence": 0.95,
        "requested_authority": 1,
        "reversible": True,
        "battery_soc": 0.80,
        "telemetry_age_s": 0.10,
        "degraded_state": DegradedState.NORMAL,
        "bounded_local_mode": False,
        "model_digest": "sha256:model",
        "configuration_digest": "sha256:config",
        "observation_digest": "sha256:obs",
    }
    values.update(overrides)
    return PhysicalActionRequest(**values)


def test_pa_001_valid_action_is_allowed():
    result = evaluate_physical_action(request(), policy())
    assert result.decision is PhysicalActionDecision.ALLOW


def test_pa_002_explicitly_denied_action_is_rejected():
    result = evaluate_physical_action(
        request(action_type="unsafe_override"), policy()
    )
    assert result.decision is PhysicalActionDecision.DENY


def test_pa_003_stale_telemetry_defers_execution():
    result = evaluate_physical_action(request(telemetry_age_s=9.0), policy())
    assert result.decision is PhysicalActionDecision.DEFER
    assert "telemetry is stale" in result.reasons


def test_pa_004_low_battery_enters_safe_hold():
    result = evaluate_physical_action(request(battery_soc=0.10), policy())
    assert result.decision is PhysicalActionDecision.SAFE_HOLD


def test_pa_005_missing_model_digest_defers_execution():
    result = evaluate_physical_action(request(model_digest=None), policy())
    assert result.decision is PhysicalActionDecision.DEFER
    assert "model digest is required" in result.reasons


def test_pa_006_missing_configuration_digest_defers_execution():
    result = evaluate_physical_action(request(configuration_digest=None), policy())
    assert result.decision is PhysicalActionDecision.DEFER
    assert "configuration digest is required" in result.reasons


def test_pa_007_degraded_bounded_local_action_is_limited():
    result = evaluate_physical_action(
        request(
            degraded_state=DegradedState.DEGRADED,
            bounded_local_mode=True,
        ),
        policy(),
    )
    assert result.decision is PhysicalActionDecision.ALLOW_WITH_LIMITS
    assert result.effective_limits["bounded_local_mode"] is True


def test_pa_008_degraded_unbounded_action_enters_safe_hold():
    result = evaluate_physical_action(
        request(degraded_state=DegradedState.DEGRADED), policy()
    )
    assert result.decision is PhysicalActionDecision.SAFE_HOLD


def test_pa_009_human_approval_action_is_not_auto_executed():
    result = evaluate_physical_action(request(action_type="dock"), policy())
    assert result.decision is PhysicalActionDecision.HUMAN_APPROVAL


def test_pa_010_emergency_stop_is_absorbing_for_actions():
    result = evaluate_physical_action(
        request(degraded_state=DegradedState.EMERGENCY_STOP), policy()
    )
    assert result.decision is PhysicalActionDecision.DENY


def test_pa_011_recovery_actions_remain_limited():
    result = evaluate_physical_action(
        request(degraded_state=DegradedState.RECOVERY), policy()
    )
    assert result.decision is PhysicalActionDecision.ALLOW_WITH_LIMITS
    assert result.effective_limits["recovery_mode"] is True


def test_pa_012_degraded_state_transition_rules_are_bounded():
    assert transition_allowed(DegradedState.NORMAL, DegradedState.DEGRADED)
    assert transition_allowed(DegradedState.DEGRADED, DegradedState.RECOVERY)
    assert transition_allowed(DegradedState.RECOVERY, DegradedState.NORMAL)
    assert not transition_allowed(
        DegradedState.EMERGENCY_STOP, DegradedState.NORMAL
    )
