from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from worldshepherd_sara import echo_event_store as echo_store_module
from worldshepherd_sara.echo_event_store import (
    EchoEventConflict,
    EchoEventStore,
    EchoEventStoreError,
    EchoStoreFull,
)
from worldshepherd_sara.echo_persistence_service import (
    ECHO_TOKEN_FILE_ENV,
    EchoServiceConfigError,
    create_echo_app,
)
from worldshepherd_sara.models import AuditRecord


TOKEN = "echo-test-token-that-is-long-and-independent-12345"
EVENT_ID = "SARA-EVENT-11111111-2222-3333-4444-555555555555"


def audit_record(*, timestamp: str = "2026-09-10T20:00:00+00:00", value: int = 1) -> AuditRecord:
    return AuditRecord(
        timestamp=timestamp,
        event="prime_custody_provenance",
        actor="admin_operator",
        payload={
            "_outbox_event_id": EVENT_ID,
            "_delivery_semantics": "AT_LEAST_ONCE",
            "prime_id": "PRIME-ECHO-TEST",
            "transition_id": "11111111-2222-3333-4444-555555555555",
            "value": value,
        },
    )


def configure_service(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    data_dir = tmp_path / "echo-data"
    data_dir.mkdir(mode=0o700)
    token_path = tmp_path / "echo-token"
    token_path.write_text(TOKEN + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    monkeypatch.setenv("ECHO_DATA_DIR", str(data_dir))
    monkeypatch.setenv(ECHO_TOKEN_FILE_ENV, str(token_path))
    monkeypatch.delenv("SARA_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SARA_RELAY_TOKEN", raising=False)
    monkeypatch.delenv("PRIME_SENTINEL_SERVICE_TOKEN", raising=False)
    return data_dir, token_path


def test_store_deduplicates_same_semantics_even_when_audit_timestamp_changes(tmp_path):
    store = EchoEventStore(tmp_path.resolve())
    first = store.ingest(audit_record())
    replay = store.ingest(audit_record(timestamp="2026-09-10T20:01:00+00:00"))

    assert first.outcome == "STORED"
    assert replay.outcome == "DEDUPLICATED"
    assert replay.record.event_id == EVENT_ID
    assert replay.record.semantic_sha256 == first.record.semantic_sha256
    assert replay.record.delivery_count == 2
    assert replay.record.first_audit_timestamp != replay.record.last_audit_timestamp
    assert store.health()["stored_events"] == 1


def test_store_persists_deduplication_across_restart(tmp_path):
    path = tmp_path.resolve()
    first = EchoEventStore(path).ingest(audit_record())
    replay = EchoEventStore(path).ingest(
        audit_record(timestamp="2026-09-10T20:02:00+00:00")
    )
    assert replay.outcome == "DEDUPLICATED"
    assert replay.record.semantic_sha256 == first.record.semantic_sha256
    assert replay.record.delivery_count == 2


def test_same_event_id_with_different_semantics_is_rejected_without_overwrite(tmp_path):
    store = EchoEventStore(tmp_path.resolve())
    original = store.ingest(audit_record()).record
    with pytest.raises(EchoEventConflict, match="different semantic content"):
        store.ingest(audit_record(value=2))

    retained = store.get(EVENT_ID)
    assert retained is not None
    assert retained.semantic_sha256 == original.semantic_sha256
    assert retained.payload()["value"] == 1
    assert retained.delivery_count == 1
    assert store.health()["rejected_conflicts"] == 1


def test_store_requires_stable_outbox_id_and_at_least_once_marker(tmp_path):
    store = EchoEventStore(tmp_path.resolve())
    missing_id = audit_record()
    missing_id.payload.pop("_outbox_event_id")
    with pytest.raises(EchoEventStoreError, match="_outbox_event_id"):
        store.ingest(missing_id)

    wrong_semantics = audit_record()
    wrong_semantics.payload["_delivery_semantics"] = "EXACTLY_ONCE"
    with pytest.raises(EchoEventStoreError, match="AT_LEAST_ONCE"):
        store.ingest(wrong_semantics)


def test_store_capacity_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(echo_store_module, "MAX_ECHO_EVENTS", 1)
    store = EchoEventStore(tmp_path.resolve())
    store.ingest(audit_record())
    second = audit_record()
    second.payload["_outbox_event_id"] = "SARA-EVENT-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    second.payload["transition_id"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    with pytest.raises(EchoStoreFull, match="capacity"):
        store.ingest(second)


def test_health_detects_semantic_row_tampering(tmp_path):
    store = EchoEventStore(tmp_path.resolve())
    store.ingest(audit_record())
    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE events SET actor='tampered-actor' WHERE event_id=?",
            (EVENT_ID,),
        )
        connection.commit()
    finally:
        connection.close()
    health = store.health()
    assert health["ok"] is False
    assert health["semantic_integrity_errors"] == 1


def test_reconcile_is_window_scoped_and_classifies_matches_and_gaps(tmp_path):
    store = EchoEventStore(tmp_path.resolve())
    store.ingest(audit_record())
    second = audit_record()
    second.payload["_outbox_event_id"] = "SARA-EVENT-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    second.payload["transition_id"] = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    result = store.reconcile([audit_record(), second])
    classes = {entry["event_id"]: entry["classification"] for entry in result["entries"]}
    assert result["scope"] == "PROVIDED_SARA_AUDIT_WINDOW"
    assert classes[EVENT_ID] == "MATCHED"
    assert classes[second.payload["_outbox_event_id"]] == "SARA_ONLY"


def test_service_ingest_retry_restart_and_conflict(tmp_path, monkeypatch):
    data_dir, _token_path = configure_service(tmp_path, monkeypatch)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    body = audit_record().model_dump(mode="json")

    with TestClient(create_echo_app()) as client:
        missing = client.post("/v1/ingest", json=body)
        assert missing.status_code == 401
        first = client.post("/v1/ingest", headers=headers, json=body)
        replay_body = dict(body)
        replay_body["timestamp"] = "2026-09-10T20:03:00+00:00"
        replay = client.post("/v1/ingest", headers=headers, json=replay_body)
        assert first.status_code == 200
        assert first.json()["outcome"] == "STORED"
        assert replay.json()["outcome"] == "DEDUPLICATED"
        assert replay.json()["delivery_count"] == 2

    monkeypatch.setenv("ECHO_DATA_DIR", str(data_dir))
    with TestClient(create_echo_app()) as client:
        replay_body["timestamp"] = "2026-09-10T20:04:00+00:00"
        after_restart = client.post("/v1/ingest", headers=headers, json=replay_body)
        assert after_restart.status_code == 200
        assert after_restart.json()["delivery_count"] == 3
        status = client.get("/v1/status", headers=headers)
        assert status.status_code == 200
        assert status.json()["stored_events"] == 1

        conflict_body = dict(body)
        conflict_body["payload"] = dict(body["payload"])
        conflict_body["payload"]["value"] = 99
        conflict = client.post("/v1/ingest", headers=headers, json=conflict_body)
        assert conflict.status_code == 409


def test_service_reconcile_and_public_health_do_not_expose_token(tmp_path, monkeypatch):
    _data_dir, token_path = configure_service(tmp_path, monkeypatch)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    body = audit_record().model_dump(mode="json")
    with TestClient(create_echo_app()) as client:
        assert client.post("/v1/ingest", headers=headers, json=body).status_code == 200
        reconcile = client.post(
            "/v1/reconcile", headers=headers, json={"records": [body]}
        )
        assert reconcile.status_code == 200
        assert reconcile.json()["counts"]["MATCHED"] == 1
        public = client.get("/readyz")
        assert public.status_code == 200
        combined = client.get("/livez").text + public.text
        assert TOKEN not in combined
        assert str(token_path) not in combined


def test_service_rejects_insecure_or_symlink_token_file(tmp_path, monkeypatch):
    data_dir = tmp_path / "echo-data"
    data_dir.mkdir(mode=0o700)
    real = tmp_path / "token"
    real.write_text(TOKEN + "\n", encoding="utf-8")
    real.chmod(0o644)
    monkeypatch.setenv("ECHO_DATA_DIR", str(data_dir))
    monkeypatch.setenv(ECHO_TOKEN_FILE_ENV, str(real))
    with pytest.raises(EchoServiceConfigError, match="group/other permissions"):
        create_echo_app()

    real.chmod(0o600)
    link = tmp_path / "token-link"
    link.symlink_to(real)
    monkeypatch.setenv(ECHO_TOKEN_FILE_ENV, str(link))
    with pytest.raises(EchoServiceConfigError, match="symbolic link"):
        create_echo_app()
