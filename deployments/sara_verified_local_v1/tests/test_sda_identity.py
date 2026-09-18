from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationError,
    PrimeSentinelVerifier,
)
from worldshepherd_sara.sda import (
    SdaContractValidationState,
    SdaIngestDisposition,
    SdaInterfaceContract,
    SdaObservation,
    SdaSourceClass,
    SdaSourceIdentity,
    evaluate_sda_ingest,
)
from worldshepherd_sara.sda_identity import (
    SdaWorkloadIdentityAssertion,
    canonical_sda_workload_identity_message,
    verify_sda_workload_identity,
)


NOW = datetime(2026, 9, 17, 23, 45, tzinfo=timezone.utc)
KEY_ID = "SDA-WORKLOAD-K1"
TRANSPORT_CERT_SHA256 = "sha256:" + "d" * 64


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def signing_material():
    private = Ed25519PrivateKey.generate()
    verifier = PrimeSentinelVerifier(
        public_keys_b64url={
            KEY_ID: b64url(private.public_key().public_bytes_raw())
        }
    )
    return private, verifier


def signed_assertion(
    private: Ed25519PrivateKey,
    *,
    source_id: str = "SYNTH-RADAR-A",
    adapter_id: str = "WS-SDA-SYNTH",
    adapter_version: str = "1.0.0",
    issued_at: datetime = NOW - timedelta(seconds=5),
    expires_at: datetime = NOW + timedelta(minutes=2),
    key_id: str = KEY_ID,
    transport_cert_sha256: str = TRANSPORT_CERT_SHA256,
) -> SdaWorkloadIdentityAssertion:
    unsigned = SdaWorkloadIdentityAssertion(
        key_id=key_id,
        workload_id="spiffe://worldshepherd.internal/sda/adapter/synth-radar-a",
        source_id=source_id,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        transport_cert_sha256=transport_cert_sha256,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce="nonce-sda-workload-0001",
        signature_b64url="placeholder",
    )
    signature = b64url(private.sign(canonical_sda_workload_identity_message(unsigned)))
    return unsigned.model_copy(update={"signature_b64url": signature})


def contract() -> SdaInterfaceContract:
    value = SdaInterfaceContract(
        contract_id="SDA-CONTRACT-SYNTH-WORKLOAD-001",
        source_id="SYNTH-RADAR-A",
        adapter_id="WS-SDA-SYNTH",
        adapter_version="1.0.0",
        authoritative_spec_ref="internal://ws-sda/synthetic-contract-workload-v1",
        authoritative_spec_digest="sha256:" + "b" * 64,
        allowed_reference_frames=["GCRF"],
        allowed_releasability_tags=["US_ONLY"],
        max_age_seconds=600.0,
        max_future_skew_seconds=30.0,
        max_clock_uncertainty_seconds=0.05,
        validation_state=SdaContractValidationState.SYNTHETIC,
        validation_ref="test://sda-workload-contract",
        require_workload_identity=True,
        enabled=True,
    )
    return value


def observation(active: SdaInterfaceContract) -> SdaObservation:
    covariance = [[0.0 for _ in range(6)] for _ in range(6)]
    for index in range(6):
        covariance[index][index] = 1.0
    return SdaObservation(
        observation_id="OBS-WORKLOAD-001",
        source_event_id="EVENT-WORKLOAD-001",
        source_sequence=1,
        source=SdaSourceIdentity(
            source_id="SYNTH-RADAR-A",
            source_class=SdaSourceClass.SYNTHETIC,
            provider="Worldshepherd synthetic fixture",
            sensor_id="SYNTH-SENSOR-1",
            adapter_id="WS-SDA-SYNTH",
            adapter_version="1.0.0",
        ),
        observed_at=NOW,
        received_at=NOW + timedelta(seconds=1),
        time_system="UTC",
        clock_uncertainty_seconds=0.01,
        reference_frame="GCRF",
        position_km=(1.0, 2.0, 3.0),
        velocity_km_s=(0.1, 0.2, 0.3),
        covariance_6x6=covariance,
        measurement_confidence=0.8,
        source_reliability=0.8,
        handling_label="UNCLASSIFIED_SYNTHETIC",
        releasability_tags=["US_ONLY"],
        raw_source_digest="sha256:" + "a" * 64,
        interface_contract_id=active.contract_id,
        interface_contract_digest=active.digest(),
        transformation_refs=["adapter:synthetic-workload-v1"],
    )


