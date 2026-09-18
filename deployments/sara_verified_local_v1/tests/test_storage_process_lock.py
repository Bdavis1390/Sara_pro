from __future__ import annotations

import multiprocessing as mp
import os
import stat
import time
from pathlib import Path

import pytest

from worldshepherd_sara.storage import DurableStore


def _increment_registry_counter(
    data_dir: str,
    start_event,
    result_queue,
    *,
    hold_seconds: float = 0.075,
) -> None:
    """Independent-process worker used to exercise the POSIX registry lock."""

    try:
        store = DurableStore(data_dir)
        if not store.registry_cross_process_lock_supported:
            result_queue.put(("unsupported", None))
            return
        if not start_event.wait(timeout=10):
            result_queue.put(("error", "start timeout"))
            return

        def operation(registry):
            current = int(registry.get("PROCESS_COUNTER", 0))
            # Enlarge the read/derive/write overlap window. Without a process-
            # visible transaction lock, concurrent workers can all derive from
            # the same stale value and overwrite one another.
            time.sleep(hold_seconds)
            updated = current + 1
            return {"PROCESS_COUNTER": updated}, updated

        result = store.transact_registry(operation)
        result_queue.put(("ok", result))
    except BaseException as exc:  # pragma: no cover - surfaced to parent assertion.
        result_queue.put(("error", f"{type(exc).__name__}: {exc}"))


def _spawn_context():
    # spawn guarantees the workers do not inherit the parent's lock descriptors
    # or in-memory RLock state, so this is genuinely a multi-process test.
    return mp.get_context("spawn")


def test_registry_lock_file_is_private_and_cross_process_support_is_explicit(tmp_path):
    store = DurableStore(tmp_path)

    assert stat.S_IMODE(store.registry_lock_path.stat().st_mode) == 0o600
    if os.name == "posix":
        assert store.registry_cross_process_lock_supported is True


def test_independent_process_transactions_do_not_lose_updates(tmp_path):
    parent_store = DurableStore(tmp_path)
    if not parent_store.registry_cross_process_lock_supported:
        pytest.skip("POSIX flock is unavailable on this runtime")

    parent_store.patch_registry({"PROCESS_COUNTER": 0})
    ctx = _spawn_context()
    start_event = ctx.Event()
    result_queue = ctx.Queue()
    process_count = 4
    workers = [
        ctx.Process(
            target=_increment_registry_counter,
            args=(str(tmp_path), start_event, result_queue),
            kwargs={"hold_seconds": 0.075},
        )
        for _ in range(process_count)
    ]

    for worker in workers:
        worker.start()
    start_event.set()

    results = [result_queue.get(timeout=20) for _ in workers]
    for worker in workers:
        worker.join(timeout=20)
        assert worker.exitcode == 0

    assert all(status == "ok" for status, _value in results), results
    committed_values = sorted(value for _status, value in results)
    assert committed_values == list(range(1, process_count + 1))
    assert parent_store.get_registry()["PROCESS_COUNTER"] == process_count


def test_process_lock_serializes_repeated_contention_rounds(tmp_path):
    parent_store = DurableStore(tmp_path)
    if not parent_store.registry_cross_process_lock_supported:
        pytest.skip("POSIX flock is unavailable on this runtime")

    ctx = _spawn_context()
    process_count = 3
    rounds = 3

    for round_index in range(rounds):
        parent_store.patch_registry({"PROCESS_COUNTER": 0, "ROUND": round_index})
        start_event = ctx.Event()
        result_queue = ctx.Queue()
        workers = [
            ctx.Process(
                target=_increment_registry_counter,
                args=(str(tmp_path), start_event, result_queue),
                kwargs={"hold_seconds": 0.05},
            )
            for _ in range(process_count)
        ]
        for worker in workers:
            worker.start()
        start_event.set()

        results = [result_queue.get(timeout=20) for _ in workers]
        for worker in workers:
            worker.join(timeout=20)
            assert worker.exitcode == 0

        assert all(status == "ok" for status, _value in results), results
        registry = parent_store.get_registry()
        assert registry["ROUND"] == round_index
        assert registry["PROCESS_COUNTER"] == process_count


def test_registry_lock_symlink_is_rejected_when_no_follow_is_supported(tmp_path):
    if not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("runtime does not expose O_NOFOLLOW")

    root = Path(tmp_path)
    target = root / "lock-target"
    target.write_text("do-not-follow\n", encoding="utf-8")
    (root / "registry.lock").symlink_to(target)

    with pytest.raises(RuntimeError, match="registry lock file"):
        DurableStore(root)
