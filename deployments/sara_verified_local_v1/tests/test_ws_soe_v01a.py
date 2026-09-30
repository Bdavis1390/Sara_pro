from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from worldshepherd_sara.ws_soe import (
    AuthorizationError,
    ConformanceStatus,
    DecisionOutcome,
    DemoCounterExecutor,
    ExpiredIntentError,
    Intent,
    Observation,
    ReplayError,
    assess_conformance,
    authorize_intent,
    canonical_sha256,
    make_evidence_receipt,
)


def _intent(now: datetime) -> Intent:
    return Intent(
        intent_id="intent-demo-001",
        action="demo.counter.increment",
        target="demo.counter",
        arguments={"delta": 1},
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=1),
        nonce="nonce-demo-001",
    )


def _decision(intent: Intent, now: datetime, outcome: DecisionOutcome = DecisionOutcome.ALLOW):
    return authorize_intent(
        intent,
        decision_id="decision-demo-001",
        authority="test-authority",
        decided_at=now - timedelta(milliseconds=500),
        outcome=outcome,
    )


def test_demo_counter_increment_41_to_42_is_match():
    now = datetime(2026, 9, 30, 16, 0, 0, tzinfo=UTC)
    intent = _intent(now)
    decision = _decision(intent, now)
    executor = DemoCounterExecutor(initial_value=41)

    observation = executor.execute(intent, decision, now=now, observation_id="obs-demo-001")
    assert observation.before == {"counter": 41}
    assert observation.after == {"counter": 42}
    assert executor.value == 42

    receipt = make_evidence_receipt(
        intent,
        observation,
        receipt_id="receipt-demo-001",
        emitted_at=now + timedelta(milliseconds=1),
    )
    assessment = assess_conformance(
        intent,
        decision=decision,
        observation=observation,
        receipts=[receipt],
        assessed_at=now + timedelta(seconds=1),
    )
    assert assessment.status == ConformanceStatus.MATCH
    assert assessment.decision_hash == canonical_sha256(decision)
    assert assessment.observation_hash == canonical_sha256(observation)
    assert assessment.evidence_hash == canonical_sha256(receipt)


def test_canonical_hash_is_stable_across_mapping_key_order():
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}
    assert canonical_sha256(left) == canonical_sha256(right)


def test_mutation_after_authorization_breaks_exact_intent_binding():
    now = datetime(2026, 9, 30, 16, 1, 0, tzinfo=UTC)
    intent = _intent(now)
    decision = _decision(intent, now)
    intent.arguments["delta"] = 2

    with pytest.raises(AuthorizationError, match="exact current intent"):
        DemoCounterExecutor().execute(intent, decision, now=now, observation_id="obs-mutated")


def test_replay_is_rejected_after_successful_execution():
    now = datetime(2026, 9, 30, 16, 2, 0, tzinfo=UTC)
    intent = _intent(now)
    decision = _decision(intent, now)
    executor = DemoCounterExecutor()
    executor.execute(intent, decision, now=now, observation_id="obs-first")

    with pytest.raises(ReplayError):
        executor.execute(intent, decision, now=now + timedelta(seconds=1), observation_id="obs-replay")


def test_target_substitution_breaks_exact_intent_binding():
    now = datetime(2026, 9, 30, 16, 3, 0, tzinfo=UTC)
    original = _intent(now)
    decision = _decision(original, now)
    substituted = original.model_copy(update={"target": "demo.counter.shadow"})

    with pytest.raises(AuthorizationError, match="exact current intent"):
        DemoCounterExecutor().execute(substituted, decision, now=now, observation_id="obs-substitute")


def test_expired_intent_is_rejected_at_boundary():
    now = datetime(2026, 9, 30, 16, 4, 0, tzinfo=UTC)
    intent = _intent(now)
    decision = _decision(intent, now)

    with pytest.raises(ExpiredIntentError):
        DemoCounterExecutor().execute(
            intent,
            decision,
            now=intent.expires_at,
            observation_id="obs-expired",
        )


