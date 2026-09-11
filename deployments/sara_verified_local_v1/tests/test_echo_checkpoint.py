from __future__ import annotations

import copy
import hashlib
import sqlite3

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.echo_checkpoint import (
    EchoCheckpointConfigError,
    EchoCheckpointError,
    EchoCheckpointManager,
)
from worldshepherd_sara.echo_checkpoint_integrity import check_checkpoint_integrity
from worldshepherd_sara.echo_checkpoint_verify import (
    EchoCheckpointVerificationError,
    verify_bundle,
    verify_chain,
)
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.echo_persistence_service import ECHO_TOKEN_FILE_ENV, create_echo_app
from worldshepherd_sara.models import AuditRecord


def record(event_id: str, value: int) -> AuditRecord:
    return AuditRecord(
        timestamp=f"2026-09-10T20:0{value}:00+00:00",
        event="prime_custody_provenance",
        actor="admin_operator",
        payload={
            "_outbox_event_id": event_id,
            "_delivery_semantics": "AT_LEAST_ONCE",
            "prime_id": "PRIME-CHECKPOINT-TEST",
            "value": value,
        },
    )


def manager(tmp_path, key: Ed25519PrivateKey) -> tuple[EchoEventStore, EchoCheckpointManager]:
    root = tmp_path / "echo-checkpoint-data"
    root.mkdir(mode=0o700)
    store = EchoEventStore(root.resolve())
    return store, EchoCheckpointManager(store, private_key=key, key_id="ECHO-CHECKPOINT-TEST-V1")


