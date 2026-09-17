from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import worldshepherd_sara.echo_checkpoint as checkpoint_module
from worldshepherd_sara.echo_checkpoint import (
    CHECKPOINT_SIGNER_MODE_ENV,
    EXTERNAL_SIGNER_MODE,
    EchoCheckpointConfigError,
    EchoCheckpointError,
    EchoCheckpointManager,
)
from worldshepherd_sara.echo_checkpoint_verify import verify_bundle
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.models import AuditRecord


@dataclass
class ExternalTestSigner:
    private_key: Ed25519PrivateKey
    key_id: str = "EXTERNAL-SIGNER-TEST-V1"
    algorithm: str = "Ed25519"
    signed_messages: list[bytes] = field(default_factory=list)

    def public_key_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def sign(self, message: bytes) -> bytes:
        self.signed_messages.append(bytes(message))
        return self.private_key.sign(message)


@dataclass
class InvalidSignatureSigner(ExternalTestSigner):
    def sign(self, message: bytes) -> bytes:
        self.signed_messages.append(bytes(message))
        return b"\x00" * 64


def record(event_id: str, *, secret_marker: str) -> AuditRecord:
    return AuditRecord(
        timestamp="2026-09-17T23:45:00+00:00",
        event="g7_signer_boundary_test",
        actor="admin_operator",
        payload={
            "_outbox_event_id": event_id,
            "_delivery_semantics": "AT_LEAST_ONCE",
            "secret_marker_for_boundary_test": secret_marker,
        },
    )


def store_with_event(tmp_path, *, name: str = "echo-g7"):
    root = (tmp_path / name).resolve()
    store = EchoEventStore(root)
    marker = "RAW-EVENT-PAYLOAD-MUST-NOT-REACH-SIGNER"
    store.ingest(
        record(
            "SARA-EVENT-G7-11111111-1111-1111-1111-111111111111",
            secret_marker=marker,
        )
    )
    return store, marker


def test_injected_signer_creates_verifiable_checkpoint_without_payload_disclosure(
    tmp_path,
):
    store, marker = store_with_event(tmp_path)
    signer = ExternalTestSigner(Ed25519PrivateKey.generate())
    manager = EchoCheckpointManager(store, signer=signer)

    bundle = manager.create_checkpoint()

    assert len(signer.signed_messages) == 1
    signing_request = signer.signed_messages[0]
    assert marker.encode("utf-8") not in signing_request
    assert b"secret_marker_for_boundary_test" not in signing_request
    verified = verify_bundle(bundle, manager.fingerprint_sha256)
    assert verified["event_count"] == 1
    assert verified["key_id"] == signer.key_id


def test_invalid_external_signature_fails_before_checkpoint_persistence(tmp_path):
    store, _marker = store_with_event(tmp_path)
    signer = InvalidSignatureSigner(Ed25519PrivateKey.generate())
    manager = EchoCheckpointManager(store, signer=signer)

    with pytest.raises(EchoCheckpointError, match="unverifiable signature"):
        manager.create_checkpoint()

    assert manager.latest_status()["checkpoint_count"] == 0


def test_external_mode_never_falls_back_to_local_pem(tmp_path, monkeypatch):
    root = (tmp_path / "echo-external-mode").resolve()
    store = EchoEventStore(root)
    local_loader_called = False

    def forbidden_local_loader(_path: str):
        nonlocal local_loader_called
        local_loader_called = True
        raise AssertionError("local PEM loader must not be called in EXTERNAL mode")

    monkeypatch.setenv(CHECKPOINT_SIGNER_MODE_ENV, EXTERNAL_SIGNER_MODE)
    monkeypatch.setattr(checkpoint_module, "_read_private_key", forbidden_local_loader)

    with pytest.raises(
        EchoCheckpointConfigError,
        match="local PEM fallback is forbidden",
    ):
        EchoCheckpointManager.from_environment(store)

    assert local_loader_called is False


def test_signer_injection_cannot_be_combined_with_local_private_key(tmp_path):
    store, _marker = store_with_event(tmp_path)
    local_key = Ed25519PrivateKey.generate()
    signer = ExternalTestSigner(Ed25519PrivateKey.generate())

    with pytest.raises(
        EchoCheckpointConfigError,
        match="cannot be combined",
    ):
        EchoCheckpointManager(
            store,
            private_key=local_key,
            key_id="LOCAL-KEY",
            signer=signer,
        )


def test_unsupported_signer_algorithm_fails_closed(tmp_path):
    store, _marker = store_with_event(tmp_path)
    signer = ExternalTestSigner(
        Ed25519PrivateKey.generate(),
        algorithm="RSA-PSS",
    )

    with pytest.raises(
        EchoCheckpointConfigError,
        match="must use Ed25519",
    ):
        EchoCheckpointManager(store, signer=signer)


def test_external_key_id_cannot_be_rebound_to_different_key_material(tmp_path):
    store, _marker = store_with_event(tmp_path)
    first = ExternalTestSigner(
        Ed25519PrivateKey.generate(),
        key_id="EXTERNAL-BOUND-ID",
    )
    EchoCheckpointManager(store, signer=first)

    second = ExternalTestSigner(
        Ed25519PrivateKey.generate(),
        key_id="EXTERNAL-BOUND-ID",
    )
    with pytest.raises(
        EchoCheckpointConfigError,
        match="different key material",
    ):
        EchoCheckpointManager(store, signer=second)


def test_signer_boundary_is_software_precursor_not_g7_custody_proof(tmp_path):
    store, _marker = store_with_event(tmp_path)
    signer = ExternalTestSigner(Ed25519PrivateKey.generate())
    manager = EchoCheckpointManager(store, signer=signer)
    public = manager.public_key_record()

    assert public["algorithm"] == "Ed25519"
    assert "private" not in str(public).lower()
    assert manager.fingerprint_sha256
