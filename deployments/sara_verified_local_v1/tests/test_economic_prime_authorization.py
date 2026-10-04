from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.economic_authorization import (
    EconomicAuthorizationPolicy,
    EconomicPaymentIntent,
    economic_intent_sha256,
    economic_policy_sha256,
)
from worldshepherd_sara.economic_ledger import (
    EconomicAuthorizationLedger,
    EconomicReplayDetected,
)
from worldshepherd_sara.economic_prime_authorization import (
    EconomicPrimeAuthorizationAssertion,
    EconomicPrimeAuthorizationError,
    canonical_economic_prime_authorization_message,
    verify_economic_prime_authorization,
)
from worldshepherd_sara.prime_sentinel_authorization import PrimeSentinelVerifier


NOW = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keys():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            "PS-ECO-K1": _b64url(private.public_key().public_bytes_raw())
        }
    )
    return private, verifier


def _policy(**overrides) -> EconomicAuthorizationPolicy:
    values = {
        "policy_id": "POLICY-G2",
        "session_id": "SESSION-G2",
        "allowed_protocols": frozenset({"X402", "MPP"}),
        "allowed_networks": frozenset({"sandbox"}),
        "allowed_assets": frozenset({"TEST-USDC"}),
        "allowed_payees": frozenset({"merchant:test"}),
        "max_per_transaction": Decimal("5.00"),
        "max_session_total": Decimal("10.00"),
        "require_human_approval": True,
        "expires_at": NOW + timedelta(minutes=15),
    }
    values.update(overrides)
    return EconomicAuthorizationPolicy(**values)


def _intent(
    *,
    intent_id: str = "INTENT-G2-001",
    nonce: str = "intent-nonce-g2-0123456789",
    **overrides,
) -> EconomicPaymentIntent:
    values = {
        "intent_id": intent_id,
        "actor_id": "SARA-G2-TEST",
        "session_id": "SESSION-G2",
        "protocol": "X402",
        "network": "sandbox",
        "asset": "TEST-USDC",
        "payee": "merchant:test",
        "amount": Decimal("1.25"),
        "purpose": "Synthetic paid API response",
        "mode": "DRY_RUN",
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "nonce": nonce,
        "human_approval_id": "HUMAN-APPROVAL-G2",
    }
    values.update(overrides)
    return EconomicPaymentIntent(**values)


def _signed_assertion(
    private: Ed25519PrivateKey,
    intent: EconomicPaymentIntent,
    policy: EconomicAuthorizationPolicy,
    *,
    authorization_id: str = "PS-ECO-AUTH-001",
    authorization_nonce: str = "auth-nonce-g2-0123456789",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    **overrides,
) -> EconomicPrimeAuthorizationAssertion:
    values = {
        "key_id": "PS-ECO-K1",
        "authorization_id": authorization_id,
        "authorization_nonce": authorization_nonce,
        "intent_id": intent.intent_id,
        "intent_sha256": economic_intent_sha256(intent),
        "policy_id": policy.policy_id,
        "policy_sha256": economic_policy_sha256(policy),
        "session_id": intent.session_id,
        "protocol": intent.protocol,
        "network": intent.network,
        "asset": intent.asset,
        "payee": intent.payee,
        "authorized_amount": intent.amount,
        "human_approval_id": intent.human_approval_id,
        "issued_at": issued_at or NOW,
        "expires_at": expires_at or NOW + timedelta(minutes=5),
        "signature_b64url": _b64url(b"0" * 64),
    }
    values.update(overrides)
    assertion = EconomicPrimeAuthorizationAssertion(**values)
    signature = private.sign(canonical_economic_prime_authorization_message(assertion))
    return assertion.model_copy(update={"signature_b64url": _b64url(signature)})


def test_valid_prime_economic_authorization_verifies_exact_binding():
    private, verifier = _keys()
    p = _policy()
    i = _intent()
    assertion = _signed_assertion(private, i, p)

    verified = verify_economic_prime_authorization(
        assertion,
        verifier=verifier,
        intent=i,
        policy=p,
        now=NOW,
    )

    assert verified.authorization_id == "PS-ECO-AUTH-001"
    assert verified.intent_sha256 == economic_intent_sha256(i)
    assert verified.policy_sha256 == economic_policy_sha256(p)
    assert verified.authorized_amount == i.amount
    assert len(verified.authorization_record_sha256) == 64
    assert len(verified.key_fingerprint_sha256) == 64


def test_validly_signed_amount_escalation_is_rejected_by_binding():
    private, verifier = _keys()
    p = _policy()
    i = _intent()
    assertion = _signed_assertion(
        private,
        i,
        p,
        authorized_amount=Decimal("2.50"),
    )

    with pytest.raises(EconomicPrimeAuthorizationError, match="authorized_amount"):
        verify_economic_prime_authorization(
            assertion,
            verifier=verifier,
            intent=i,
            policy=p,
            now=NOW,
        )