def test_two_checkpoint_chain_verifies_and_survives_manager_restart(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    store, checkpoints = manager(tmp_path, key)
    store.ingest(record("SARA-EVENT-11111111-1111-1111-1111-111111111111", 1))
    first = checkpoints.create_checkpoint()
    store.ingest(record("SARA-EVENT-22222222-2222-2222-2222-222222222222", 2))
    second = checkpoints.create_checkpoint()

    fingerprint = checkpoints.fingerprint_sha256
    summary = verify_chain([first, second], fingerprint)
    assert summary["status"] == "PASS"
    assert summary["checkpoint_count"] == 2
    assert summary["last_sequence"] == 2
    assert second["manifest"]["previous_checkpoint_sha256"] == first["checkpoint_sha256"]
    assert check_checkpoint_integrity(checkpoints)["ok"] is True

    restarted = EchoCheckpointManager(store, private_key=key, key_id="ECHO-CHECKPOINT-TEST-V1")
    status = check_checkpoint_integrity(restarted)
    assert status["checkpoint_count"] == 2
    assert restarted.get_checkpoint(2) == second


def test_bundle_tampering_and_unpinned_key_are_rejected(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    store, checkpoints = manager(tmp_path, key)
    store.ingest(record("SARA-EVENT-11111111-1111-1111-1111-111111111111", 1))
    store.ingest(record("SARA-EVENT-22222222-2222-2222-2222-222222222222", 2))
    bundle = checkpoints.create_checkpoint()
    fingerprint = checkpoints.fingerprint_sha256
    assert verify_bundle(bundle, fingerprint)["event_count"] == 2

    mutations = []
    deleted = copy.deepcopy(bundle)
    deleted["manifest"]["events"].pop()
    deleted["manifest"]["event_count"] = 1
    mutations.append(deleted)

    reordered = copy.deepcopy(bundle)
    reordered["manifest"]["events"].reverse()
    mutations.append(reordered)

    substituted = copy.deepcopy(bundle)
    substituted["manifest"]["events"][0]["semantic_sha256"] = "0" * 64
    mutations.append(substituted)

    bad_signature = copy.deepcopy(bundle)
    bad_signature["signature_b64url"] = "A" * 86
    mutations.append(bad_signature)

    for mutated in mutations:
        with pytest.raises(EchoCheckpointVerificationError):
            verify_bundle(mutated, fingerprint)

    other = Ed25519PrivateKey.generate().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    swapped = copy.deepcopy(bundle)
    swapped["public_key"]["public_key_b64url"] = __import__("base64").urlsafe_b64encode(other).rstrip(b"=").decode()
    swapped["public_key"]["fingerprint_sha256"] = hashlib.sha256(other).hexdigest()
    with pytest.raises(EchoCheckpointVerificationError, match="not trusted"):
        verify_bundle(swapped, fingerprint)


def test_chain_reordering_predecessor_and_monotonicity_fail(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    store, checkpoints = manager(tmp_path, key)
    store.ingest(record("SARA-EVENT-11111111-1111-1111-1111-111111111111", 1))
    first = checkpoints.create_checkpoint()
    store.ingest(record("SARA-EVENT-22222222-2222-2222-2222-222222222222", 2))
    second = checkpoints.create_checkpoint()
    fingerprint = checkpoints.fingerprint_sha256

    with pytest.raises(EchoCheckpointVerificationError):
        verify_chain([second, first], fingerprint)

    broken = copy.deepcopy(second)
    broken["manifest"]["previous_checkpoint_sha256"] = "0" * 64
    with pytest.raises(EchoCheckpointVerificationError):
        verify_chain([first, broken], fingerprint)


def test_stored_membership_corruption_is_detected(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    store, checkpoints = manager(tmp_path, key)
    store.ingest(record("SARA-EVENT-11111111-1111-1111-1111-111111111111", 1))
    checkpoints.create_checkpoint()
    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE echo_checkpoint_events SET semantic_sha256=? WHERE checkpoint_sequence=1",
            ("0" * 64,),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(EchoCheckpointError, match="membership"):
        check_checkpoint_integrity(checkpoints)


def test_key_id_cannot_be_rebound_to_new_key(tmp_path, echo_checkpoint_key):
    key, _path = echo_checkpoint_key
    store, _checkpoints = manager(tmp_path, key)
    with pytest.raises(EchoCheckpointConfigError, match="different key material"):
        EchoCheckpointManager(
            store,
            private_key=Ed25519PrivateKey.generate(),
            key_id="ECHO-CHECKPOINT-TEST-V1",
        )


def test_service_creates_exports_and_reports_signed_checkpoint(tmp_path, monkeypatch, echo_checkpoint_key):
    data_dir = tmp_path / "service-echo-data"
    data_dir.mkdir(mode=0o700)
    token = "echo-checkpoint-service-token-0123456789abcdef"
    token_path = tmp_path / "echo-service-token"
    token_path.write_text(token + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    monkeypatch.setenv("ECHO_DATA_DIR", str(data_dir.resolve()))
    monkeypatch.setenv(ECHO_TOKEN_FILE_ENV, str(token_path.resolve()))
    monkeypatch.delenv("SARA_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SARA_RELAY_TOKEN", raising=False)
    monkeypatch.delenv("PRIME_SENTINEL_SERVICE_TOKEN", raising=False)
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(create_echo_app()) as client:
        body = record("SARA-EVENT-11111111-1111-1111-1111-111111111111", 1).model_dump(mode="json")
        assert client.post("/v1/ingest", headers=headers, json=body).status_code == 200
        created = client.post("/v1/checkpoint", headers=headers)
        assert created.status_code == 201
        public = client.get("/v1/checkpoint/public-key", headers=headers)
        status = client.get("/v1/checkpoint/status", headers=headers)
        exported = client.get("/v1/checkpoint/1", headers=headers)
        assert public.status_code == status.status_code == exported.status_code == 200
        assert status.json()["checkpoint_count"] == 1
        assert exported.json() == created.json()
        assert "private" not in public.text.lower()

        ready = client.get("/readyz")
        assert ready.status_code == 200
        assert ready.json()["checkpoint_integrity"] == "HEALTHY"
