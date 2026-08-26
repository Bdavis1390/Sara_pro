from __future__ import annotations

import pytest

from worldshepherd_sara.config_custody import ConfigurationCustodyLedger, create_snapshot


def test_configuration_custody_chains_snapshots_and_verifies_lineage():
    ledger = ConfigurationCustodyLedger()
    first = create_snapshot(snapshot_id="CFG-001", payload={"mode":"safe"}, created_utc="2026-08-26T00:00:00Z", actor="operator", reason="initial")
    ledger.append(first)
    second = create_snapshot(snapshot_id="CFG-002", payload={"mode":"mission"}, created_utc="2026-08-26T00:10:00Z", actor="operator", reason="approved mission config", parent_digest=first.digest)
    ledger.append(second)
    assert ledger.head() == second
    assert ledger.verify_chain() is True


def test_configuration_rollback_is_new_append_only_snapshot_not_history_rewrite():
    ledger = ConfigurationCustodyLedger()
    first = create_snapshot(snapshot_id="CFG-001", payload={"threshold":1}, created_utc="2026-08-26T00:00:00Z", actor="operator", reason="initial")
    ledger.append(first)
    second = create_snapshot(snapshot_id="CFG-002", payload={"threshold":2}, created_utc="2026-08-26T00:10:00Z", actor="operator", reason="change", parent_digest=first.digest)
    ledger.append(second)
    rollback = ledger.rollback_snapshot(target_digest=first.digest, snapshot_id="CFG-003", created_utc="2026-08-26T00:20:00Z", actor="operator", reason="rollback")
    ledger.append(rollback)
    assert rollback.payload == first.payload
    assert rollback.parent_digest == second.digest
    assert len(ledger.records()) == 3
    assert ledger.verify_chain() is True


def test_configuration_custody_rejects_branching_from_stale_parent():
    ledger = ConfigurationCustodyLedger()
    first = create_snapshot(snapshot_id="CFG-001", payload={"x":1}, created_utc="2026-08-26T00:00:00Z", actor="operator", reason="initial")
    ledger.append(first)
    second = create_snapshot(snapshot_id="CFG-002", payload={"x":2}, created_utc="2026-08-26T00:10:00Z", actor="operator", reason="second", parent_digest=first.digest)
    ledger.append(second)
    stale = create_snapshot(snapshot_id="CFG-003", payload={"x":3}, created_utc="2026-08-26T00:20:00Z", actor="operator", reason="bad branch", parent_digest=first.digest)
    with pytest.raises(ValueError):
        ledger.append(stale)