def test_stale_observation_remains_distinct_from_match():
    now = datetime(2026, 9, 30, 16, 5, 0, tzinfo=UTC)
    intent = _intent(now)
    decision = _decision(intent, now)
    observation = DemoCounterExecutor().execute(intent, decision, now=now, observation_id="obs-stale")
    receipt = make_evidence_receipt(intent, observation, receipt_id="receipt-stale", emitted_at=now)

    assessment = assess_conformance(
        intent,
        decision=decision,
        observation=observation,
        receipts=[receipt],
        assessed_at=now + timedelta(seconds=31),
        max_observation_age=timedelta(seconds=30),
    )
    assert assessment.status == ConformanceStatus.STALE
    assert assessment.status != ConformanceStatus.MATCH


def test_evidence_chain_corruption_is_conflict():
    now = datetime(2026, 9, 30, 16, 6, 0, tzinfo=UTC)
    intent = _intent(now)
    decision = _decision(intent, now)
    observation = DemoCounterExecutor().execute(intent, decision, now=now, observation_id="obs-chain")
    receipt = make_evidence_receipt(intent, observation, receipt_id="receipt-chain", emitted_at=now)
    corrupted = receipt.model_copy(update={"previous_receipt_hash": "sha256:" + "0" * 64})

    assessment = assess_conformance(
        intent,
        decision=decision,
        observation=observation,
        receipts=[corrupted],
        assessed_at=now + timedelta(seconds=1),
    )
    assert assessment.status == ConformanceStatus.CONFLICT


def test_unknown_never_collapses_into_match_when_observation_is_missing():
    now = datetime(2026, 9, 30, 16, 7, 0, tzinfo=UTC)
    intent = _intent(now)
    decision = _decision(intent, now)
    assessment = assess_conformance(
        intent,
        decision=decision,
        observation=None,
        assessed_at=now,
    )
    assert assessment.status == ConformanceStatus.UNKNOWN
    assert assessment.status != ConformanceStatus.MATCH


def test_deviation_is_distinct_when_bound_outcome_is_wrong():
    now = datetime(2026, 9, 30, 16, 8, 0, tzinfo=UTC)
    intent = _intent(now)
    decision = _decision(intent, now)
    observation = Observation(
        observation_id="obs-deviation",
        intent_hash=canonical_sha256(intent),
        action=intent.action,
        target=intent.target,
        observed_at=now,
        before={"counter": 41},
        after={"counter": 43},
        result={"applied_delta": 2},
    )
    receipt = make_evidence_receipt(intent, observation, receipt_id="receipt-deviation", emitted_at=now)
    assessment = assess_conformance(
        intent,
        decision=decision,
        observation=observation,
        receipts=[receipt],
        assessed_at=now + timedelta(seconds=1),
    )
    assert assessment.status == ConformanceStatus.DEVIATION


def test_violation_is_distinct_when_execution_is_observed_after_deny():
    now = datetime(2026, 9, 30, 16, 9, 0, tzinfo=UTC)
    intent = _intent(now)
    denied = _decision(intent, now, outcome=DecisionOutcome.DENY)
    observation = Observation(
        observation_id="obs-denied",
        intent_hash=canonical_sha256(intent),
        action=intent.action,
        target=intent.target,
        observed_at=now,
        before={"counter": 41},
        after={"counter": 42},
        result={"applied_delta": 1},
    )
    receipt = make_evidence_receipt(intent, observation, receipt_id="receipt-denied", emitted_at=now)
    assessment = assess_conformance(
        intent,
        decision=denied,
        observation=observation,
        receipts=[receipt],
        assessed_at=now + timedelta(seconds=1),
    )
    assert assessment.status == ConformanceStatus.VIOLATION


def test_all_six_conformance_states_remain_explicit():
    assert {state.value for state in ConformanceStatus} == {
        "MATCH",
        "DEVIATION",
        "VIOLATION",
        "UNKNOWN",
        "STALE",
        "CONFLICT",
    }
