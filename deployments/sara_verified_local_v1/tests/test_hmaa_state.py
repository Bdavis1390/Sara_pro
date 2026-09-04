from __future__ import annotations

from datetime import datetime, timedelta, timezone

from worldshepherd_sara.hmaa import AssuranceDisposition, HMAAEvent
from worldshepherd_sara.hmaa_state import HMAAAssuranceState


BASE = datetime(2026, 9, 4, 20, 0, tzinfo=timezone.utc)


def _event(
    event_id: str,
    *,
    offset_seconds: int = 0,
    payload: dict[str, object] | None = None,
) -> HMAAEvent:
    return HMAAEvent(
        event_id=event_id,
        mission_id="SIM-STATE-001",
        source_system="synthetic-sil",
        entity_id="AIRCRAFT-SIM-1",
        event_type="ENTITY_UPDATE",
        source_timestamp=BASE + timedelta(seconds=offset_seconds),
        ingest_timestamp=BASE + timedelta(seconds=max(offset_seconds, 0)),
        payload=payload or {"health": "nominal"},
    )


def test_replayed_source_event_is_deduplicated_and_warned():
    state = HMAAAssuranceState()
    first = _event("E-1")
    _, first_assessment = state.assess(first)
    observation, replay_assessment = state.assess(first)

    assert first_assessment.disposition == AssuranceDisposition.ALLOW
    assert observation.replay.duplicate_event is True
    assert observation.replay.conflicting_replay is False
    assert replay_assessment.disposition == AssuranceDisposition.WARN


def test_conflicting_replay_requires_review():
    state = HMAAAssuranceState()
    state.assess(_event("E-1", payload={"health": "nominal"}))
    observation, assessment = state.assess(
        _event("E-1", payload={"health": "unexpected-change"})
    )

    assert observation.replay.duplicate_event is False
    assert observation.replay.conflicting_replay is True
    assert assessment.disposition == AssuranceDisposition.REVIEW
    assert any("conflicting" in reason for reason in assessment.reasons)


def test_clock_skew_tolerance_accepts_small_reordering_but_flags_large_reordering():
    state = HMAAAssuranceState(clock_skew_tolerance_seconds=2.0)
    state.assess(_event("E-10", offset_seconds=10))

    within_tolerance, within_assessment = state.assess(
        _event("E-9", offset_seconds=9)
    )
    outside_tolerance, outside_assessment = state.assess(
        _event("E-6", offset_seconds=6)
    )

    assert within_tolerance.chronology.skew_seconds == 1.0
    assert within_tolerance.chronology.out_of_order_event is False
    assert within_assessment.disposition == AssuranceDisposition.ALLOW

    assert outside_tolerance.chronology.skew_seconds == 4.0
    assert outside_tolerance.chronology.out_of_order_event is True
    assert outside_assessment.disposition == AssuranceDisposition.REVIEW


def test_state_snapshot_exposes_counts_not_source_payloads():
    state = HMAAAssuranceState()
    state.assess(_event("E-1", payload={"sensitive": "not-for-snapshot"}))
    snapshot = state.snapshot()

    assert snapshot["deduplication_identities"] == 1
    assert snapshot["chronology_scopes"] == 1
    assert "sensitive" not in repr(snapshot)
