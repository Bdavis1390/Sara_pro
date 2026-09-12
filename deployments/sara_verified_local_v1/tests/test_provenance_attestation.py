from __future__ import annotations

import hashlib
import hmac

from worldshepherd_sara.provenance_attestation import (
    ProvenanceAttestation,
    create_provenance_attestation,
    verify_provenance_attestation,
)


SECRET = b"test-only-shared-secret"
PACKAGE_DIGEST = "a" * 64


def _sign(message: bytes) -> bytes:
    return hmac.new(SECRET, message, hashlib.sha256).digest()


def _verify(message: bytes, signature: bytes, algorithm: str, key_id: str) -> bool:
    if algorithm != "HMAC-SHA256-TEST" or key_id != "test-key-1":
        return False
    expected = hmac.new(SECRET, message, hashlib.sha256).digest()
    return hmac.compare_digest(expected, signature)


def _attestation() -> ProvenanceAttestation:
    return create_provenance_attestation(
        package_digest=PACKAGE_DIGEST,
        signer_id="worldshepherd-test-signer",
        key_id="test-key-1",
        algorithm="HMAC-SHA256-TEST",
        issued_utc="2026-09-12T21:30:00Z",
        signer=_sign,
    )


def test_attestation_verifies_with_explicit_trust_policy():
    attestation = _attestation()

    assert verify_provenance_attestation(
        attestation,
        verifier=_verify,
        trusted_signer_ids={"worldshepherd-test-signer"},
        trusted_key_ids={"test-key-1"},
        trusted_algorithms={"HMAC-SHA256-TEST"},
    )


def test_attestation_rejects_changed_package_digest():
    attestation = _attestation().model_copy(update={"package_digest": "b" * 64})

    assert not verify_provenance_attestation(
        attestation,
        verifier=_verify,
        trusted_signer_ids={"worldshepherd-test-signer"},
        trusted_key_ids={"test-key-1"},
        trusted_algorithms={"HMAC-SHA256-TEST"},
    )


def test_attestation_rejects_untrusted_identity_or_algorithm():
    attestation = _attestation()

    assert not verify_provenance_attestation(
        attestation,
        verifier=_verify,
        trusted_signer_ids={"other-signer"},
    )
    assert not verify_provenance_attestation(
        attestation,
        verifier=_verify,
        trusted_key_ids={"other-key"},
    )
    assert not verify_provenance_attestation(
        attestation,
        verifier=_verify,
        trusted_algorithms={"OTHER"},
    )


def test_attestation_fails_closed_on_bad_signature_encoding_or_verifier_error():
    attestation = _attestation().model_copy(update={"signature_b64": "not-base64!!!"})
    assert not verify_provenance_attestation(attestation, verifier=_verify)

    valid = _attestation()

    def exploding_verifier(message: bytes, signature: bytes, algorithm: str, key_id: str) -> bool:
        raise RuntimeError("verifier unavailable")

    assert not verify_provenance_attestation(valid, verifier=exploding_verifier)
