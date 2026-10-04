from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from worldshepherd_sara.economic_authorization import (
    EconomicAuthorizationPolicy,
    EconomicPaymentIntent,
    economic_policy_sha256,
)
from worldshepherd_sara.economic_ledger import (
    EconomicAuthorizationLedger,
    EconomicInvalidTransition,
    EconomicLedgerConflict,
    EconomicLedgerError,
    EconomicReplayDetected,
)


NOW = datetime(2026, 10, 4, 19, 0, tzinfo=timezone.utc)


def policy(**overrides) -> EconomicAuthorizationPolicy:
    values = {
        "policy_id": "POLICY-G1",
        "session_id": "SESSION-G1",
        "allowed_protocols": frozenset({"X402", "MPP"}),
        "allowed_networks": frozenset({"sandbox"}),
        "allowed_assets": frozenset({"TEST-USDC"}),
        "allowed_payees": frozenset({"merchant:test"}),
        "max_per_transaction": Decimal("10.00"),
        "max_session_total": Decimal("10.00"),
        "require_human_approval": True,
        "expires_at": NOW + timedelta(minutes=30),
    }
    values.update(overrides)
    return EconomicAuthorizationPolicy(**values)


def intent(
    *,
    intent_id: str = "INTENT-G1-001",
    nonce: str = "nonce-g1-0123456789abcdef",
    amount: str = "1.25",
    mode: str = "DRY_RUN",
    **overrides,
) -> EconomicPaymentIntent:
    values = {
        "intent_id": intent_id,
        "actor_id": "SARA-G1-TEST",
        "session_id": "SESSION-G1",
        "protocol": "X402",
        "network": "sandbox",
        "asset": "TEST-USDC",
        "payee": "merchant:test",
        "amount": Decimal(amount),
        "purpose": "Synthetic paid API response",
        "mode": mode,
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "nonce": nonce,
        "human_approval_id": "APPROVAL-G1",
    }
    values.update(overrides)
    return EconomicPaymentIntent(**values)


def make_ledger(tmp_path: Path) -> EconomicAuthorizationLedger:
    return EconomicAuthorizationLedger((tmp_path / "economic-ledger").resolve())


def test_intent_record_is_durable_and_idempotent_before_consumption(tmp_path):
    ledger = make_ledger(tmp_path)
    original = ledger.record_intent(intent(), policy(), now=NOW)
    assert original.decision_status == "PENDING"

    restarted = EconomicAuthorizationLedger(ledger.data_dir)
    retry = restarted.record_intent(intent(), policy(), now=NOW)
    assert retry.intent_id == original.intent_id
    assert retry.intent_sha256 == original.intent_sha256
    assert retry.nonce == original.nonce
    assert restarted.health()["records"] == 1
    assert restarted.health()["events"] == 1


