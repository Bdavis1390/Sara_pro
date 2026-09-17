from __future__ import annotations

import multiprocessing
import os
import time

import pytest

from worldshepherd_sara.storage import DurableStore


def _increment_registry_worker(data_dir: str, ready, start, results) -> None:
    try:
        store = DurableStore(data_dir)
        ready.put(("ready", os.getpid()))
        if not start.wait(timeout=5):
            results.put(("error", "start timeout"))
            return

        def operation(registry):
            before = int(registry.get("cross_process_counter", 0))
            # Deliberately widen the lost-update window. Without a process-shared
            # transaction lock, both workers can read the same value before either
            # write completes.
            time.sleep(0.15)
            return {"cross_process_counter": before + 1}, before

        before = store.transact_registry(operation)
        results.put(("ok", before))
    except Exception as exc:  # pragma: no cover - surfaced to parent assertion
        results.put(("error", f"{type(exc).__name__}: {exc}"))


def test_registry_transaction_serializes_two_independent_processes(tmp_path):
    if os.name != "posix" or "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("cross-process DurableStore proof requires POSIX fork/flock")

    data_dir = tmp_path / "shared-sara-store"
    store = DurableStore(data_dir)
    store.patch_registry({"cross_process_counter": 0})

    ctx = multiprocessing.get_context("fork")
    ready = ctx.Queue()
    results = ctx.Queue()
    start = ctx.Event()

    workers = [
        ctx.Process(
            target=_increment_registry_worker,
            args=(str(data_dir), ready, start, results),
        )
        for _ in range(2)
    ]
    for worker in workers:
        worker.start()

    assert ready.get(timeout=5)[0] == "ready"
    assert ready.get(timeout=5)[0] == "ready"
    start.set()

    for worker in workers:
        worker.join(timeout=10)
        assert worker.exitcode == 0

    outcomes = [results.get(timeout=5), results.get(timeout=5)]
    assert all(outcome[0] == "ok" for outcome in outcomes), outcomes
    assert {outcome[1] for outcome in outcomes} == {0, 1}

    final = DurableStore(data_dir).get_registry()
    assert final["cross_process_counter"] == 2
