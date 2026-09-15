from __future__ import annotations

import hashlib
import hmac

import pytest

from worldshepherd_sara.provenance_attestation import create_provenance_attestation
from worldshepherd_sara.trust_registry import (
    TrustKeyRecord,
    build_trust_registry,
    trust_record_for_attestation,
    verify_attestation_with_registry,
    verify_trust_registry,
)


SECRET = b"test-only-trust-registry-secret"
PACKAGE_DIGEST = "c" * 64


def _sign(message: bytes) -> bytes:
    return hmac.new(SECRET, message, hashlib.sha256).digest()


def _verify(message: bytes, signature: bytes, algorithm: str, key_id: str) -> bool:
    if algorithm != "HMAC-SHA256-TEST" or key_id not in {"key-active", "key-retired", "key-revoked"}:
        return False
    expected = hmac.new(SECRET, message, hashlib.sha256).digest()
    return hmac.compare_digest(expected, signature)


def _record(
    *,
    key_id: str,
    status: str,
    valid_from_utc: str = "2026-09-01T00:00:00Z",
    valid_until_utc: str | None = None,
    revoked_utc: str | None = None,
    successor_key_id: str | None = None,
) -> TrustKeyRecord:
    return TrustKeyRecord(
        signer_id="worldshepherd-test-signer",
        key_id=key_id,
        algorithm="HMAC-SHA256-TEST",
        status=status,
        valid_from_utc=valid_from_utc,
        valid_until_utc=valid_until_utc,
        revoked_utc=revoked_utc,
        successor_key_id=successor_key_id,
    )


def _attestation(*, key_id: str, issued_utc: str):
    return create_provenance_attestation(
        package_digest=PACKAGE_DIGEST,
        signer_id="worldshepherd-test-signer",
        key_id=key_id,
        algorithm="HMAC-SHA256-TEST",
        issued_utc=issued_utc,
        signer=_sign,
    )


def test_registry_is_deterministic_and_digest_verified():
    active = _record(key_id="key-active", status="ACTIVE")
    retired = _record(
        key_id="key-retired",
        status="RETIRED",
        valid_until_utc="2026-09-10T00:00:00Z",
        successor_key_id="key-active",
    )

    first = build_trust_registry(
        registry_id="registry-1",
        generated_utc="2026-09-12T22:30:00Z",
        entries=[active, retired],
    )
    second = build_trust_registry(
        registry_id="registry-1",
        generated_utc="2026-09-12T22:30:00Z",
        entries=[retired, active],
    )

    assert first.registry_digest == second.registry_digest
    assert verify_trust_registry(first)


def test_active_key_verifies_attestation():
    registry = build_trust_registry(
        registry_id="registry-active",
        generated_utc="2026-09-12T22:30:00Z",
        entries=[_record(key_id="key-active", status="ACTIVE")],
    )
    attestation = _attestation(key_id="key-active", issued_utc="2026-09-12T21:00:00Z")

    assert trust_record_for_attestation(attestation, registry) is not None
    assert verify_attestation_with_registry(attestation, registry=registry, verifier=_verify)


def test_retired_key_preserves_historical_verification_but_rejects_late_issuance():
    registry = build_trust_registry(
        registry_id="registry-retired",
        generated_utc="2026-09-12T22:30:00Z",
        entries=[
            _record(
                key_id="key-retired",
                status="RETIRED",
                valid_until_utc="2026-09-10T00:00:00Z",
                successor_key_id="key-active",
            )
        ],
    )

    historical = _attestation(key_id="key-retired", issued_utc="2026-09-09T12:00:00Z")
    too_late = _attestation(key_id="key-retired", issued_utc="2026-09-11T12:00:00Z")

    assert verify_attestation_with_registry(historical, registry=registry, verifier=_verify)
    assert not verify_attestation_with_registry(too_late, registry=registry, verifier=_verify)


def test_revoked_key_fails_closed_even_for_earlier_attestation():
    registry = build_trust_registry(
        registry_id="registry-revoked",
        generated_utc="2026-09-12T22:30:00Z",
        entries=[
            _record(
                key_id="key-revoked",
                status="REVOKED",
                revoked_utc="2026-09-12T20:00:00Z",
            )
        ],
    )
    attestation = _attestation(key_id="key-revoked", issued_utc="2026-09-11T12:00:00Z")

    assert trust_record_for_attestation(attestation, registry) is None
    assert not verify_attestation_with_registry(attestation, registry=registry, verifier=_verify)


def test_registry_rejects_duplicate_identity_and_detects_digest_tampering():
    record = _record(key_id="key-active", status="ACTIVE")
    with pytest.raises(ValueError):
        build_trust_registry(
            registry_id="registry-duplicate",
            generated_utc="2026-09-12T22:30:00Z",
            entries=[record, record],
        )

    registry = build_trust_registry(
        registry_id="registry-tamper",
        generated_utc="2026-09-12T22:30:00Z",
        entries=[record],
    )
    tampered = registry.model_copy(update={"registry_digest": "0" * 64})
    assert not verify_trust_registry(tampered)


def test_registry_validity_rules_fail_closed():
    with pytest.raises(ValueError):
        build_trust_registry(
            registry_id="registry-bad-retired",
            generated_utc="2026-09-12T22:30:00Z",
            entries=[_record(key_id="key-retired", status="RETIRED")],
        )

    with pytest.raises(ValueError):
        build_trust_registry(
            registry_id="registry-bad-revoked",
            generated_utc="2026-09-12T22:30:00Z",
            entries=[_record(key_id="key-revoked", status="REVOKED")],
        )
