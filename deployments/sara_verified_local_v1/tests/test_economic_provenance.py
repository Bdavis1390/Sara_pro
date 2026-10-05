from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from worldshepherd_sara.economic_authorization import (
    EconomicAuthorizationPolicy,
    EconomicPaymentIntent,
)
from worldshepherd_sara.economic_ledger import EconomicAuthorizationLedger
from worldshepherd_sara.economic_provenance import (
    ECONOMIC_PROVENANCE_SCHEMA,
    EconomicProvenanceError,
    build_economic_provenance_event,
    queue_economic_provenance_patch,
)
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.event_outbox import drain_event_outbox
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


NOW = datetime(2026, 10, 4, 21, 0, tzinfo=timezone.utc)


def _policy() -> EconomicAuthorizationPolicy:
    return EconomicAuthorizationPolicy(
        policy_id="POLICY-G3",
        session_id="SESSION-G3",
        allowed_protocols=frozenset({"X402"}),
        allowed_networks=frozenset({"sandbox"}),
        allowed_assets=frozenset({"TEST-USDC"}),
        allowed_payees=frozenset({"merchant:test"}),
        max_per_transaction=Decimal("5.00"),
        max_session_total=Decimal("10.00"),
        require_human_approval=True,
        expires_at=NOW + timedelta(minutes=15),
    )


def _intent(
    *,
    intent_id: str = "INTENT-G3-001",
    nonce: str = "intent-nonce-g3-0123456789",
    amount: str = "1.25",
) -> EconomicPaymentIntent:
    return EconomicPaymentIntent(
        intent_id=intent_id,
        actor_id="SARA-G3-TEST",
        session_id="SESSION-G3",
        protocol="X402",
        network="sandbox",
        asset="TEST-USDC",
        payee="merchant:test",
        amount=Decimal(amount),
        purpose="Synthetic paid API response",
        mode="DRY_RUN",
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        nonce=nonce,
        human_approval_id="HUMAN-APPROVAL-G3",
    )


def _allowed_record(tmp_path):
    p = _policy()
    i = _intent()
    ledger = EconomicAuthorizationLedger((tmp_path / "economic").resolve())
    ledger.record_intent(i, p, now=NOW)
    decision = ledger.evaluate_recorded_intent(i, p, now=NOW)
    assert decision.disposition == "ALLOW_DRY_RUN"
    record = ledger.get(i.intent_id)
    assert record is not None
    return ledger, p, i, record


def test_intent_provenance_is_stable_and_hashes_nonce(tmp_path):
    _ledger, _p, i, record = _allowed_record(tmp_path)
    first = build_economic_provenance_event(record, phase="INTENT_RECORDED")
    second = build_economic_provenance_event(record, phase="INTENT_RECORDED")

    assert first == second
    assert first["event_id"].startswith("SARA-EVENT-ECON-INTENT_RECORDED-")
    assert first["payload"]["schema"] == ECONOMIC_PROVENANCE_SCHEMA
    assert first["payload"]["intent_sha256"] == record.intent_sha256
    assert "nonce" not in first["payload"]
    assert first["payload"]["nonce_sha256"] != i.nonce
    assert first["payload"]["raw_provider_content_included"] is False


def test_decision_provenance_preserves_negative_evidence(tmp_path):
    p = _policy()
    i = _intent(amount="6.00")
    ledger = EconomicAuthorizationLedger((tmp_path / "economic").resolve())
    ledger.record_intent(i, p, now=NOW)
    decision = ledger.evaluate_recorded_intent(i, p, now=NOW)
    assert decision.disposition == "DENY"
    record = ledger.get(i.intent_id)
    assert record is not None

    event = build_economic_provenance_event(record, phase="DECISION_RECORDED")

    assert event["payload"]["decision_status"] == "DENIED"
    assert "per_transaction_limit_exceeded" in event["payload"]["reasons"]
    assert event["payload"]["disposition"] == "DENY"


