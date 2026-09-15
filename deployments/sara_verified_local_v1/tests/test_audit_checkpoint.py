from __future__ import annotations

import copy
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.audit_checkpoint import (
    SaraAuditCheckpointError,
    SaraAuditCheckpointManager,
)
from worldshepherd_sara.audit_checkpoint_verify import (
    SaraAuditCheckpointVerificationError,
    verify_checkpoint_bundle,
    verify_checkpoint_chain,
)
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


def _manager(tmp_path):
    store = DurableStore(tmp_path / "sara")
    key = Ed25519PrivateKey.generate()
    manager = SaraAuditCheckpointManager(
        store,
        private_key=key,
        key_id="SARA-AUDIT-TEST-V1",
    )
    return store, manager


def _append(store: DurableStore, sequence: int) -> None:
    store.append_audit(
        AuditRecord(
            timestamp=f"2026-09-14T00:{sequence:02d}:00+00:00",
            event="audit_checkpoint_test",
            actor="admin_operator",
            payload={"sequence": sequence, "value": f"VALUE-{sequence}"},
        )
    )


def _lines(store: DurableStore) -> list[dict]:
    return [
        json.loads(line)
        for line in store.audit_path.read_text(encoding="utf-8").splitlines()
    ]


def _rewrite(store: DurableStore, rows: list[dict]) -> None:
    store.audit_path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    store.audit_path.chmod(0o600)


def test_checkpoint_verifies_exact_audit_and_survives_restart(tmp_path):
    store, manager = _manager(tmp_path)
    for sequence in range(1, 4):
        _append(store, sequence)
    bundle = manager.create_checkpoint()

    assert verify_checkpoint_bundle(bundle, manager.fingerprint_sha256)["record_count"] == 3
    status = manager.verify_current()
    assert status["status"] == "PASS"
    assert status["checkpointed_records"] == 3
    assert status["uncheckpointed_records"] == 0

    restarted = SaraAuditCheckpointManager(
        store,
        private_key=manager.private_key,
        key_id=manager.key_id,
    )
    assert restarted.verify_current()["latest_checkpoint_sha256"] == bundle["checkpoint_sha256"]


def test_newer_records_are_visible_as_uncheckpointed_tail(tmp_path):
    store, manager = _manager(tmp_path)
    _append(store, 1)
    manager.create_checkpoint()
    _append(store, 2)
    _append(store, 3)

    status = manager.verify_current()
    assert status["status"] == "PASS_WITH_UNCHECKPOINTED_TAIL"
    assert status["checkpointed_records"] == 1
    assert status["current_records"] == 3
    assert status["uncheckpointed_records"] == 2


def test_historical_mutation_is_detected(tmp_path):
    store, manager = _manager(tmp_path)
    for sequence in range(1, 4):
        _append(store, sequence)
    manager.create_checkpoint()
    rows = _lines(store)
    rows[0]["payload"]["value"] = "MUTATED"
    _rewrite(store, rows)

    with pytest.raises(SaraAuditCheckpointError, match="prefix integrity mismatch"):
        manager.verify_current()


def test_historical_reordering_is_detected(tmp_path):
    store, manager = _manager(tmp_path)
    for sequence in range(1, 4):
        _append(store, sequence)
    manager.create_checkpoint()
    rows = _lines(store)
    rows[0], rows[1] = rows[1], rows[0]
    _rewrite(store, rows)

    with pytest.raises(SaraAuditCheckpointError, match="prefix integrity mismatch"):
        manager.verify_current()


def test_checkpointed_prefix_truncation_is_detected(tmp_path):
    store, manager = _manager(tmp_path)
    for sequence in range(1, 4):
        _append(store, sequence)
    manager.create_checkpoint()
    rows = _lines(store)
    _rewrite(store, rows[:2])

    with pytest.raises(SaraAuditCheckpointError, match="truncation detected"):
        manager.verify_current()


def test_signed_bundle_tampering_is_rejected(tmp_path):
    store, manager = _manager(tmp_path)
    _append(store, 1)
    bundle = manager.create_checkpoint()

    mutations = []
    changed_count = copy.deepcopy(bundle)
    changed_count["manifest"]["record_count"] = 2
    mutations.append(changed_count)
    changed_head = copy.deepcopy(bundle)
    changed_head["manifest"]["audit_chain_head_sha256"] = "0" * 64
    mutations.append(changed_head)
    bad_signature = copy.deepcopy(bundle)
    bad_signature["signature_b64url"] = "A" * 86
    mutations.append(bad_signature)

    for mutated in mutations:
        with pytest.raises(SaraAuditCheckpointVerificationError):
            verify_checkpoint_bundle(mutated, manager.fingerprint_sha256)


def test_checkpoint_chain_is_contiguous_and_monotonic(tmp_path):
    store, manager = _manager(tmp_path)
    _append(store, 1)
    first = manager.create_checkpoint()
    _append(store, 2)
    second = manager.create_checkpoint()

    summary = verify_checkpoint_chain(
        [first, second], manager.fingerprint_sha256
    )
    assert summary["status"] == "PASS"
    assert summary["checkpoint_count"] == 2
    assert second["manifest"]["previous_checkpoint_sha256"] == first["checkpoint_sha256"]

    with pytest.raises(SaraAuditCheckpointVerificationError):
        verify_checkpoint_chain([second, first], manager.fingerprint_sha256)


def test_external_latest_digest_pin_detects_local_checkpoint_rollback(tmp_path):
    store, manager = _manager(tmp_path)
    _append(store, 1)
    first = manager.create_checkpoint()
    _append(store, 2)
    second = manager.create_checkpoint()

    # Simulate privileged rollback of only the local checkpoint ledger to the
    # first valid signed checkpoint.  Without an external latest-digest pin,
    # the remaining first checkpoint is cryptographically valid and the audit
    # simply appears to have an uncheckpointed tail.
    manager.ledger_path.write_text(
        json.dumps(first, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    manager.ledger_path.chmod(0o600)
    assert manager.verify_current()["status"] == "PASS_WITH_UNCHECKPOINTED_TAIL"

    with pytest.raises(
        SaraAuditCheckpointVerificationError,
        match="rollback/latest-digest mismatch",
    ):
        manager.verify_current(
            expected_latest_checkpoint_sha256=second["checkpoint_sha256"]
        )


def test_key_fingerprint_swap_is_rejected(tmp_path):
    store, manager = _manager(tmp_path)
    _append(store, 1)
    bundle = manager.create_checkpoint()
    other = Ed25519PrivateKey.generate()
    other_manager = SaraAuditCheckpointManager(
        store,
        private_key=other,
        key_id="SARA-AUDIT-OTHER-V1",
    )
    with pytest.raises(SaraAuditCheckpointVerificationError, match="not trusted"):
        verify_checkpoint_bundle(bundle, other_manager.fingerprint_sha256)
