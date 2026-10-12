from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.prime_action_authorization import (
    PrimeActionAuthorizationAssertion,
    PrimeActionAuthorizationError,
    PrimeActionAuthorizationVerifier,
    assert_recorded_action_authorization_usable,
    canonical_action_authorization_message,
    consumed_action_authorization_registry_patch,
    verified_action_authorization_registry_patch,
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keys():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeActionAuthorizationVerifier(
        public_keys_b64url={"PS-ACT-K1": _b64url(private.public_key().public_bytes_raw())}
    )
    return private, verifier


def _signed(private, *, now, request_sha256=None, human=False):
    request_sha256 = request_sha256 or "sha256:" + "1" * 64
    assertion = PrimeActionAuthorizationAssertion(
        key_id="PS-ACT-K1",
        authorization_id="ACT-AUTH-001",
        action_id="ACTION-001",
        prime_id="PRIME-001",
        provider="OPENAI",
        provider_operation="RESPONSES_CREATE",
        model_allowlist=["gpt-test"],
        tool_allowlist=["read_system_status"],
        resource_scope=["system:status"],
        requested_authority=10,
        reversible=True,
        side_effect_class="READ_ONLY",
        policy_id="POLICY-001",
        policy_sha256="sha256:" + "2" * 64,
        policy_disposition=("HUMAN_REVIEW_REQUIRED" if human else "AUTO_ELIGIBLE"),
        request_sha256=request_sha256,
        human_approval_required=human,
        human_decision_id=("HUMAN-001" if human else None),
        human_decision_sha256=("sha256:" + "3" * 64 if human else None),
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce="nonce-action-0123456789",
        signature_b64url=_b64url(b"0" * 64),
    )
    sig = private.sign(canonical_action_authorization_message(assertion))
    return assertion.model_copy(update={"signature_b64url": _b64url(sig)})


def test_valid_action_authorization_verifies_and_is_one_time_consumable():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    verified = verifier.verify(_signed(private, now=now), now=now)
    assert verified.provider == "OPENAI"
    registry = verified_action_authorization_registry_patch({}, verified)
    entry = assert_recorded_action_authorization_usable(
        registry,
        authorization_id=verified.authorization_id,
        action_id=verified.action_id,
        request_sha256=verified.request_sha256,
        verifier=verifier,
        now=now,
    )
    assert entry["status"] == "VERIFIED"
    consumed = consumed_action_authorization_registry_patch(
        registry,
        authorization_id=verified.authorization_id,
        execution_id="AI-EXEC-001",
        consumed_at=now,
    )
    assert consumed["PRIME_ACTION_AUTHORIZATIONS"][verified.authorization_id]["status"] == "CONSUMED"
    with pytest.raises(PrimeActionAuthorizationError, match="cannot be consumed"):
        consumed_action_authorization_registry_patch(
            consumed,
            authorization_id=verified.authorization_id,
            execution_id="AI-EXEC-002",
            consumed_at=now,
        )


def test_tampered_request_digest_fails_signature_verification():
    private, verifier = _keys()
    now = datetime.now(timezone.utc)
    assertion = _signed(private, now=now)
    tampered = assertion.model_copy(update={"request_sha256": "sha256:" + "f" * 64})
    with pytest.raises(PrimeActionAuthorizationError, match="signature"):
        verifier.verify(tampered, now=now)


def test_human_review_disposition_cannot_be_issued_without_human_evidence():
    private, _ = _keys()
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="must agree"):
        PrimeActionAuthorizationAssertion(
            key_id="PS-ACT-K1",
            authorization_id="ACT-AUTH-002",
            action_id="ACTION-002",
            prime_id="PRIME-001",
            provider="OPENAI",
            provider_operation="RESPONSES_CREATE",
            model_allowlist=["gpt-test"],
            tool_allowlist=[],
            resource_scope=[],
            requested_authority=0,
            reversible=True,
            side_effect_class="READ_ONLY",
            policy_id="POLICY-001",
            policy_sha256="sha256:" + "2" * 64,
            policy_disposition="HUMAN_REVIEW_REQUIRED",
            request_sha256="sha256:" + "1" * 64,
            human_approval_required=False,
            issued_at=now,
            expires_at=now + timedelta(minutes=5),
            nonce="nonce-action-abcdefghijkl",
            signature_b64url=_b64url(b"0" * 64),
        )


def test_consequential_execution_requires_human_review():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="requires human review"):
        PrimeActionAuthorizationAssertion(
            key_id="PS-ACT-K1",
            authorization_id="ACT-AUTH-003",
            action_id="ACTION-003",
            prime_id="PRIME-001",
            provider="OPENAI",
            provider_operation="RESPONSES_CREATE",
            model_allowlist=["gpt-test"],
            requested_authority=10,
            reversible=True,
            side_effect_class="CONSEQUENTIAL",
            policy_id="POLICY-001",
            policy_sha256="sha256:" + "2" * 64,
            policy_disposition="AUTO_ELIGIBLE",
            request_sha256="sha256:" + "1" * 64,
            human_approval_required=False,
            issued_at=now,
            expires_at=now + timedelta(minutes=5),
            nonce="nonce-action-consequential",
            signature_b64url=_b64url(b"0" * 64),
        )


def test_empty_model_identifier_is_rejected():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        PrimeActionAuthorizationAssertion(
            key_id="PS-ACT-K1",
            authorization_id="ACT-AUTH-004",
            action_id="ACTION-004",
            prime_id="PRIME-001",
            provider="OPENAI",
            provider_operation="RESPONSES_CREATE",
            model_allowlist=[""],
            requested_authority=0,
            reversible=True,
            side_effect_class="READ_ONLY",
            policy_id="POLICY-001",
            policy_sha256="sha256:" + "2" * 64,
            policy_disposition="AUTO_ELIGIBLE",
            request_sha256="sha256:" + "1" * 64,
            issued_at=now,
            expires_at=now + timedelta(minutes=5),
            nonce="nonce-action-empty-model",
            signature_b64url=_b64url(b"0" * 64),
        )