def test_workload_assertion_rejects_overlong_lifetime():
    with pytest.raises(ValidationError, match="5 minutes"):
        SdaWorkloadIdentityAssertion(
            key_id=KEY_ID,
            workload_id="spiffe://worldshepherd.internal/sda/adapter/synth-radar-a",
            source_id="SYNTH-RADAR-A",
            adapter_id="WS-SDA-SYNTH",
            adapter_version="1.0.0",
            transport_cert_sha256=TRANSPORT_CERT_SHA256,
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=6),
            nonce="nonce-sda-workload-0001",
            signature_b64url="placeholder",
        )


def test_signed_workload_identity_verifies_with_public_key_only():
    private, verifier = signing_material()
    assertion = signed_assertion(private)
    verified = verify_sda_workload_identity(assertion, verifier=verifier, now=NOW)

    assert verified.source_id == "SYNTH-RADAR-A"
    assert verified.adapter_id == "WS-SDA-SYNTH"
    assert verified.key_id == KEY_ID
    assert verified.transport_cert_sha256 == TRANSPORT_CERT_SHA256
    assert len(verified.key_fingerprint_sha256) == 64


def test_workload_identity_rejects_signature_tamper_revoked_key_expiry_and_future_issue():
    private, verifier = signing_material()
    assertion = signed_assertion(private)

    tampered = assertion.model_copy(update={"source_id": "SPOOFED"})
    with pytest.raises(PrimeSentinelAuthorizationError, match="signature"):
        verify_sda_workload_identity(tampered, verifier=verifier, now=NOW)

    revoked = PrimeSentinelVerifier(
        public_keys_b64url={
            KEY_ID: b64url(private.public_key().public_bytes_raw())
        },
        revoked_key_ids={KEY_ID},
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="revoked"):
        verify_sda_workload_identity(assertion, verifier=revoked, now=NOW)

    expired = signed_assertion(
        private,
        issued_at=NOW - timedelta(minutes=3),
        expires_at=NOW - timedelta(seconds=1),
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="expired"):
        verify_sda_workload_identity(expired, verifier=verifier, now=NOW)

    future = signed_assertion(
        private,
        issued_at=NOW + timedelta(seconds=31),
        expires_at=NOW + timedelta(minutes=2),
    )
    with pytest.raises(PrimeSentinelAuthorizationError, match="future"):
        verify_sda_workload_identity(future, verifier=verifier, now=NOW)


def test_ingest_contract_fails_closed_without_required_workload_identity():
    active = contract()
    item = observation(active)

    result = evaluate_sda_ingest(item, contract=active, now=NOW)
    assert result.disposition == SdaIngestDisposition.REJECT
    assert any("requires verified workload identity" in reason for reason in result.reasons)


def test_ingest_accepts_only_identity_bound_to_exact_source_adapter_and_version():
    active = contract()
    item = observation(active)
    private, verifier = signing_material()

    correct = verify_sda_workload_identity(
        signed_assertion(private),
        verifier=verifier,
        now=NOW,
    )
    accepted = evaluate_sda_ingest(
        item,
        contract=active,
        workload_identity=correct,
        now=NOW,
    )
    assert accepted.disposition == SdaIngestDisposition.ACCEPT

    wrong_adapter = verify_sda_workload_identity(
        signed_assertion(private, adapter_id="OTHER-ADAPTER"),
        verifier=verifier,
        now=NOW,
    )
    rejected = evaluate_sda_ingest(
        item,
        contract=active,
        workload_identity=wrong_adapter,
        now=NOW,
    )
    assert rejected.disposition == SdaIngestDisposition.REJECT
    assert any("adapter identity mismatch" in reason for reason in rejected.reasons)


def test_identity_expiry_is_rechecked_at_ingest_to_close_verification_execution_gap():
    active = contract()
    item = observation(active)
    private, verifier = signing_material()

    assertion = signed_assertion(
        private,
        issued_at=NOW - timedelta(seconds=5),
        expires_at=NOW + timedelta(seconds=5),
    )
    verified = verify_sda_workload_identity(assertion, verifier=verifier, now=NOW)

    late = evaluate_sda_ingest(
        item,
        contract=active,
        workload_identity=verified,
        now=NOW + timedelta(seconds=6),
    )
    assert late.disposition == SdaIngestDisposition.REJECT
    assert any("expired" in reason for reason in late.reasons)
