from __future__ import annotations

from datetime import UTC, datetime, timedelta

from worldshepherd_sara.ws_soe import (
    ConformanceStatus,
    Intent,
    Observation,
    assess_conformance,
    authorize_intent,
    canonical_sha256,
    make_evidence_receipt,
)


def _decision(intent: Intent, now: datetime):
    return authorize_intent(
        intent,
        decision_id="decision-precedence",
        authority="test-authority",
        decided_at=now - timedelta(milliseconds=500),
    )


def test_stale_does_not_mask_unsupported_conformance_rule():
    now = datetime(2026, 9, 30, 17, 0, 0, tzinfo=UTC)
    intent = Intent(
        intent_id="intent-unsupported",
        action="demo.counter.unmodeled",
        target="demo.counter",
        arguments={"delta": 1},
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=1),
        nonce="nonce-unsupported",
    )
    decision = _decision(intent, now)
    observation = Observation(
        observation_id="obs-unsupported",
        intent_hash=canonical_sha256(intent),
        action=intent.action,
        target=intent.target,
        observed_at=now,
        before={"counter": 41},
        after={"counter": 42},
        result={"applied_delta": 1},
    )
    receipt = make_evidence_receipt(
        intent,
        observation,
        receipt_id="receipt-unsupported",
        emitted_at=now,
    )

    assessment = assess_conformance(
        intent,
        decision=decision,
        observation=observation,
        receipts=[receipt],
        assessed_at=now + timedelta(seconds=31),
        max_observation_age=timedelta(seconds=30),
    )
    assert assessment.status == ConformanceStatus.UNKNOWN


def test_stale_does_not_mask_bound_outcome_deviation():
    now = datetime(2026, 9, 30, 17, 1, 0, tzinfo=UTC)
    intent = Intent(
        intent_id="intent-stale-deviation",
        action="demo.counter.increment",
        target="demo.counter",
        arguments={"delta": 1},
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=1),
        nonce="nonce-stale-deviation",
    )
    decision = _decision(intent, now)
    observation = Observation(
        observation_id="obs-stale-deviation",
        intent_hash=canonical_sha256(intent),
        action=intent.action,
        target=intent.target,
        observed_at=now,
        before={"counter": 41},
        after={"counter": 43},
        result={"applied_delta": 2},
    )
    receipt = make_evidence_receipt(
        intent,
        observation,
        receipt_id="receipt-stale-deviation",
        emitted_at=now,
    )

    assessment = assess_conformance(
        intent,
        decision=decision,
        observation=observation,
        receipts=[receipt],
        assessed_at=now + timedelta(seconds=31),
        max_observation_age=timedelta(seconds=30),
    )
    assert assessment.status == ConformanceStatus.DEVIATION


def test_stale_does_not_mask_missing_rule_evidence():
    now = datetime(2026, 9, 30, 17, 2, 0, tzinfo=UTC)
    intent = Intent(
        intent_id="intent-stale-unknown",
        action="demo.counter.increment",
        target="demo.counter",
        arguments={"delta": 1},
        issued_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=1),
        nonce="nonce-stale-unknown",
    )
    decision = _decision(intent, now)
    observation = Observation(
        observation_id="obs-stale-unknown",
        intent_hash=canonical_sha256(intent),
        action=intent.action,
        target=intent.target,
        observed_at=now,
        before={},
        after={},
        result={},
    )
    receipt = make_evidence_receipt(
        intent,
        observation,
        receipt_id="receipt-stale-unknown",
        emitted_at=now,
    )

    assessment = assess_conformance(
        intent,
        decision=decision,
        observation=observation,
        receipts=[receipt],
        assessed_at=now + timedelta(seconds=31),
        max_observation_age=timedelta(seconds=30),
    )
    assert assessment.status == ConformanceStatus.UNKNOWN
