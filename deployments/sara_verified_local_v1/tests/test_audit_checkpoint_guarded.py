from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.audit_checkpoint import SaraAuditCheckpointError
from worldshepherd_sara.audit_checkpoint_guarded import (
    GuardedSaraAuditCheckpointManager,
)
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


def _append(store: DurableStore, sequence: int) -> None:
    store.append_audit(
        AuditRecord(
            timestamp=f"2026-09-14T15:{sequence:02d}:00+00:00",
            event="guarded_checkpoint_test",
            actor="admin_operator",
            payload={"sequence": sequence, "value": f"VALUE-{sequence}"},
        )
    )


def _manager(tmp_path):
    store = DurableStore(tmp_path / "sara")
    manager = GuardedSaraAuditCheckpointManager(
        store,
        private_key=Ed25519PrivateKey.generate(),
        key_id="SARA-AUDIT-GUARDED-TEST-V1",
    )
    return store, manager


def test_guarded_checkpoint_extends_verified_prefix(tmp_path):
    store, manager = _manager(tmp_path)
    _append(store, 1)
    first = manager.create_checkpoint()
    _append(store, 2)
    second = manager.create_checkpoint()

    assert first["manifest"]["record_count"] == 1
    assert second["manifest"]["record_count"] == 2
    assert second["manifest"]["previous_checkpoint_sha256"] == first["checkpoint_sha256"]
    assert manager.verify_current()["status"] == "PASS"


def test_guarded_checkpoint_refuses_historical_mutation_plus_append(tmp_path):
    store, manager = _manager(tmp_path)
    _append(store, 1)
    _append(store, 2)
    first = manager.create_checkpoint()

    rows = [
        json.loads(line)
        for line in store.audit_path.read_text(encoding="utf-8").splitlines()
    ]
    rows[0]["payload"]["value"] = "MUTATED-BEFORE-EXTENSION"
    store.audit_path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    store.audit_path.chmod(0o600)
    _append(store, 3)

    with pytest.raises(SaraAuditCheckpointError, match="prefix integrity mismatch"):
        manager.create_checkpoint()

    ledger = manager._read_ledger()
    assert len(ledger) == 1
    assert ledger[0]["checkpoint_sha256"] == first["checkpoint_sha256"]


def test_guarded_checkpoint_refuses_reorder_plus_append(tmp_path):
    store, manager = _manager(tmp_path)
    _append(store, 1)
    _append(store, 2)
    manager.create_checkpoint()

    rows = [
        json.loads(line)
        for line in store.audit_path.read_text(encoding="utf-8").splitlines()
    ]
    rows[0], rows[1] = rows[1], rows[0]
    store.audit_path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    store.audit_path.chmod(0o600)
    _append(store, 3)

    with pytest.raises(SaraAuditCheckpointError, match="prefix integrity mismatch"):
        manager.create_checkpoint()
    assert len(manager._read_ledger()) == 1
