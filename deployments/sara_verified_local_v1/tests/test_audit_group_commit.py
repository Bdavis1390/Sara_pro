from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


def _record(index: int) -> AuditRecord:
    return AuditRecord.create(
        event="group_commit_test",
        actor="test",
        payload={"index": index},
    )


def test_group_commit_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("SARA_AUDIT_GROUP_COMMIT", raising=False)
    store = DurableStore(tmp_path / "data")
    assert store.audit_group_commit_enabled is False


def test_group_commit_batches_concurrent_callers_and_preserves_exact_records(tmp_path):
    store = DurableStore(
        tmp_path / "data",
        audit_group_commit=True,
        audit_group_commit_window_ms=5.0,
    )
    barrier = threading.Barrier(8)
    batch_sizes: list[int] = []
    original = store._write_audit_lines

    def counted_write(lines: list[str]) -> None:
        batch_sizes.append(len(lines))
        original(lines)

    store._write_audit_lines = counted_write  # type: ignore[method-assign]

    def append_one(index: int) -> None:
        barrier.wait()
        store.append_audit(_record(index))

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(append_one, range(8)))

    records = [
        record
        for record in store.read_audit(16)
        if record.get("event") == "group_commit_test"
    ]
    assert sorted(record["payload"]["index"] for record in records) == list(range(8))
    assert sum(batch_sizes) == 8
    assert max(batch_sizes) > 1


def test_group_commit_does_not_return_before_batch_write_completes(tmp_path):
    store = DurableStore(
        tmp_path / "data",
        audit_group_commit=True,
        audit_group_commit_window_ms=2.0,
    )
    durable = threading.Event()
    original = store._write_audit_lines

    def delayed_write(lines: list[str]) -> None:
        time.sleep(0.02)
        original(lines)
        durable.set()

    store._write_audit_lines = delayed_write  # type: ignore[method-assign]
    returned_after_durable: list[bool] = []

    def append_one(index: int) -> None:
        store.append_audit(_record(index))
        returned_after_durable.append(durable.is_set())

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(append_one, range(4)))

    assert returned_after_durable == [True, True, True, True]


def test_group_commit_propagates_batch_failure_to_all_waiters(tmp_path):
    store = DurableStore(
        tmp_path / "data",
        audit_group_commit=True,
        audit_group_commit_window_ms=5.0,
    )
    barrier = threading.Barrier(6)

    def fail_write(lines: list[str]) -> None:
        raise OSError("simulated durable audit failure")

    store._write_audit_lines = fail_write  # type: ignore[method-assign]

    def append_one(index: int) -> str:
        barrier.wait()
        with pytest.raises(RuntimeError, match="failed before durability"):
            store.append_audit(_record(index))
        return "failed_closed"

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(append_one, range(6)))

    assert results == ["failed_closed"] * 6
    assert store.read_audit(10) == []


def test_group_commit_window_is_bounded(tmp_path):
    with pytest.raises(ValueError, match="between 0 and"):
        DurableStore(
            tmp_path / "too-large",
            audit_group_commit=True,
            audit_group_commit_window_ms=10.1,
        )
