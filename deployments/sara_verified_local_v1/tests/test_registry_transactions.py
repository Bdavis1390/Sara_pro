from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from worldshepherd_sara.storage import DurableStore


def test_transact_registry_prevents_concurrent_lost_updates(tmp_path):
    store = DurableStore(tmp_path / "data")
    store.patch_registry({"COUNTER": 0, "UNRELATED": {"preserve": True}})

    def increment(_: int) -> int:
        def operation(registry):
            next_value = int(registry.get("COUNTER", 0)) + 1
            return {"COUNTER": next_value}, next_value

        return store.transact_registry(operation)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(increment, range(64)))

    registry = store.get_registry()
    assert registry["COUNTER"] == 64
    assert registry["UNRELATED"] == {"preserve": True}
    assert sorted(results) == list(range(1, 65))


def test_transact_registry_exception_aborts_without_write(tmp_path):
    store = DurableStore(tmp_path / "data")
    store.patch_registry({"STATE": {"version": 1}})
    before = store.registry_path.read_bytes()

    def operation(registry):
        registry["STATE"] = {"version": 999}
        raise RuntimeError("simulated transaction failure")

    with pytest.raises(RuntimeError, match="simulated transaction failure"):
        store.transact_registry(operation)

    assert store.registry_path.read_bytes() == before
    assert store.get_registry()["STATE"] == {"version": 1}


def test_transact_registry_none_patch_is_read_decision_only(tmp_path):
    store = DurableStore(tmp_path / "data")
    store.patch_registry({"STATE": "READY"})
    before = store.registry_path.read_bytes()

    result = store.transact_registry(
        lambda registry: (None, {"observed": registry["STATE"]})
    )

    assert result == {"observed": "READY"}
    assert store.registry_path.read_bytes() == before


def test_transact_registry_validates_combined_registry_before_commit(tmp_path):
    store = DurableStore(tmp_path / "data")
    store.patch_registry({"GOOD": "state"})
    before = store.registry_path.read_bytes()

    def invalid_patch(_registry):
        # Sets are not permitted by the JSON-resource validator.
        return {"BAD": {"not-json"}}, "should-not-return"

    with pytest.raises((TypeError, ValueError)):
        store.transact_registry(invalid_patch)

    assert store.registry_path.read_bytes() == before
    assert store.get_registry() == {"GOOD": "state"}
