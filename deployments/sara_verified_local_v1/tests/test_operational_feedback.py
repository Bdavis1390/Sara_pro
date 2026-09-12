import pytest
from pydantic import ValidationError

from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.improvement_cycle import ImprovementRisk, ImprovementTriggerKind
from worldshepherd_sara.improvement_feedback import (
    ImprovementFeedbackCursor,
    ImprovementFeedbackPolicy,
    run_operational_feedback_cycle,
)
from worldshepherd_sara.improvement_ledger import ImprovementLedger
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.operational_improvement import (
    OperationalImprovementSignalError,
    audit_event_to_improvement,
    stored_echo_event_to_improvement,
)
from worldshepherd_sara.qualification import CapabilityStatus


def signal_event(event_id: str, *, source="ECHO", trigger="ANOMALY") -> AuditRecord:
    return AuditRecord(
        timestamp="2026-09-12T20:00:00+00:00",
        event="operational_signal",
        actor="SARA",
        payload={
            "_outbox_event_id": event_id,
            "_delivery_semantics": "AT_LEAST_ONCE",
            "_ws_improvement_signal": {
                "source": source,
                "trigger_kind": trigger,
                "statement": "Observed delta exceeded the qualified envelope.",
                "affected_lanes": ["PRIME"],
                "risk_level": "HIGH",
                "required_tests": ["regression-gate"],
                "success_metrics": ["qualified envelope restored"],
                "negative_evidence": [{"metric": "delta", "result": "outside-envelope"}],
            },
        },
    )


def ordinary_event(event_id: str) -> AuditRecord:
    return AuditRecord(
        timestamp="2026-09-12T20:00:00+00:00",
        event="ordinary_audit",
        actor="SARA",
        payload={
            "_outbox_event_id": event_id,
            "_delivery_semantics": "AT_LEAST_ONCE",
        },
    )


def echo_store(tmp_path):
    root = tmp_path / "echo"
    root.mkdir(mode=0o700)
    return EchoEventStore(root.resolve())


def test_explicit_event_translation_does_not_inflate_maturity():
    item = audit_event_to_improvement(
        signal_event("SARA-EVENT-wsri-operational-1"),
        created_utc="2026-09-12T20:01:00Z",
    )
    assert item.trigger_kind == ImprovementTriggerKind.ANOMALY
    assert item.risk_level == ImprovementRisk.HIGH
    assert item.baseline_capability_status == [CapabilityStatus.NOT_CURRENTLY_CLAIMED]
    assert item.target_capability_status is None
    assert not item.requested_claim_promotion
    assert not item.requested_external_execution


def test_missing_signal_is_rejected():
    with pytest.raises(OperationalImprovementSignalError):
        audit_event_to_improvement(
            ordinary_event("SARA-EVENT-wsri-ordinary"),
            created_utc="2026-09-12T20:01:00Z",
        )


def test_event_id_is_stable_across_reprocessing():
    record = signal_event("SARA-EVENT-wsri-stable")
    first = audit_event_to_improvement(record, created_utc="2026-09-12T20:01:00Z")
    second = audit_event_to_improvement(record, created_utc="2026-09-13T20:01:00Z")
    assert first.improvement_id == second.improvement_id


def test_stored_echo_event_round_trip(tmp_path):
    store = echo_store(tmp_path)
    result = store.ingest(signal_event("SARA-EVENT-wsri-roundtrip"))
    item = stored_echo_event_to_improvement(
        result.record,
        created_utc=result.record.first_ingested_at,
    )
    assert result.record.event_id in item.source_refs
    assert any(ref.startswith("ECHO-SEMANTIC-SHA256:") for ref in item.source_refs)


def test_feedback_policy_fails_closed():
    with pytest.raises(ValidationError):
        ImprovementFeedbackPolicy(allow_claim_promotion=True)
    with pytest.raises(ValidationError):
        ImprovementFeedbackPolicy(allow_deployment=True)
    with pytest.raises(ValidationError):
        ImprovementFeedbackPolicy(allow_external_execution=True)


def test_feedback_cycle_ignores_ordinary_and_stores_signal(tmp_path):
    store = echo_store(tmp_path)
    store.ingest(ordinary_event("SARA-EVENT-wsri-feedback-ordinary"))
    store.ingest(signal_event("SARA-EVENT-wsri-feedback-signal"))
    ledger = ImprovementLedger((tmp_path / "ledger").resolve())
    cursor, report = run_operational_feedback_cycle(
        store,
        ledger,
        ImprovementFeedbackCursor(),
    )
    assert report.scanned_events == 2
    assert report.ordinary_events_ignored == 1
    assert report.proposals_stored == 1
    assert not report.claim_promotion_performed
    assert not report.deployment_performed
    assert not report.external_execution_performed
    assert cursor.last_event_id == "SARA-EVENT-wsri-feedback-signal"
    assert ledger.verify_chain()


def test_feedback_reprocessing_deduplicates(tmp_path):
    store = echo_store(tmp_path)
    store.ingest(signal_event("SARA-EVENT-wsri-feedback-dedupe"))
    ledger = ImprovementLedger((tmp_path / "ledger").resolve())
    _, first = run_operational_feedback_cycle(store, ledger, ImprovementFeedbackCursor())
    _, second = run_operational_feedback_cycle(store, ledger, ImprovementFeedbackCursor())
    assert first.proposals_stored == 1
    assert second.proposals_deduplicated == 1
    assert len(ledger.records()) == 1


def test_feedback_budget_defers_without_skipping(tmp_path):
    store = echo_store(tmp_path)
    store.ingest(signal_event("SARA-EVENT-wsri-feedback-s1"))
    store.ingest(signal_event("SARA-EVENT-wsri-feedback-s2"))
    ledger = ImprovementLedger((tmp_path / "ledger").resolve())
    policy = ImprovementFeedbackPolicy(max_new_proposals_per_cycle=1)
    cursor, first = run_operational_feedback_cycle(
        store, ledger, ImprovementFeedbackCursor(), policy=policy
    )
    assert first.deferred_signal_event_ids == ["SARA-EVENT-wsri-feedback-s2"]
    assert cursor.last_event_id == "SARA-EVENT-wsri-feedback-s1"
    cursor, second = run_operational_feedback_cycle(store, ledger, cursor, policy=policy)
    assert second.proposals_stored == 1
    assert cursor.last_event_id == "SARA-EVENT-wsri-feedback-s2"


def test_invalid_explicit_signal_is_reported(tmp_path):
    store = echo_store(tmp_path)
    bad = signal_event("SARA-EVENT-wsri-feedback-bad")
    bad.payload["_ws_improvement_signal"]["trigger_kind"] = "OPPORTUNITY"
    store.ingest(bad)
    ledger = ImprovementLedger((tmp_path / "ledger").resolve())
    cursor, report = run_operational_feedback_cycle(
        store, ledger, ImprovementFeedbackCursor()
    )
    assert report.invalid_signal_event_ids == ["SARA-EVENT-wsri-feedback-bad"]
    assert cursor.last_event_id == "SARA-EVENT-wsri-feedback-bad"
    assert len(ledger.records()) == 0
