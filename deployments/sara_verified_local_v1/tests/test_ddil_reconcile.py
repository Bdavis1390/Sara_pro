from __future__ import annotations

from worldshepherd_sara.ddil_reconcile import (
    ReconciliationState,
    VersionedState,
    reconcile_key,
    reconcile_maps,
)


def test_newer_state_wins_after_partition_rejoin():
    old = VersionedState(key="task", value="hold", logical_clock=4, authority=1, source_node="a")
    new = VersionedState(key="task", value="resume", logical_clock=5, authority=1, source_node="b")
    result = reconcile_key([old, new])
    assert result.state == ReconciliationState.MERGED
    assert result.selected is not None
    assert result.selected.value == "resume"


def test_higher_authority_wins_at_equal_clock():
    low = VersionedState(key="route", value="east", logical_clock=7, authority=1, source_node="a")
    high = VersionedState(key="route", value="west", logical_clock=7, authority=2, source_node="b")
    result = reconcile_key([low, high])
    assert result.state == ReconciliationState.MERGED
    assert result.selected is not None
    assert result.selected.source_node == "b"


def test_equal_clock_equal_authority_divergence_is_not_silently_resolved():
    a = VersionedState(key="mode", value="search", logical_clock=9, authority=1, source_node="a")
    b = VersionedState(key="mode", value="return", logical_clock=9, authority=1, source_node="b")
    result = reconcile_key([a, b])
    assert result.state == ReconciliationState.CONFLICT
    assert result.selected is None
    assert "resolution required" in result.reason


def test_reconcile_maps_preserves_one_sided_keys_and_surfaces_conflicts():
    left = {
        "a": VersionedState(key="a", value=1, logical_clock=1, authority=1, source_node="left"),
        "shared": VersionedState(key="shared", value="x", logical_clock=2, authority=1, source_node="left"),
    }
    right = {
        "b": VersionedState(key="b", value=2, logical_clock=1, authority=1, source_node="right"),
        "shared": VersionedState(key="shared", value="y", logical_clock=2, authority=1, source_node="right"),
    }
    result = reconcile_maps(left, right)
    assert set(result) == {"a", "b", "shared"}
    assert result["shared"].state == ReconciliationState.CONFLICT
