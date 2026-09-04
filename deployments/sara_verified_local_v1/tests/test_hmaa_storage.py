from __future__ import annotations

import stat
from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.hmaa import (
    HMAAEvent,
    evaluate_event_assurance,
    seal_event,
)
from worldshepherd_sara.hmaa_storage import HMAAEvidenceStore


BASE = datetime(2026, 9, 4, 21, 0, tzinfo=timezone.utc)


def _event(event_id: str, offset: int = 0) -> HMAAEvent:
    return HMAAEvent(
        event_id=event_id,
        mission_id="SIM-PERSIST-001",
        source_system="synthetic-sil",
        event_type="OBSERVATION",
        source_timestamp=BASE + timedelta(seconds=offset),
        ingest_timestamp=BASE + timedelta(seconds=offset),
        payload={"offset": offset},
    )


def test_append_only_store_preserves_chain_and_secure_permissions(tmp_path):
    store = HMAAEvidenceStore(tmp_path / "data")
    first = seal_event(_event("E1"))
    second = seal_event(_event("E2", 1), first.event_hash)

    store.append(first, evaluate_event_assurance())
    store.append(second, evaluate_event_assurance())

    records = store.read_recent(limit=10, mission_id="SIM-PERSIST-001")
    assert [record.event.event_id for record in records] == ["E1", "E2"]
    assert records[-1].event.previous_event_hash == first.event_hash
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.root.stat().st_mode) == 0o700


def test_store_rejects_unsealed_event(tmp_path):
    store = HMAAEvidenceStore(tmp_path / "data")
    with pytest.raises(ValueError, match="cryptographic seal"):
        store.append(_event("E1"), evaluate_event_assurance())


def test_store_rejects_non_contiguous_mission_chain(tmp_path):
    store = HMAAEvidenceStore(tmp_path / "data")
    first = seal_event(_event("E1"))
    store.append(first, evaluate_event_assurance())

    unrelated_head = "sha256:" + ("0" * 64)
    discontinuous = seal_event(_event("E2", 1), unrelated_head)
    with pytest.raises(ValueError, match="continue the persisted"):
        store.append(discontinuous, evaluate_event_assurance())


def test_status_does_not_expose_absolute_data_directory(tmp_path):
    store = HMAAEvidenceStore(tmp_path / "private-data")
    status = store.status()

    assert status["append_only_file"] == "hmaa_evidence.jsonl"
    assert str(tmp_path) not in repr(status)


def test_hmaa_evidence_symlink_swap_is_rejected(tmp_path):
    store = HMAAEvidenceStore(tmp_path / "data")
    first = seal_event(_event("E1"))
    store.append(first, evaluate_event_assurance())

    outside = tmp_path / "outside-evidence.jsonl"
    outside.write_text("{}\n", encoding="utf-8")
    store.path.unlink()
    store.path.symlink_to(outside)

    with pytest.raises(RuntimeError, match="HMAA evidence file"):
        store.read_recent(limit=1)

    assert outside.read_text(encoding="utf-8") == "{}\n"
