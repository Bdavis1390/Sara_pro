from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.audit_checkpoint_guarded import (
    GuardedSaraAuditCheckpointManager,
)
from worldshepherd_sara.audit_checkpoint_anchor import export_external_anchor
from worldshepherd_sara.audit_checkpoint_offline_verify import (
    SaraAuditOfflineVerificationError,
    verify_offline_export,
)
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


def _append(store: DurableStore, sequence: int) -> None:
    store.append_audit(
        AuditRecord(
            timestamp=f"2026-09-14T18:{sequence:02d}:00+00:00",
            event="offline_verifier_restart_test",
            actor="admin_operator",
            payload={"sequence": sequence, "state": "expected"},
        )
    )


def _cross_restart_fixture(tmp_path):
    root = tmp_path / "sara"
    external = tmp_path / "external"
    external.mkdir()
    key = Ed25519PrivateKey.generate()

    first_store = DurableStore(root)
    first_manager = GuardedSaraAuditCheckpointManager(
        first_store,
        private_key=key,
        key_id="SARA-AUDIT-OFFLINE-VERIFY-V1",
    )
    _append(first_store, 1)
    _append(first_store, 2)
    first_checkpoint = first_manager.create_checkpoint()
    first_audit_bytes = first_store.audit_path.read_bytes()
    first_ledger_bytes = first_manager.ledger_path.read_bytes()

    # Simulate process restart: reconstruct store/manager from durable files.
    second_store = DurableStore(root)
    second_manager = GuardedSaraAuditCheckpointManager(
        second_store,
        private_key=key,
        key_id="SARA-AUDIT-OFFLINE-VERIFY-V1",
    )
    _append(second_store, 3)
    second_checkpoint = second_manager.create_checkpoint()
    anchor_path = (external / "anchor-latest.json").resolve()
    export_external_anchor(second_manager, anchor_path)

    return {
        "store": second_store,
        "manager": second_manager,
        "anchor": anchor_path,
        "first_checkpoint": first_checkpoint,
        "second_checkpoint": second_checkpoint,
        "first_audit_bytes": first_audit_bytes,
        "first_ledger_bytes": first_ledger_bytes,
    }


def _verify(fixture):
    return verify_offline_export(
        audit_path=fixture["store"].audit_path.resolve(),
        checkpoint_ledger_path=fixture["manager"].ledger_path.resolve(),
        external_anchor_path=fixture["anchor"],
    )


def test_offline_verifier_passes_cross_restart_chain_without_private_key_input(tmp_path):
    fixture = _cross_restart_fixture(tmp_path)
    result = _verify(fixture)
    assert result["status"] == "PASS"
    assert result["checkpoint_sequence"] == 2
    assert result["checkpointed_records"] == 3
    assert result["current_records"] == 3
    assert result["private_key_required"] is False
    assert result["running_sara_required"] is False
    assert result["checkpoint_sha256"] == fixture["second_checkpoint"]["checkpoint_sha256"]


def test_offline_verifier_reports_newer_uncheckpointed_tail(tmp_path):
    fixture = _cross_restart_fixture(tmp_path)
    _append(fixture["store"], 4)
    result = _verify(fixture)
    assert result["status"] == "PASS_WITH_UNCHECKPOINTED_TAIL"
    assert result["checkpointed_records"] == 3
    assert result["current_records"] == 4
    assert result["uncheckpointed_records"] == 1


def test_offline_verifier_detects_audit_rollback_after_restart(tmp_path):
    fixture = _cross_restart_fixture(tmp_path)
    fixture["store"].audit_path.write_bytes(fixture["first_audit_bytes"])
    fixture["store"].audit_path.chmod(0o600)
    with pytest.raises(
        SaraAuditOfflineVerificationError,
        match="rollback/truncation",
    ):
        _verify(fixture)


def test_offline_verifier_detects_coordinated_local_audit_and_ledger_rollback(tmp_path):
    fixture = _cross_restart_fixture(tmp_path)
    fixture["store"].audit_path.write_bytes(fixture["first_audit_bytes"])
    fixture["store"].audit_path.chmod(0o600)
    fixture["manager"].ledger_path.write_bytes(fixture["first_ledger_bytes"])
    fixture["manager"].ledger_path.chmod(0o600)

    with pytest.raises(
        SaraAuditOfflineVerificationError,
        match="rollback/latest-digest mismatch",
    ):
        _verify(fixture)


def test_offline_verifier_detects_checkpointed_content_mutation(tmp_path):
    fixture = _cross_restart_fixture(tmp_path)
    lines = fixture["store"].audit_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["payload"]["state"] = "tampered"
    lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    fixture["store"].audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    fixture["store"].audit_path.chmod(0o600)

    with pytest.raises(
        SaraAuditOfflineVerificationError,
        match="prefix integrity mismatch",
    ):
        _verify(fixture)


def test_offline_verifier_rejects_symlinked_evidence_inputs(tmp_path):
    fixture = _cross_restart_fixture(tmp_path)
    audit_link = tmp_path / "audit-link.jsonl"
    audit_link.symlink_to(fixture["store"].audit_path)
    with pytest.raises(
        SaraAuditOfflineVerificationError,
        match="regular file",
    ):
        verify_offline_export(
            audit_path=audit_link.absolute(),
            checkpoint_ledger_path=fixture["manager"].ledger_path.resolve(),
            external_anchor_path=fixture["anchor"],
        )
