from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from worldshepherd_sara.registry_checkpoint import (
    REGISTRY_CHECKPOINT_META_KEY,
    RegistryCheckpointIntegrityError,
    checkpoint_metadata,
    make_genesis_record,
    make_transaction_records,
    plan_checkpoint_recovery,
    registry_state_root_sha256,
    verify_checkpoint_journal,
)
from worldshepherd_sara.storage import DurableStore


NOW = "2026-09-17T21:00:00Z"


def _with_genesis(registry: dict):
    genesis = make_genesis_record(registry, event_time=NOW)
    checkpointed = dict(registry)
    checkpointed[REGISTRY_CHECKPOINT_META_KEY] = checkpoint_metadata(
        generation=0,
        commit_hash=genesis["record_hash"],
        state_root_sha256=genesis["new_state_root_sha256"],
    )
    return checkpointed, genesis


def _journal_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_checkpoint_protocol_commits_generation_and_detects_registry_rollback():
    current, genesis = _with_genesis({"A": 1})
    journal = verify_checkpoint_journal([genesis])
    updated = dict(current)
    updated["A"] = 2
    prepare, commit, final_registry = make_transaction_records(
        current,
        updated,
        journal=journal,
        event_time=NOW,
        tx_id="TX-1",
    )

    healthy = plan_checkpoint_recovery(final_registry, [genesis, prepare, commit])
    assert healthy.action == "HEALTHY"
    assert final_registry[REGISTRY_CHECKPOINT_META_KEY]["generation"] == 1
    assert final_registry[REGISTRY_CHECKPOINT_META_KEY]["commit_hash"] == commit["record_hash"]

    with pytest.raises(RegistryCheckpointIntegrityError, match="rollback|tamper"):
        plan_checkpoint_recovery(current, [genesis, prepare, commit])


def test_pending_prepare_recovery_distinguishes_unapplied_from_applied_registry():
    current, genesis = _with_genesis({"A": 1})
    journal = verify_checkpoint_journal([genesis])
    updated = dict(current)
    updated["A"] = 2
    prepare, commit, final_registry = make_transaction_records(
        current,
        updated,
        journal=journal,
        event_time=NOW,
        tx_id="TX-RECOVERY",
    )

    unapplied = plan_checkpoint_recovery(
        current,
        [genesis, prepare],
        recovery_time="2026-09-17T21:01:00Z",
    )
    assert unapplied.action == "RECOVER_ABORT"
    assert unapplied.recovery_record["record_type"] == "ABORT"
    assert plan_checkpoint_recovery(
        current,
        [genesis, prepare, unapplied.recovery_record],
    ).action == "HEALTHY"

    applied = plan_checkpoint_recovery(final_registry, [genesis, prepare])
    assert applied.action == "RECOVER_COMMIT"
    assert applied.recovery_record == commit
    assert plan_checkpoint_recovery(
        final_registry,
        [genesis, prepare, applied.recovery_record],
    ).action == "HEALTHY"


def test_journal_record_tamper_breaks_hash_chain_verification():
    current, genesis = _with_genesis({"A": 1})
    journal = verify_checkpoint_journal([genesis])
    updated = dict(current)
    updated["A"] = 2
    prepare, commit, _final = make_transaction_records(
        current,
        updated,
        journal=journal,
        event_time=NOW,
        tx_id="TX-TAMPER",
    )
    commit["new_state_root_sha256"] = "f" * 64

    with pytest.raises(RegistryCheckpointIntegrityError, match="record hash mismatch"):
        verify_checkpoint_journal([genesis, prepare, commit])


def test_store_bootstraps_genesis_and_checkpoints_every_write(tmp_path):
    store = DurableStore(tmp_path)
    initial = store.get_registry()
    initial_status = store.checkpoint_status()

    assert initial[REGISTRY_CHECKPOINT_META_KEY]["generation"] == 0
    assert initial_status["generation"] == 0
    assert initial_status["external_witnessed"] is False
    assert store.registry_checkpoint_path.stat().st_mode & 0o077 == 0

    after_patch = store.patch_registry({"A": 1})
    patch_status = store.checkpoint_status()
    assert after_patch[REGISTRY_CHECKPOINT_META_KEY]["generation"] == 1
    assert patch_status["generation"] == 1
    assert patch_status["state_root_sha256"] == registry_state_root_sha256(after_patch)

    result = store.transact_registry(lambda registry: (None, registry["A"]))
    assert result == 1
    assert store.checkpoint_status()["generation"] == 1

    store.transact_registry(lambda registry: ({"B": 2}, "committed"))
    assert store.get_registry()["B"] == 2
    assert store.checkpoint_status()["generation"] == 2

    records = _journal_lines(store.registry_checkpoint_path)
    assert [record["record_type"] for record in records] == [
        "GENESIS",
        "PREPARE",
        "COMMIT",
        "PREPARE",
        "COMMIT",
    ]


