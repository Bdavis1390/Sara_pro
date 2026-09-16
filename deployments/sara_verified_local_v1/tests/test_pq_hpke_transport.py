from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey

from worldshepherd_sara.pq_hpke_transport import (
    PQHPKEError,
    PQPublicKeyRecord,
    PQRequestEnvelope,
    PQResponseEnvelope,
    open_request,
    open_response,
    prepare_request,
    prepare_response,
    public_key_from_record,
    public_key_record,
)


def test_mlkem768_hpke_request_and_encrypted_response_round_trip():
    server = MLKEM768PrivateKey.generate()
    now = datetime.now(timezone.utc)
    prepared = prepare_request(
        service="ECHO_SENTINEL_LINK",
        operation="status",
        request_id="PQREQ-roundtrip-00000001",
        bearer_token="t" * 64,
        payload={"probe": "pq"},
        recipient_public_key=server.public_key(),
        now=now,
    )
    opened = open_request(prepared.envelope, recipient_private_key=server, now=now)
    assert opened.request.bearer_token == "t" * 64
    assert opened.request.payload == {"probe": "pq"}

    response = prepare_response(
        service="ECHO_SENTINEL_LINK",
        operation="status",
        request_id=prepared.envelope.request_id,
        status_code=200,
        payload={"ok": True, "post_quantum_transport": True},
        reply_public_key=opened.reply_public_key,
    )
    decoded = open_response(response, reply_private_key=prepared.reply_private_key)
    assert decoded.status_code == 200
    assert decoded.payload["post_quantum_transport"] is True


def test_public_key_record_is_pinnable_and_rejects_substitution():
    server = MLKEM768PrivateKey.generate()
    record = public_key_record(server, key_id="ECHO-PQ-TRANSPORT-K1")
    assert record.kem == "ML-KEM-768"
    assert record.kdf == "HKDF-SHA512"
    assert record.aead == "AES-256-GCM"
    assert len(record.fingerprint_sha256) == 64
    public_key_from_record(record, expected_fingerprint=record.fingerprint_sha256)

    other = public_key_record(MLKEM768PrivateKey.generate(), key_id="ECHO-PQ-TRANSPORT-K1")
    with pytest.raises(PQHPKEError, match="not pinned"):
        public_key_from_record(other, expected_fingerprint=record.fingerprint_sha256)

    mutated = record.model_copy(update={"fingerprint_sha256": "0" * 64})
    with pytest.raises(PQHPKEError, match="fingerprint mismatch"):
        public_key_from_record(mutated)


def test_wrong_private_key_cannot_decrypt_request():
    server = MLKEM768PrivateKey.generate()
    prepared = prepare_request(
        service="PRIME_SENTINEL",
        operation="issue",
        request_id="PQREQ-wrong-key-0000001",
        bearer_token="a" * 64,
        payload={},
        recipient_public_key=server.public_key(),
    )
    with pytest.raises(PQHPKEError, match="decryption failed"):
        open_request(prepared.envelope, recipient_private_key=MLKEM768PrivateKey.generate())


def test_outer_operation_context_substitution_breaks_decryption():
    server = MLKEM768PrivateKey.generate()
    prepared = prepare_request(
        service="ECHO_SENTINEL_LINK",
        operation="ingest",
        request_id="PQREQ-context-000000001",
        bearer_token="a" * 64,
        payload={"x": 1},
        recipient_public_key=server.public_key(),
    )
    substituted = prepared.envelope.model_copy(update={"operation": "checkpoint"})
    with pytest.raises(PQHPKEError, match="decryption failed"):
        open_request(substituted, recipient_private_key=server)


def test_ciphertext_tamper_is_rejected():
    server = MLKEM768PrivateKey.generate()
    prepared = prepare_request(
        service="ECHO_SENTINEL_LINK",
        operation="reconcile",
        request_id="PQREQ-tamper-0000000001",
        bearer_token="a" * 64,
        payload={"records": []},
        recipient_public_key=server.public_key(),
    )
    raw = bytearray(base64.urlsafe_b64decode(prepared.envelope.ciphertext_b64url + "=" * (-len(prepared.envelope.ciphertext_b64url) % 4)))
    raw[-1] ^= 1
    tampered = prepared.envelope.model_copy(
        update={"ciphertext_b64url": base64.urlsafe_b64encode(bytes(raw)).rstrip(b"=").decode("ascii")}
    )
    with pytest.raises(PQHPKEError, match="decryption failed"):
        open_request(tampered, recipient_private_key=server)


def test_expired_and_future_requests_fail_after_valid_decryption():
    server = MLKEM768PrivateKey.generate()
    now = datetime.now(timezone.utc)
    expired = prepare_request(
        service="SARA",
        operation="health",
        request_id="PQREQ-expired-000000001",
        bearer_token="a" * 64,
        payload={},
        recipient_public_key=server.public_key(),
        now=now - timedelta(seconds=45),
        lifetime_seconds=30,
    )
    with pytest.raises(PQHPKEError, match="expired"):
        open_request(expired.envelope, recipient_private_key=server, now=now)

    future = prepare_request(
        service="SARA",
        operation="health",
        request_id="PQREQ-future-0000000001",
        bearer_token="a" * 64,
        payload={},
        recipient_public_key=server.public_key(),
        now=now + timedelta(seconds=20),
    )
    with pytest.raises(PQHPKEError, match="future"):
        open_request(future.envelope, recipient_private_key=server, now=now)


def test_response_requires_the_ephemeral_reply_private_key_and_bound_context():
    server = MLKEM768PrivateKey.generate()
    prepared = prepare_request(
        service="PRIME_SENTINEL",
        operation="issue",
        request_id="PQREQ-response-00000001",
        bearer_token="a" * 64,
        payload={},
        recipient_public_key=server.public_key(),
    )
    opened = open_request(prepared.envelope, recipient_private_key=server)
    response = prepare_response(
        service="PRIME_SENTINEL",
        operation="issue",
        request_id=prepared.envelope.request_id,
        status_code=200,
        payload={"ok": True},
        reply_public_key=opened.reply_public_key,
    )
    with pytest.raises(PQHPKEError, match="decryption failed"):
        open_response(response, reply_private_key=MLKEM768PrivateKey.generate())

    substituted = response.model_copy(update={"operation": "status"})
    with pytest.raises(PQHPKEError, match="decryption failed"):
        open_response(substituted, reply_private_key=prepared.reply_private_key)


def test_envelope_models_reject_extra_fields():
    with pytest.raises(ValueError):
        PQRequestEnvelope.model_validate(
            {
                "service": "SARA",
                "operation": "health",
                "request_id": "PQREQ-extra-00000000001",
                "ciphertext_b64url": "AA",
                "reply_public_key_b64url": "AA",
                "unexpected": True,
            }
        )
    with pytest.raises(ValueError):
        PQResponseEnvelope.model_validate(
            {
                "service": "SARA",
                "operation": "health",
                "request_id": "PQREQ-extra-response-001",
                "ciphertext_b64url": "AA",
                "unexpected": True,
            }
        )
