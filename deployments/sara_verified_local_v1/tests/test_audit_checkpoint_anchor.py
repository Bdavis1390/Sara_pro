from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.audit_checkpoint import SaraAuditCheckpointManager
from worldshepherd_sara.audit_checkpoint_anchor import (
    SaraAuditExternalAnchorError,
    export_external_anchor,
    load_external_anchor,
    verify_with_external_anchor,
)
from worldshepherd_sara.audit_checkpoint_verify import (
    SaraAuditCheckpointVerificationError,
)
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.storage import DurableStore


def _setup(tmp_path):
    store = DurableStore(tmp_path / "sara")
    manager = SaraAuditCheckpointManager(
        store,
        private_key=Ed25519PrivateKey.generate(),
        key_id="SARA-AUDIT-ANCHOR-TEST-V1",
    )
    return store, manager


def _append(store: DurableStore, sequence: int) -> None:
    store.append_audit(
        AuditRecord(
            timestamp=f"2026-09-14T13:{sequence:02d}:00+00:00",
            event="audit_anchor_test",
            actor="admin_operator",
            payload={"sequence": sequence},
        )
    )


def test_external_anchor_round_trip_and_verification(tmp_path):
    store, manager = _setup(tmp_path)
    _append(store, 1)
    checkpoint = manager.create_checkpoint()
    external = tmp_path / "external"
    external.mkdir()
    anchor_path = (external / "anchor-1.json").resolve()

    anchor = export_external_anchor(manager, anchor_path)
    loaded = load_external_anchor(anchor_path)
    assert loaded == anchor
    assert anchor["checkpoint_sha256"] == checkpoint["checkpoint_sha256"]
    verified = verify_with_external_anchor(manager, anchor_path)
    assert verified["status"] == "PASS"
    assert verified["checkpoint_sequence"] == 1
    assert verified["checkpoint_record_count"] == 1


def test_export_refuses_anchor_inside_sara_data_boundary(tmp_path):
    store, manager = _setup(tmp_path)
    _append(store, 1)
    manager.create_checkpoint()
    with pytest.raises(SaraAuditExternalAnchorError, match="outside the SARA data directory"):
        export_external_anchor(manager, (store.root / "anchor.json").resolve())


def test_export_refuses_overwrite_of_existing_anchor(tmp_path):
    store, manager = _setup(tmp_path)
    _append(store, 1)
    manager.create_checkpoint()
    anchor_path = (tmp_path / "anchor.json").resolve()
    anchor_path.write_text("existing", encoding="utf-8")
    with pytest.raises(SaraAuditExternalAnchorError, match="already exists"):
        export_external_anchor(manager, anchor_path)


def test_external_anchor_detects_local_checkpoint_rollback(tmp_path):
    store, manager = _setup(tmp_path)
    _append(store, 1)
    first = manager.create_checkpoint()
    _append(store, 2)
    second = manager.create_checkpoint()
    anchor_path = (tmp_path / "anchor-latest.json").resolve()
    export_external_anchor(manager, anchor_path)

    manager.ledger_path.write_text(
        json.dumps(first, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    manager.ledger_path.chmod(0o600)

    with pytest.raises(
        SaraAuditCheckpointVerificationError,
        match="rollback/latest-digest mismatch",
    ):
        verify_with_external_anchor(manager, anchor_path)

    # The external anchor itself still names the second signed checkpoint.
    assert load_external_anchor(anchor_path)["checkpoint_sha256"] == second["checkpoint_sha256"]


def test_anchor_content_tampering_is_detected(tmp_path):
    store, manager = _setup(tmp_path)
    _append(store, 1)
    manager.create_checkpoint()
    anchor_path = (tmp_path / "anchor.json").resolve()
    anchor = export_external_anchor(manager, anchor_path)
    anchor["checkpoint_record_count"] = 999
    anchor_path.write_text(json.dumps(anchor) + "\n", encoding="utf-8")
    anchor_path.chmod(0o600)

    with pytest.raises(SaraAuditExternalAnchorError, match="content digest mismatch"):
        load_external_anchor(anchor_path)


def test_symlink_anchor_is_rejected(tmp_path):
    store, manager = _setup(tmp_path)
    _append(store, 1)
    manager.create_checkpoint()
    real_path = (tmp_path / "real-anchor.json").resolve()
    export_external_anchor(manager, real_path)
    link_path = tmp_path / "anchor-link.json"
    link_path.symlink_to(real_path)

    with pytest.raises(SaraAuditExternalAnchorError, match="regular file"):
        load_external_anchor(link_path.resolve(strict=False) if False else link_path.absolute())
