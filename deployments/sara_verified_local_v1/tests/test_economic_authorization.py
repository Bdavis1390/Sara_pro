from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from worldshepherd_sara.economic_authorization import (
    EconomicAuthorizationError,
    EconomicAuthorizationPolicy,
    EconomicPaymentIntent,
    canonical_economic_intent_message,
    canonical_economic_policy_message,
    economic_intent_sha256,
    economic_policy_sha256,
    evaluate_economic_intent,
)


def _now() -> datetime:
    return datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc)


def _policy(**overrides) -> EconomicAuthorizationPolicy:
    values = {
        "policy_id": "POLICY-001",
        "session_id": "SESSION-001",
        "allowed_protocols": frozenset({"X402", "AP2", "MPP"}),
        "allowed_networks": frozenset({"sandbox"}),
        "allowed_assets": frozenset({"TEST-USDC"}),
        "allowed_payees": frozenset({"merchant:test"}),
        "max_per_transaction": Decimal("5.00"),
        "max_session_total": Decimal("10.00"),
        "require_human_approval": True,
        "expires_at": _now() + timedelta(minutes=15),
    }
    values.update(overrides)
    return EconomicAuthorizationPolicy(**values)


def _intent(**overrides) -> EconomicPaymentIntent:
    values = {
        "intent_id": "INTENT-001",
        "actor_id": "SARA-TEST-AGENT",
        "session_id": "SESSION-001",
        "protocol": "X402",
        "network": "sandbox",
        "asset": "TEST-USDC",
        "payee": "merchant:test",
        "amount": Decimal("1.25"),
        "purpose": "Retrieve a synthetic paid API response",
        "mode": "DRY_RUN",
        "created_at": _now(),
        "expires_at": _now() + timedelta(minutes=5),
        "nonce": "nonce-0123456789abcdef",
        "human_approval_id": "APPROVAL-001",
    }
    values.update(overrides)
    return EconomicPaymentIntent(**values)


def test_valid_dry_run_intent_is_allowed():
    decision = evaluate_economic_intent(
        _intent(),
        _policy(),
        spent_so_far=Decimal("2.00"),
        now=_now(),
    )

    assert decision.disposition == "ALLOW_DRY_RUN"
    assert decision.reasons == ()
    assert decision.remaining_budget_after == Decimal("6.75")
    assert len(decision.intent_sha256) == 64


def test_live_execution_is_fail_closed():
    decision = evaluate_economic_intent(
        _intent(mode="LIVE"),
        _policy(),
        spent_so_far=Decimal("0"),
        now=_now(),
    )

    assert decision.disposition == "DENY"
    assert "live_payment_execution_not_enabled" in decision.reasons


def test_human_approval_is_required_by_default():
    decision = evaluate_economic_intent(
        _intent(human_approval_id=None),
        _policy(),
        spent_so_far=Decimal("0"),
        now=_now(),
    )

    assert decision.disposition == "DENY"
    assert "human_approval_required" in decision.reasons


def test_protocol_network_asset_and_payee_are_explicit_allowlists():
    intent = _intent(
        protocol="MASTERCARD_AP4M",
        network="other",
        asset="OTHER",
        payee="merchant:other",
    )
    decision = evaluate_economic_intent(
        intent,
        _policy(),
        spent_so_far=Decimal("0"),
        now=_now(),
    )

    assert decision.disposition == "DENY"
    assert set(decision.reasons) >= {
        "protocol_not_allowed",
        "network_not_allowed",
        "asset_not_allowed",
        "payee_not_allowed",
    }


def test_single_transaction_and_session_budget_are_both_enforced():
    decision = evaluate_economic_intent(
        _intent(amount=Decimal("6.00")),
        _policy(),
        spent_so_far=Decimal("5.00"),
        now=_now(),
    )

    assert decision.disposition == "DENY"
    assert "per_transaction_limit_exceeded" in decision.reasons
    assert "session_budget_exceeded" in decision.reasons
    assert decision.remaining_budget_after == Decimal("0")


def test_session_binding_and_expiry_fail_closed():
    decision = evaluate_economic_intent(
        _intent(
            session_id="SESSION-WRONG",
            created_at=_now() - timedelta(minutes=2),
            expires_at=_now() - timedelta(minutes=1),
        ),
        _policy(),
        spent_so_far=Decimal("0"),
        now=_now(),
    )

    assert decision.disposition == "DENY"
    assert "session_mismatch" in decision.reasons
    assert "intent_expired" in decision.reasons


def test_future_intent_fails_closed():
    decision = evaluate_economic_intent(
        _intent(
            created_at=_now() + timedelta(minutes=1),
            expires_at=_now() + timedelta(minutes=6),
        ),
        _policy(),
        spent_so_far=Decimal("0"),
        now=_now(),
    )

    assert decision.disposition == "DENY"
    assert "intent_created_in_future" in decision.reasons


def test_negative_spend_state_is_rejected():
    with pytest.raises(EconomicAuthorizationError, match="negative"):
        evaluate_economic_intent(
            _intent(),
            _policy(),
            spent_so_far=Decimal("-0.01"),
            now=_now(),
        )


def test_canonical_intent_hash_is_stable_and_binds_material_fields():
    first = _intent()
    same = _intent()
    changed = _intent(amount=Decimal("1.26"))

    assert canonical_economic_intent_message(first) == canonical_economic_intent_message(same)
    assert economic_intent_sha256(first) == economic_intent_sha256(same)
    assert economic_intent_sha256(first) != economic_intent_sha256(changed)


def test_canonical_policy_hash_is_order_independent_and_binds_limits():
    first = _policy(
        allowed_protocols=frozenset({"MPP", "X402", "AP2"}),
        allowed_payees=frozenset({"merchant:test"}),
    )
    same = _policy(
        allowed_protocols=frozenset({"AP2", "MPP", "X402"}),
        allowed_payees=frozenset({"merchant:test"}),
    )
    changed = _policy(max_session_total=Decimal("10.01"))

    assert canonical_economic_policy_message(first) == canonical_economic_policy_message(same)
    assert economic_policy_sha256(first) == economic_policy_sha256(same)
    assert economic_policy_sha256(first) != economic_policy_sha256(changed)


def test_policy_cannot_set_single_limit_above_session_limit():
    with pytest.raises(ValueError, match="max_per_transaction"):
        _policy(
            max_per_transaction=Decimal("11.00"),
            max_session_total=Decimal("10.00"),
        )
