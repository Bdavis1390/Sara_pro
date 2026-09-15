from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.persistent_audit_store import PersistentAuditDescriptorStore


def _record(sequence: int) -> AuditRecord:
    return AuditRecord.create(
        event="persistent_audit_test",
        actor="test",
        payload={"sequence": sequence},
    )


def _records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_persistent_descriptor_reused_and_every_record_preserved(tmp_path):
    store = PersistentAuditDescriptorStore(tmp_path)
    store.append_audit(_record(1))
    first_fd = store._audit_fd
    first_identity = store._audit_identity
    assert first_fd is not None
    assert first_identity is not None

    store.append_audit(_record(2))
    assert store._audit_fd == first_fd
    assert store._audit_identity == first_identity
    assert [row["payload"]["sequence"] for row in _records(store.audit_path)] == [1, 2]
    store.close()


def test_concurrent_appends_are_exact_once(tmp_path):
    store = PersistentAuditDescriptorStore(tmp_path)
    count = 64
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda sequence: store.append_audit(_record(sequence)), range(count)))

    rows = _records(store.audit_path)
    observed = [int(row["payload"]["sequence"]) for row in rows]
    assert len(observed) == count
    assert sorted(observed) == list(range(count))
    assert len(set(observed)) == count
    store.close()


def test_permission_drift_fails_closed(tmp_path):
    store = PersistentAuditDescriptorStore(tmp_path)
    store.append_audit(_record(1))
    os.chmod(store.audit_path, 0o640)

    with pytest.raises(RuntimeError, match="mode changed"):
        store.append_audit(_record(2))

    store.close()


def test_path_replacement_fails_closed(tmp_path):
    store = PersistentAuditDescriptorStore(tmp_path)
    store.append_audit(_record(1))
    original = tmp_path / "audit-original.jsonl"
    store.audit_path.rename(original)
    store.audit_path.write_text("", encoding="utf-8")
    store.audit_path.chmod(0o600)

    with pytest.raises(RuntimeError, match="path was replaced"):
        store.append_audit(_record(2))

    store.close()


def test_fsync_failure_propagates_before_success(monkeypatch, tmp_path):
    store = PersistentAuditDescriptorStore(tmp_path)
    store.append_audit(_record(1))
    audit_fd = store._audit_fd
    assert audit_fd is not None
    real_fsync = os.fsync

    def fail_audit_fsync(descriptor: int) -> None:
        if descriptor == audit_fd:
            raise OSError("injected fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fail_audit_fsync)
    with pytest.raises(OSError, match="injected fsync failure"):
        store.append_audit(_record(2))
    store.close()


def test_closed_store_rejects_new_appends(tmp_path):
    store = PersistentAuditDescriptorStore(tmp_path)
    store.append_audit(_record(1))
    store.close()
    with pytest.raises(RuntimeError, match="store is closed"):
        store.append_audit(_record(2))
