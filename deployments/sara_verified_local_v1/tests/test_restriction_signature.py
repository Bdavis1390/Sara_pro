from __future__ import annotations

import base64
import copy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)
from worldshepherd_sara.restriction_provenance import capture_restriction
from worldshepherd_sara.restriction_signature import (
    RESTRICTION_SIGNATURE_DOMAIN,
    RESTRICTION_SIGNATURE_SCHEMA,
    canonical_restriction_signature_message,
    verify_restriction_signature,
)


KEY = b"worldshepherd-g6-hmac-test-key-32-bytes-minimum"
KEY_ID = "ws-restriction-key-epoch-2026-09"
SIGNING_KEY_ID = "PS-RESTRICTION-K1"
APPROVED_SUMMARY = "Output was restricted; only bounded provenance is retained."


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _signing_material():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            SIGNING_KEY_ID: _b64url(private.public_key().public_bytes_raw())
        }
    )
    return private, verifier


def evidence():
    return capture_restriction(
        fingerprint_key=KEY,
        fingerprint_key_id=KEY_ID,
        action="BLOCK",
        reason_code="POLICY.SIGNATURE_TEST",
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        process_version="v3",
        policy_ref="CONTENT_POLICY",
        correlation_id="signature-001",
        raw_input="signature test raw input must not persist",
        raw_generated="signature test raw output must not persist",
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        occurred_at="2026-09-17T23:00:00+00:00",
    )


def test_external_prime_signature_verifies_with_public_key_only():
    private, verifier = _signing_material()
    item = evidence()
    message = canonical_restriction_signature_message(
        item,
        signing_key_id=SIGNING_KEY_ID,
    )
    signature = _b64url(private.sign(message))

    verified = verify_restriction_signature(
        item,
        signing_key_id=SIGNING_KEY_ID,
        signature_b64url=signature,
        verifier=verifier,
    )

    assert message.startswith(RESTRICTION_SIGNATURE_DOMAIN)
    assert verified.schema == RESTRICTION_SIGNATURE_SCHEMA
    assert verified.restriction_id == item.restriction_id
    assert verified.signing_key_id == SIGNING_KEY_ID
    assert len(verified.signing_key_fingerprint_sha256) == 64
    assert len(verified.signed_message_sha256) == 64
    assert verified.signature_b64url == signature


def test_signature_binds_entire_safe_restriction_document():
    private, verifier = _signing_material()
    item = evidence()
    signature = _b64url(
        private.sign(
            canonical_restriction_signature_message(
                item,
                signing_key_id=SIGNING_KEY_ID,
            )
        )
    )

    tampered = copy.deepcopy(item)
    object.__setattr__(tampered, "reason_code", "POLICY.TAMPERED")

    with pytest.raises(PrimeSentinelAuthorizationError, match="signature"):
        verify_restriction_signature(
            tampered,
            signing_key_id=SIGNING_KEY_ID,
            signature_b64url=signature,
            verifier=verifier,
        )


def test_signature_binds_expected_signing_key_id():
    private, verifier = _signing_material()
    item = evidence()
    signature = _b64url(
        private.sign(
            canonical_restriction_signature_message(
                item,
                signing_key_id=SIGNING_KEY_ID,
            )
        )
    )

    with pytest.raises(PrimeSentinelAuthorizationError, match="unknown"):
        verify_restriction_signature(
            item,
            signing_key_id="PS-OTHER",
            signature_b64url=signature,
            verifier=verifier,
        )


def test_revoked_prime_signing_key_fails_closed():
    private, _verifier = _signing_material()
    item = evidence()
    public = _b64url(private.public_key().public_bytes_raw())
    revoked = PrimeSentinelVerifier(
        public_keys_b64url={SIGNING_KEY_ID: public},
        revoked_key_ids={SIGNING_KEY_ID},
    )
    signature = _b64url(
        private.sign(
            canonical_restriction_signature_message(
                item,
                signing_key_id=SIGNING_KEY_ID,
            )
        )
    )

    with pytest.raises(PrimeSentinelAuthorizationError, match="revoked"):
        verify_restriction_signature(
            item,
            signing_key_id=SIGNING_KEY_ID,
            signature_b64url=signature,
            verifier=revoked,
        )


def test_signature_protocol_never_contains_hmac_or_prime_private_key_material():
    private, verifier = _signing_material()
    item = evidence()
    message = canonical_restriction_signature_message(
        item,
        signing_key_id=SIGNING_KEY_ID,
    )
    signature = _b64url(private.sign(message))
    verified = verify_restriction_signature(
        item,
        signing_key_id=SIGNING_KEY_ID,
        signature_b64url=signature,
        verifier=verifier,
    )

    serialized = str(verified.semantic_document())
    assert KEY.decode("utf-8") not in serialized
    assert KEY.decode("utf-8") not in message.decode("utf-8")
    # The verifier exposes only the public-key fingerprint, never private material.
    assert set(verified.semantic_document()) == {
        "schema",
        "restriction_id",
        "signing_key_id",
        "signing_key_fingerprint_sha256",
        "signature_b64url",
        "signed_message_sha256",
    }