def test_authorization_provenance_records_rejection_without_private_material(tmp_path):
    ledger, _p, i, _record = _allowed_record(tmp_path)
    rejected = ledger.record_authorization_result(
        intent_id=i.intent_id,
        status="REJECTED",
        authorization_ref="PS-ECO-REJECT-001",
        now=NOW,
    )

    event = build_economic_provenance_event(
        rejected,
        phase="AUTHORIZATION_RECORDED",
    )

    assert event["actor"] == "PRIME_SENTINEL"
    assert event["payload"]["authorization_status"] == "REJECTED"
    assert event["payload"]["private_signing_material_included"] is False
    serialized = json.dumps(event, sort_keys=True)
    assert "BEGIN PRIVATE KEY" not in serialized


def test_unreached_phases_fail_closed(tmp_path):
    _ledger, _p, _i, record = _allowed_record(tmp_path)

    with pytest.raises(EconomicProvenanceError, match="authorization"):
        build_economic_provenance_event(record, phase="AUTHORIZATION_RECORDED")
    with pytest.raises(EconomicProvenanceError, match="consumed"):
        build_economic_provenance_event(record, phase="DRY_RUN_CONSUMED")
    with pytest.raises(EconomicProvenanceError, match="failure"):
        build_economic_provenance_event(record, phase="FAILED")


def test_dry_run_consumption_never_claims_external_settlement(tmp_path):
    ledger, _p, i, _record = _allowed_record(tmp_path)
    consumed = ledger.consume_dry_run(
        intent_id=i.intent_id,
        adapter_receipt_ref="DRYRUN-G3-RECEIPT",
        now=NOW,
    )

    event = build_economic_provenance_event(consumed, phase="DRY_RUN_CONSUMED")

    assert event["payload"]["consumption_status"] == "DRY_RUN_CONSUMED"
    assert event["payload"]["external_settlement_claimed"] is False


def test_failure_event_is_retained_as_first_class_provenance(tmp_path):
    ledger, _p, i, _record = _allowed_record(tmp_path)
    failed = ledger.mark_failed(
        intent_id=i.intent_id,
        failure_code="SANDBOX_PROVIDER_UNREACHABLE",
        now=NOW,
    )

    event = build_economic_provenance_event(failed, phase="FAILED")

    assert event["payload"]["failure_code"] == "SANDBOX_PROVIDER_UNREACHABLE"
    assert event["payload"]["failed_at"] is not None


def test_sara_outbox_to_echo_round_trip_and_deduplication(tmp_path):
    _ledger, _p, _i, record = _allowed_record(tmp_path)
    sara = DurableStore(tmp_path / "sara")

    def operation(registry):
        patch, event_id = queue_economic_provenance_patch(
            registry,
            record,
            phase="DECISION_RECORDED",
        )
        return patch, event_id

    event_id = sara.transact_registry(operation)
    assert event_id.startswith("SARA-EVENT-ECON-DECISION_RECORDED-")
    assert drain_event_outbox(sara, limit=1) == 1

    audits = [
        AuditRecord(**item)
        for item in sara.read_audit(50)
        if item.get("event") == "economic_provenance"
    ]
    assert len(audits) == 1
    assert audits[0].payload["_outbox_event_id"] == event_id
    assert audits[0].payload["_delivery_semantics"] == "AT_LEAST_ONCE"

    echo = EchoEventStore((tmp_path / "echo").resolve())
    first = echo.ingest(audits[0])
    replay = echo.ingest(audits[0])

    assert first.outcome == "STORED"
    assert replay.outcome == "DEDUPLICATED"
    assert replay.record.event_id == event_id
    assert replay.record.delivery_count == 2
    assert echo.reconcile(audits)["counts"] == {"MATCHED": 1}
    assert echo.health()["ok"] is True


def test_same_intent_different_phases_get_distinct_stable_ids(tmp_path):
    ledger, _p, i, record = _allowed_record(tmp_path)
    consumed = ledger.consume_dry_run(intent_id=i.intent_id, now=NOW)

    decision_event = build_economic_provenance_event(
        record,
        phase="DECISION_RECORDED",
    )
    consumed_event = build_economic_provenance_event(
        consumed,
        phase="DRY_RUN_CONSUMED",
    )

    assert decision_event["event_id"] != consumed_event["event_id"]
