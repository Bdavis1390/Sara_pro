from __future__ import annotations

from worldshepherd_sara.autonomy_policy import (
    AutonomousActionCandidate,
    AutonomyPolicy,
    ExecutionDisposition,
    evaluate_candidate,
)


def test_low_risk_reversible_allowlisted_action_can_be_auto_eligible():
    policy = AutonomyPolicy(
        policy_id="POL-1",
        allowed_auto_action_types=["refresh_cache"],
        denied_action_types=["release_payload"],
        minimum_auto_confidence=0.99,
        maximum_auto_authority=1,
    )
    candidate = AutonomousActionCandidate(action_id="A1", action_type="refresh_cache", confidence=1.0, requested_authority=1, reversible=True)
    disposition, reasons = evaluate_candidate(candidate, policy)
    assert disposition == ExecutionDisposition.AUTO_ELIGIBLE
    assert reasons


def test_non_allowlisted_or_high_authority_action_requires_human_review():
    policy = AutonomyPolicy(policy_id="POL-1", allowed_auto_action_types=["refresh_cache"], minimum_auto_confidence=0.9, maximum_auto_authority=1)
    candidate = AutonomousActionCandidate(action_id="A2", action_type="reroute_vehicle", confidence=0.95, requested_authority=2, reversible=True)
    disposition, reasons = evaluate_candidate(candidate, policy)
    assert disposition == ExecutionDisposition.HUMAN_REVIEW_REQUIRED
    assert any("allowlist" in reason for reason in reasons)
    assert any("authority" in reason for reason in reasons)


def test_explicitly_denied_action_fails_closed():
    policy = AutonomyPolicy(policy_id="POL-1", denied_action_types=["release_payload"])
    candidate = AutonomousActionCandidate(action_id="A3", action_type="release_payload", confidence=1.0, requested_authority=0, reversible=True)
    disposition, _ = evaluate_candidate(candidate, policy)
    assert disposition == ExecutionDisposition.DENIED
