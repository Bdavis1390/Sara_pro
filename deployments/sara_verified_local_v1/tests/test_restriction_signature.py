from __future__ import annotations

import base64
import copy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.event_outbox import EVENT_OUTBOX_REGISTRY_KEY
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.restriction_observability import (
    RestrictionObservabilityError,
    project_restriction_audit_record,
    restriction_observability,
)
from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)
from worldshepherd_sara.restriction_provenance import capture_restriction
from worldshepherd_sara.restriction_signature import (
    RESTRICTION_SIGNATURE_DOMAIN,
    RESTRICTION_SIGNATURE_SCHEMA,
    SIGNED_RESTRICTION_SCHEMA,
    bind_verified_restriction_signature,
    canonical_restriction_signature_message,
    verify_restriction_signature,
    queue_signed_restriction_event,
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


def test_verified_v4_envelope_queues_only_after_signature_verification():
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
    signed = bind_verified_restriction_signature(
        item,
        signing_key_id=SIGNING_KEY_ID,
        signature_b64url=signature,
        verifier=verifier,
    )

    patch, stable_id = queue_signed_restriction_event({}, signed)
    entry = patch[EVENT_OUTBOX_REGISTRY_KEY][stable_id]

    assert stable_id == item.outbox_event_id
    assert entry["actor"] == "PRIME_SENTINEL"
    assert entry["payload"]["schema"] == SIGNED_RESTRICTION_SCHEMA
    assert entry["payload"]["restriction"] == item.semantic_document()
    assert entry["payload"]["prime_signature"]["restriction_id"] == item.restriction_id
    assert entry["payload"]["prime_signature"]["signing_key_id"] == SIGNING_KEY_ID
    assert entry["payload"]["raw_content_persisted"] is False

    serialized = str(entry)
    assert "signature test raw input must not persist" not in serialized
    assert "signature test raw output must not persist" not in serialized
    assert KEY.decode("utf-8") not in serialized


def test_tampered_evidence_cannot_be_bound_or_queued_as_verified_v4():
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
    object.__setattr__(tampered, "policy_ref", "TAMPERED_POLICY")

    with pytest.raises(PrimeSentinelAuthorizationError, match="signature"):
        bind_verified_restriction_signature(
            tampered,
            signing_key_id=SIGNING_KEY_ID,
            signature_b64url=signature,
            verifier=verifier,
        )


def _signed_audit_record(private, verifier):
    item = evidence()
    signature = _b64url(
        private.sign(
            canonical_restriction_signature_message(
                item,
                signing_key_id=SIGNING_KEY_ID,
            )
        )
    )
    signed = bind_verified_restriction_signature(
        item,
        signing_key_id=SIGNING_KEY_ID,
        signature_b64url=signature,
        verifier=verifier,
    )
    payload = signed.semantic_document()
    payload["_outbox_event_id"] = signed.outbox_event_id
    payload["_delivery_semantics"] = "AT_LEAST_ONCE"
    return item, signed, AuditRecord(
        timestamp="2026-09-17T23:00:01+00:00",
        event="content_restriction_recorded",
        actor="PRIME_SENTINEL",
        payload=payload,
    ).model_dump(mode="json")


def test_v4_observability_reverifies_signature_and_minimizes_projection():
    private, verifier = _signing_material()
    item, signed, record = _signed_audit_record(private, verifier)

    projected = project_restriction_audit_record(record, verifier=verifier)

    assert projected["provenance_schema"] == SIGNED_RESTRICTION_SCHEMA
    assert projected["restriction_schema"] == item.semantic_document()["schema"]
    assert projected["signature_verified"] is True
    assert projected["signing_key_id"] == SIGNING_KEY_ID
    assert projected["signing_key_fingerprint_sha256"] == (
        signed.signature.signing_key_fingerprint_sha256
    )
    assert "signature_b64url" not in projected
    assert "prime_signature" not in projected
    assert "safe_summary" not in projected
    assert "metadata" not in projected


def test_v4_signature_tampering_and_revocation_make_observability_unhealthy():
    private, verifier = _signing_material()
    _item, _signed, record = _signed_audit_record(private, verifier)

    tampered_signature = copy.deepcopy(record)
    sig = tampered_signature["payload"]["prime_signature"]["signature_b64url"]
    tampered_signature["payload"]["prime_signature"]["signature_b64url"] = (
        ("A" if sig[0] != "A" else "B") + sig[1:]
    )
    with pytest.raises(RestrictionObservabilityError, match="signature verification"):
        project_restriction_audit_record(tampered_signature, verifier=verifier)

    tampered_fingerprint = copy.deepcopy(record)
    tampered_fingerprint["payload"]["prime_signature"][
        "signing_key_fingerprint_sha256"
    ] = "0" * 64
    with pytest.raises(RestrictionObservabilityError, match="fingerprint mismatch"):
        project_restriction_audit_record(tampered_fingerprint, verifier=verifier)

    revoked = PrimeSentinelVerifier(
        public_keys_b64url={
            SIGNING_KEY_ID: _b64url(private.public_key().public_bytes_raw())
        },
        revoked_key_ids={SIGNING_KEY_ID},
    )
    report = restriction_observability(
        [record],
        recent_limit=1,
        verifier=revoked,
    )
    assert report["ok"] is False
    assert report["valid_restriction_events"] == 0
    assert report["malformed_restriction_events"] == 1


def test_v4_signed_message_digest_tampering_is_detected():
    private, verifier = _signing_material()
    _item, _signed, record = _signed_audit_record(private, verifier)
    tampered = copy.deepcopy(record)
    tampered["payload"]["prime_signature"]["signed_message_sha256"] = "f" * 64

    with pytest.raises(RestrictionObservabilityError, match="digest mismatch"):
        project_restriction_audit_record(tampered, verifier=verifier)
