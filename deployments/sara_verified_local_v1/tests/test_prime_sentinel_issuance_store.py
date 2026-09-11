from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import worldshepherd_sara.prime_sentinel_issuance_store as issuance_module
from worldshepherd_sara.prime_configuration_custody import PrimeEnvironment
from worldshepherd_sara.prime_sentinel_issuance_store import (
    PrimeSentinelIssuanceStore,
    PrimeSentinelLedgerFull,
    PrimeSentinelRequestConflict,
    reconcile_signed_records,
)
from worldshepherd_sara.prime_sentinel_ledger_integrity import (
    verify_issuance_ledger_integrity,
)


def make_store(tmp_path: Path) -> PrimeSentinelIssuanceStore:
    return PrimeSentinelIssuanceStore(tmp_path / "sentinel-data")


def prepare(
    store: PrimeSentinelIssuanceStore,
    request_id: str = "PSREQ-ledger-0001",
    prime_id: str = "PRIME-LEDGER-001",
):
    return store.prepare_or_get(
        request_id=request_id,
        prime_id=prime_id,
        target_environment=PrimeEnvironment.SPACE,
        lifetime_seconds=300,
        key_id="key-01",
    )


def signed_assertion(record, signature: str = "signature-value") -> dict[str, object]:
    return {
        "schema": "WS-PRIME-SENTINEL-AUTHZ-V1",
        "issuer": "PRIME_SENTINEL",
        "key_id": record.key_id,
        "authorization_id": record.authorization_id,
        "prime_id": record.prime_id,
        "action": "REQUALIFICATION_RELEASE",
        "target_environment": record.target_environment,
        "issued_at": record.issued_at,
        "expires_at": record.expires_at,
        "nonce": record.nonce,
        "signature_b64url": signature,
    }


def sign(store: PrimeSentinelIssuanceStore, record, signature: str = "signature-value"):
    assertion = signed_assertion(record, signature)
    return store.mark_signed(
        request_id=record.request_id,
        signature_b64url=signature,
        assertion=assertion,
    )


def test_prepare_is_durable_and_retry_preserves_authorization_identity(tmp_path):
    store = make_store(tmp_path)
    first = prepare(store)
    assert first.state == "PREPARED"

    restarted = PrimeSentinelIssuanceStore(store.data_dir)
    second = prepare(restarted)
    assert second.authorization_id == first.authorization_id
    assert second.nonce == first.nonce
    assert second.issued_at == first.issued_at
    assert second.expires_at == first.expires_at
    assert restarted.health()["records"] == 1
    assert restarted.health()["events"] == 1


def test_request_id_conflict_does_not_mutate_original_record(tmp_path):
    store = make_store(tmp_path)
    original = prepare(store, request_id="PSREQ-conflict-ledger-01", prime_id="P1")
    with pytest.raises(PrimeSentinelRequestConflict):
        store.prepare_or_get(
            request_id="PSREQ-conflict-ledger-01",
            prime_id="P2",
            target_environment=PrimeEnvironment.SPACE,
            lifetime_seconds=300,
            key_id="key-01",
        )
    persisted = store.get("PSREQ-conflict-ledger-01")
    assert persisted is not None
    assert persisted.authorization_id == original.authorization_id
    assert persisted.prime_id == "P1"


def test_signed_record_and_event_chain_survive_restart(tmp_path):
    store = make_store(tmp_path)
    record = prepare(store)
    signed = sign(store, record)
    assert signed.state == "SIGNED"

    restarted = PrimeSentinelIssuanceStore(store.data_dir)
    recovered = restarted.get(record.request_id)
    assert recovered is not None
    assert recovered.state == "SIGNED"
    assert recovered.assertion_dict() == signed_assertion(record)
    health = restarted.health()
    assert health["records"] == 1
    assert health["events"] == 2
    assert health["event_chain_ok"] is True
    integrity = verify_issuance_ledger_integrity(restarted)
    assert integrity["ok"] is True
    assert integrity["records"] == 1
    assert integrity["events"] == 2