def test_policy_rebinding_is_rejected_even_with_same_policy_id():
    private, verifier = _keys()
    original = _policy()
    changed = _policy(max_session_total=Decimal("11.00"))
    i = _intent()
    assertion = _signed_assertion(private, i, original)

    with pytest.raises(EconomicPrimeAuthorizationError, match="policy_sha256"):
        verify_economic_prime_authorization(
            assertion,
            verifier=verifier,
            intent=i,
            policy=changed,
            now=NOW,
        )


def test_signature_tampering_fails_closed():
    private, verifier = _keys()
    p = _policy()
    i = _intent()
    assertion = _signed_assertion(private, i, p)
    bad = bytearray(base64.urlsafe_b64decode(assertion.signature_b64url + "=="))
    bad[0] ^= 1
    tampered = assertion.model_copy(update={"signature_b64url": _b64url(bytes(bad))})

    with pytest.raises(EconomicPrimeAuthorizationError, match="signature"):
        verify_economic_prime_authorization(
            tampered,
            verifier=verifier,
            intent=i,
            policy=p,
            now=NOW,
        )


def test_expired_and_future_economic_authorizations_fail_closed():
    private, verifier = _keys()
    p = _policy()
    i = _intent()

    expired = _signed_assertion(
        private,
        i,
        p,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW - timedelta(minutes=1),
    )
    with pytest.raises(EconomicPrimeAuthorizationError, match="expired"):
        verify_economic_prime_authorization(
            expired,
            verifier=verifier,
            intent=i,
            policy=p,
            now=NOW,
        )

    future = _signed_assertion(
        private,
        i,
        p,
        issued_at=NOW + timedelta(minutes=2),
        expires_at=NOW + timedelta(minutes=7),
    )
    with pytest.raises(EconomicPrimeAuthorizationError, match="future"):
        verify_economic_prime_authorization(
            future,
            verifier=verifier,
            intent=i,
            policy=p,
            now=NOW,
        )


def test_verified_prime_authorization_is_bound_into_durable_ledger(tmp_path):
    private, verifier = _keys()
    p = _policy()
    i = _intent()
    ledger = EconomicAuthorizationLedger((tmp_path / "economic-g2").resolve())
    ledger.record_intent(i, p, now=NOW)
    decision = ledger.evaluate_recorded_intent(i, p, now=NOW)
    assert decision.disposition == "ALLOW_DRY_RUN"

    assertion = _signed_assertion(private, i, p)
    verified = verify_economic_prime_authorization(
        assertion,
        verifier=verifier,
        intent=i,
        policy=p,
        now=NOW,
    )
    record = ledger.record_authorization_result(
        intent_id=i.intent_id,
        status="PRIME_VERIFIED",
        authorization_ref=verified.authorization_id,
        authorization_digest_sha256=verified.authorization_record_sha256,
        authorization_nonce=verified.authorization_nonce,
        now=NOW,
    )

    assert record.authorization_status == "PRIME_VERIFIED"
    assert record.authorization_ref == verified.authorization_id
    assert record.authorization_digest_sha256 == verified.authorization_record_sha256
    assert record.authorization_nonce == verified.authorization_nonce


def test_prime_authorization_reference_nonce_and_digest_are_one_time(tmp_path):
    private, verifier = _keys()
    p = _policy()
    first = _intent()
    second = _intent(
        intent_id="INTENT-G2-002",
        nonce="intent-nonce-g2-2222222222",
        amount=Decimal("1.00"),
    )
    ledger = EconomicAuthorizationLedger((tmp_path / "economic-g2").resolve())
    ledger.record_intent(first, p, now=NOW)
    ledger.record_intent(second, p, now=NOW)
    ledger.evaluate_recorded_intent(first, p, now=NOW)
    ledger.evaluate_recorded_intent(second, p, now=NOW)

    assertion = _signed_assertion(private, first, p)
    verified = verify_economic_prime_authorization(
        assertion,
        verifier=verifier,
        intent=first,
        policy=p,
        now=NOW,
    )
    ledger.record_authorization_result(
        intent_id=first.intent_id,
        status="PRIME_VERIFIED",
        authorization_ref=verified.authorization_id,
        authorization_digest_sha256=verified.authorization_record_sha256,
        authorization_nonce=verified.authorization_nonce,
        now=NOW,
    )

    with pytest.raises(EconomicReplayDetected):
        ledger.record_authorization_result(
            intent_id=second.intent_id,
            status="PRIME_VERIFIED",
            authorization_ref=verified.authorization_id,
            authorization_digest_sha256=verified.authorization_record_sha256,
            authorization_nonce=verified.authorization_nonce,
            now=NOW,
        )