def test_storage_owned_checkpoint_metadata_cannot_be_patched_or_returned_by_transaction(tmp_path):
    store = DurableStore(tmp_path)

    with pytest.raises(RegistryCheckpointIntegrityError, match="storage-owned"):
        store.patch_registry({REGISTRY_CHECKPOINT_META_KEY: {"generation": 999}})

    with pytest.raises(RegistryCheckpointIntegrityError, match="storage-owned"):
        store.transact_registry(
            lambda registry: ({REGISTRY_CHECKPOINT_META_KEY: {"generation": 999}}, None)
        )


def test_restoring_older_registry_while_newer_journal_remains_fails_closed(tmp_path):
    store = DurableStore(tmp_path)
    store.patch_registry({"SECURITY_STATE": "BEFORE"})
    old_registry_bytes = store.registry_path.read_bytes()
    store.patch_registry({"SECURITY_STATE": "AFTER"})
    assert store.get_registry()["SECURITY_STATE"] == "AFTER"

    store.registry_path.write_bytes(old_registry_bytes)
    os.chmod(store.registry_path, 0o600)

    with pytest.raises(RegistryCheckpointIntegrityError, match="rollback|tamper"):
        DurableStore(tmp_path)


def test_deleting_journal_from_checkpointed_registry_fails_closed(tmp_path):
    store = DurableStore(tmp_path)
    store.patch_registry({"A": 1})
    store.registry_checkpoint_path.unlink()

    with pytest.raises(RegistryCheckpointIntegrityError, match="journal is missing"):
        DurableStore(tmp_path)


def test_store_recovers_prepare_when_registry_replacement_never_happened(tmp_path):
    store = DurableStore(tmp_path)
    current = store.get_registry()
    records = _journal_lines(store.registry_checkpoint_path)
    journal = verify_checkpoint_journal(records)
    updated = dict(current)
    updated["RECOVERY"] = "UNAPPLIED"
    prepare, _commit, _final = make_transaction_records(
        current,
        updated,
        journal=journal,
        event_time=NOW,
        tx_id="TX-STORE-ABORT",
    )
    with store.registry_checkpoint_path.open("ab") as handle:
        handle.write(json.dumps(prepare, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
        handle.flush()
        os.fsync(handle.fileno())

    recovered = DurableStore(tmp_path)
    assert "RECOVERY" not in recovered.get_registry()
    tail = _journal_lines(recovered.registry_checkpoint_path)[-1]
    assert tail["record_type"] == "ABORT"
    assert tail["reason"] == "RECOVERED_PREPARE_NOT_APPLIED"


def test_store_recovers_commit_when_registry_replacement_preceded_final_journal_append(tmp_path):
    store = DurableStore(tmp_path)
    current = store.get_registry()
    records = _journal_lines(store.registry_checkpoint_path)
    journal = verify_checkpoint_journal(records)
    updated = dict(current)
    updated["RECOVERY"] = "APPLIED"
    prepare, commit, final_registry = make_transaction_records(
        current,
        updated,
        journal=journal,
        event_time=NOW,
        tx_id="TX-STORE-COMMIT",
    )
    with store.registry_checkpoint_path.open("ab") as handle:
        handle.write(json.dumps(prepare, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    store._atomic_write_json(store.registry_path, final_registry)

    recovered = DurableStore(tmp_path)
    assert recovered.get_registry()["RECOVERY"] == "APPLIED"
    tail = _journal_lines(recovered.registry_checkpoint_path)[-1]
    assert tail == commit
    assert recovered.checkpoint_status()["generation"] == commit["generation"]


def test_checkpoint_journal_symlink_is_rejected(tmp_path):
    store = DurableStore(tmp_path)
    store.registry_checkpoint_path.unlink()
    target = tmp_path / "attacker-journal"
    target.write_text("attacker\n", encoding="utf-8")
    store.registry_checkpoint_path.symlink_to(target)

    with pytest.raises((RuntimeError, RegistryCheckpointIntegrityError)):
        DurableStore(tmp_path)