def test_intent_id_cannot_be_rebound_to_different_content(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.record_intent(intent(), policy(), now=NOW)

    with pytest.raises(EconomicLedgerConflict):
        ledger.record_intent(intent(amount="1.26"), policy(), now=NOW)


def test_nonce_reuse_across_intent_ids_fails_closed(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.record_intent(intent(), policy(), now=NOW)

    with pytest.raises(EconomicReplayDetected):
        ledger.record_intent(
            intent(intent_id="INTENT-G1-002"),
            policy(),
            now=NOW,
        )


def test_policy_id_cannot_be_rebound_to_changed_policy_content(tmp_path):
    ledger = make_ledger(tmp_path)
    first_policy = policy()
    ledger.record_intent(intent(), first_policy, now=NOW)

    changed_policy = policy(max_session_total=Decimal("20.00"))
    with pytest.raises(EconomicLedgerConflict):
        ledger.record_intent(intent(), changed_policy, now=NOW)


def test_atomic_decision_path_reserves_session_budget(tmp_path):
    ledger = make_ledger(tmp_path)
    p = policy()

    first = intent(intent_id="INTENT-G1-101", nonce="nonce-g1-101-1234567890", amount="6.00")
    second = intent(intent_id="INTENT-G1-102", nonce="nonce-g1-102-1234567890", amount="5.00")

    ledger.record_intent(first, p, now=NOW)
    ledger.record_intent(second, p, now=NOW)

    first_decision = ledger.evaluate_recorded_intent(first, p, now=NOW)
    second_decision = ledger.evaluate_recorded_intent(second, p, now=NOW)

    assert first_decision.disposition == "ALLOW_DRY_RUN"
    assert first_decision.spent_before == Decimal("0")
    assert second_decision.disposition == "DENY"
    assert "session_budget_exceeded" in second_decision.reasons
    assert second_decision.spent_before == Decimal("6.00")
    assert ledger.session_reserved_total(
        session_id=p.session_id,
        policy_id=p.policy_id,
        policy_sha256=economic_policy_sha256(p),
    ) == Decimal("6.00")


def test_decision_retry_returns_persisted_decision_without_double_reservation(tmp_path):
    ledger = make_ledger(tmp_path)
    p = policy()
    i = intent(amount="4.00")
    ledger.record_intent(i, p, now=NOW)

    first = ledger.evaluate_recorded_intent(i, p, now=NOW)
    second = ledger.evaluate_recorded_intent(i, p, now=NOW + timedelta(seconds=1))

    assert first == second
    assert ledger.session_reserved_total(
        session_id=p.session_id,
        policy_id=p.policy_id,
        policy_sha256=economic_policy_sha256(p),
    ) == Decimal("4.00")


def test_live_intent_is_denied_and_cannot_be_consumed(tmp_path):
    ledger = make_ledger(tmp_path)
    p = policy()
    i = intent(mode="LIVE")
    ledger.record_intent(i, p, now=NOW)
    decision = ledger.evaluate_recorded_intent(i, p, now=NOW)

    assert decision.disposition == "DENY"
    assert "live_payment_execution_not_enabled" in decision.reasons
    with pytest.raises(EconomicInvalidTransition):
        ledger.consume_dry_run(intent_id=i.intent_id, now=NOW)


def test_consumed_dry_run_intent_and_exact_retry_fail_closed(tmp_path):
    ledger = make_ledger(tmp_path)
    p = policy()
    i = intent()
    ledger.record_intent(i, p, now=NOW)
    decision = ledger.evaluate_recorded_intent(i, p, now=NOW)
    assert decision.disposition == "ALLOW_DRY_RUN"

    consumed = ledger.consume_dry_run(
        intent_id=i.intent_id,
        adapter_receipt_ref="DRYRUN-RECEIPT-001",
        now=NOW,
    )
    assert consumed.consumption_status == "DRY_RUN_CONSUMED"

    with pytest.raises(EconomicReplayDetected):
        ledger.consume_dry_run(intent_id=i.intent_id, now=NOW)

    with pytest.raises(EconomicReplayDetected):
        ledger.record_intent(i, p, now=NOW)


def test_rejected_authorization_blocks_dry_run_consumption(tmp_path):
    ledger = make_ledger(tmp_path)
    p = policy()
    i = intent()
    ledger.record_intent(i, p, now=NOW)
    ledger.evaluate_recorded_intent(i, p, now=NOW)
    rejected = ledger.record_authorization_result(
        intent_id=i.intent_id,
        status="REJECTED",
        authorization_ref="AUTH-REJECT-001",
        now=NOW,
    )
    assert rejected.authorization_status == "REJECTED"

    with pytest.raises(EconomicInvalidTransition):
        ledger.consume_dry_run(intent_id=i.intent_id, now=NOW)


def test_prime_verified_status_requires_reference(tmp_path):
    ledger = make_ledger(tmp_path)
    p = policy()
    i = intent()
    ledger.record_intent(i, p, now=NOW)

    with pytest.raises(EconomicInvalidTransition):
        ledger.record_authorization_result(
            intent_id=i.intent_id,
            status="PRIME_VERIFIED",
            authorization_ref=None,
            now=NOW,
        )


def test_event_chain_detects_payload_tampering(tmp_path):
    ledger = make_ledger(tmp_path)
    ledger.record_intent(intent(), policy(), now=NOW)

    connection = sqlite3.connect(ledger.db_path)
    try:
        connection.execute(
            "UPDATE economic_events SET payload_json=? WHERE sequence=1",
            ('{"tampered":true}',),
        )
        connection.commit()
    finally:
        connection.close()

    ok, count = ledger.verify_event_chain()
    assert ok is False
    assert count == 1
    assert ledger.health()["ok"] is False


def test_database_symlink_is_rejected(tmp_path):
    data_dir = (tmp_path / "economic-ledger").resolve()
    ledger = EconomicAuthorizationLedger(data_dir)
    real_db = (tmp_path / "real-economic.db").resolve()
    ledger.db_path.rename(real_db)
    ledger.db_path.symlink_to(real_db)

    with pytest.raises(EconomicLedgerError, match="regular file"):
        EconomicAuthorizationLedger(data_dir)