def test_mark_signed_is_idempotent_for_identical_assertion(tmp_path):
    store = make_store(tmp_path)
    record = prepare(store)
    first = sign(store, record)
    second = sign(store, record)
    assert second.assertion_json == first.assertion_json
    assert store.health()["events"] == 2


def test_capacity_is_bounded_and_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(issuance_module, "MAX_ISSUANCE_RECORDS", 1)
    store = make_store(tmp_path)
    prepare(store, request_id="PSREQ-capacity-0001", prime_id="P1")
    with pytest.raises(PrimeSentinelLedgerFull):
        prepare(store, request_id="PSREQ-capacity-0002", prime_id="P2")
    assert store.health()["records"] == 1


def test_cross_table_integrity_detects_issuance_record_tampering(tmp_path):
    store = make_store(tmp_path)
    record = prepare(store)
    sign(store, record)

    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE issuance SET prime_id = ? WHERE request_id = ?",
            ("TAMPERED", record.request_id),
        )
        connection.commit()
    finally:
        connection.close()

    integrity = verify_issuance_ledger_integrity(store)
    assert integrity["ok"] is False
    assert integrity["reason"] in {
        "ISSUANCE_EVENT_PAYLOAD_MISMATCH",
        "SIGNED_ASSERTION_RECORD_MISMATCH",
    }


def test_event_chain_detects_event_hash_tampering(tmp_path):
    store = make_store(tmp_path)
    record = prepare(store)
    sign(store, record)

    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE issuance_events SET event_hash = ? WHERE sequence = 1",
            ("f" * 64,),
        )
        connection.commit()
    finally:
        connection.close()

    ok, count = store.verify_event_chain()
    assert ok is False
    assert count == 2
    assert verify_issuance_ledger_integrity(store)["ok"] is False


def test_database_symlink_is_rejected(tmp_path):
    data_dir = tmp_path / "sentinel-data"
    store = PrimeSentinelIssuanceStore(data_dir)
    real_db = tmp_path / "real.db"
    store.db_path.rename(real_db)
    store.db_path.symlink_to(real_db)
    with pytest.raises(Exception, match="regular file"):
        PrimeSentinelIssuanceStore(data_dir)


def test_reconciliation_classifies_not_presented_verified_consumed_and_inconsistent(tmp_path):
    store = make_store(tmp_path)
    record = prepare(store)
    signed = sign(store, record)

    not_presented = reconcile_signed_records(store.signed_records(), {})
    assert not_presented[0].classification == "ISSUED_NOT_PRESENTED"

    base = {
        "prime_id": signed.prime_id,
        "target_environment": signed.target_environment,
        "key_id": signed.key_id,
    }
    verified_registry = {
        "PRIME_SENTINEL_AUTHORIZATIONS": {
            signed.authorization_id: {**base, "status": "VERIFIED"}
        }
    }
    assert reconcile_signed_records(
        store.signed_records(), verified_registry
    )[0].classification == "VERIFIED"

    consumed_registry = {
        "PRIME_SENTINEL_AUTHORIZATIONS": {
            signed.authorization_id: {**base, "status": "CONSUMED"}
        }
    }
    assert reconcile_signed_records(
        store.signed_records(), consumed_registry
    )[0].classification == "CONSUMED"

    inconsistent_registry = {
        "PRIME_SENTINEL_AUTHORIZATIONS": {
            signed.authorization_id: {**base, "prime_id": "WRONG", "status": "CONSUMED"}
        }
    }
    result = reconcile_signed_records(store.signed_records(), inconsistent_registry)[0]
    assert result.classification == "INCONSISTENT"
    assert "prime_id" in (result.reason or "")


def test_ledger_contains_no_supplied_private_key_or_bearer_secret(tmp_path):
    store = make_store(tmp_path)
    record = prepare(store)
    sign(store, record, signature="not-a-secret-signature")
    raw = store.db_path.read_bytes()
    assert b"BEGIN PRIVATE KEY" not in raw
    assert b"prime-sentinel-test-token-that-is-long-and-independent" not in raw
