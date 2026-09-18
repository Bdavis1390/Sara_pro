from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara import sda_ddil_release as ddil_module
from worldshepherd_sara.echo_event_store import EchoEventConflict, EchoEventStore
from worldshepherd_sara.mission_replay import replay_events
from worldshepherd_sara.sda_ddil_release import (
    SdaDdilAppendOutcome,
    SdaDdilConflict,
    SdaDdilJournalFull,
    SdaDdilReconciliationState,
    SdaDdilReleaseJournal,
    SdaDdilReleaseRecord,
    ddil_records_to_mission_events,
    reconcile_release_records,
    sda_ddil_release_audit_record,
)
from worldshepherd_sara.sda_release_authorization import SdaReleaseReceipt


NOW = datetime(2026, 9, 18, 1, 45, tzinfo=timezone.utc)


def receipt(
    authorization_id: str,
    *,
    payload_fill: str = "b",
    consumed_at: datetime = NOW,
) -> SdaReleaseReceipt:
    return SdaReleaseReceipt(
        authorization_id=authorization_id,
        payload_digest="sha256:" + payload_fill * 64,
        hypothesis_set_digest="sha256:" + "a" * 64,
        policy_revision_digest="sha256:" + "c" * 64,
        destination="INTERNAL:OVERWATCH",
        releasability_tags=["INTERNAL", "SYNTHETIC"],
        human_approval_id="HUMAN-APPROVAL-001",
        human_approver="identified-human-authority",
        signing_key_id="SDA-RELEASE-K1",
        signing_key_fingerprint_sha256="1" * 64,
        consumed_at=consumed_at,
    )


def record(
    authorization_id: str,
    *,
    node: str = "node-a",
    clock: int = 1,
    authority: int = 1,
    payload_fill: str = "b",
    consumed_at: datetime = NOW,
    recorded_at: datetime = NOW + timedelta(seconds=1),
) -> SdaDdilReleaseRecord:
    return SdaDdilReleaseRecord.from_receipt(
        receipt(
            authorization_id,
            payload_fill=payload_fill,
            consumed_at=consumed_at,
        ),
        origin_node=node,
        logical_clock=clock,
        authority=authority,
        recorded_at=recorded_at,
    )


def test_journal_persists_and_deduplicates_exact_receipt_across_restart(tmp_path):
    path = (tmp_path / "journal").resolve()
    item = record("SDA-RELEASE-AUTH-001")

    first = SdaDdilReleaseJournal(path).append(item)
    second = SdaDdilReleaseJournal(path).append(item)

    assert first == SdaDdilAppendOutcome.STORED
    assert second == SdaDdilAppendOutcome.DEDUPLICATED

    reopened = SdaDdilReleaseJournal(path)
    records = reopened.all_records()
    assert len(records) == 1
    assert records[0].receipt.authorization_id == "SDA-RELEASE-AUTH-001"
    assert records[0].receipt_digest == item.receipt_digest
    assert reopened.health()["ok"] is True


def test_same_authorization_id_with_different_receipt_semantics_is_visible_conflict(tmp_path):
    journal = SdaDdilReleaseJournal((tmp_path / "journal").resolve())
    original = record("SDA-RELEASE-AUTH-002", payload_fill="b")
    mutated = record("SDA-RELEASE-AUTH-002", payload_fill="d")

    journal.append(original)
    with pytest.raises(SdaDdilConflict, match="different receipt semantics"):
        journal.append(mutated)

    records = journal.all_records()
    assert len(records) == 1
    assert records[0].receipt.payload_digest == "sha256:" + "b" * 64
    health = journal.health()
    assert health["rejected_conflicts"] == 1
    assert health["ok"] is True


def test_journal_capacity_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(ddil_module, "MAX_DDIL_RELEASE_RECORDS", 1)
    journal = SdaDdilReleaseJournal((tmp_path / "journal").resolve())

    journal.append(record("SDA-RELEASE-AUTH-003"))
    with pytest.raises(SdaDdilJournalFull, match="capacity"):
        journal.append(record("SDA-RELEASE-AUTH-004"))


def test_health_detects_record_json_tamper(tmp_path):
    journal = SdaDdilReleaseJournal((tmp_path / "journal").resolve())
    item = record("SDA-RELEASE-AUTH-005")
    journal.append(item)

    connection = sqlite3.connect(journal.db_path)
    try:
        connection.execute(
            "UPDATE release_records SET receipt_digest=? WHERE authorization_id=?",
            ("sha256:" + "f" * 64, item.receipt.authorization_id),
        )
        connection.commit()
    finally:
        connection.close()

    health = journal.health()
    assert health["ok"] is False
    assert health["semantic_integrity_errors"] == 1


def test_rejoin_merges_identical_receipts_and_preserves_one_sided_records():
    shared_left = record(
        "SDA-RELEASE-AUTH-010",
        node="left-node",
        clock=4,
        authority=1,
    )
    shared_right = record(
        "SDA-RELEASE-AUTH-010",
        node="right-node",
        clock=5,
        authority=1,
        recorded_at=NOW + timedelta(seconds=2),
    )
    left_only = record("SDA-RELEASE-AUTH-011", node="left-node", clock=5)
    right_only = record("SDA-RELEASE-AUTH-012", node="right-node", clock=6)

    plan = reconcile_release_records(
        [shared_left, left_only],
        [shared_right, right_only],
    )

    by_id = {item.authorization_id: item for item in plan.entries}
    assert by_id["SDA-RELEASE-AUTH-010"].state == SdaDdilReconciliationState.MATCHED
    assert by_id["SDA-RELEASE-AUTH-011"].state == SdaDdilReconciliationState.LEFT_ONLY
    assert by_id["SDA-RELEASE-AUTH-012"].state == SdaDdilReconciliationState.RIGHT_ONLY
    assert plan.conflicts == []

    selected_shared = [
        item
        for item in plan.merged_records
        if item.receipt.authorization_id == "SDA-RELEASE-AUTH-010"
    ][0]
    assert selected_shared.origin_node == "right-node"
    assert selected_shared.logical_clock == 5


def test_rejoin_never_auto_resolves_different_receipts_for_same_authorization():
    left = record(
        "SDA-RELEASE-AUTH-020",
        node="left-node",
        clock=100,
        authority=100,
        payload_fill="b",
    )
    right = record(
        "SDA-RELEASE-AUTH-020",
        node="right-node",
        clock=1,
        authority=1,
        payload_fill="d",
    )

    plan = reconcile_release_records([left], [right])

    assert len(plan.conflicts) == 1
    conflict = plan.conflicts[0]
    assert conflict.state == SdaDdilReconciliationState.CONFLICT
    assert conflict.selected_receipt_digest is None
    assert plan.merged_records == []
    assert "automatic resolution is forbidden" in conflict.reason


def test_one_input_side_cannot_hide_internal_authorization_conflict():
    first = record("SDA-RELEASE-AUTH-021", payload_fill="b")
    second = record("SDA-RELEASE-AUTH-021", payload_fill="d")

    with pytest.raises(SdaDdilConflict, match="left input contains conflicting"):
        reconcile_release_records([first, second], [])


def test_echo_deduplicates_same_origin_retransmission_and_rejects_mutation(tmp_path):
    echo = EchoEventStore((tmp_path / "echo").resolve())
    original = record("SDA-RELEASE-AUTH-030", node="node-a", payload_fill="b")
    same = record("SDA-RELEASE-AUTH-030", node="node-a", payload_fill="b")
    mutated = record("SDA-RELEASE-AUTH-030", node="node-a", payload_fill="d")

    first = echo.ingest(sda_ddil_release_audit_record(original))
    retry = echo.ingest(sda_ddil_release_audit_record(same))

    assert first.outcome == "STORED"
    assert retry.outcome == "DEDUPLICATED"
    assert retry.record.delivery_count == 2

    with pytest.raises(EchoEventConflict, match="different semantic content"):
        echo.ingest(sda_ddil_release_audit_record(mutated))


def test_different_replica_nodes_have_distinct_echo_event_ids_for_same_receipt():
    left = record("SDA-RELEASE-AUTH-031", node="node-a")
    right = record("SDA-RELEASE-AUTH-031", node="node-b")

    assert left.receipt_digest == right.receipt_digest
    assert left.stable_echo_event_id() != right.stable_echo_event_id()


def test_release_receipts_bridge_into_deterministic_mission_replay_without_new_authority():
    later = record(
        "SDA-RELEASE-AUTH-041",
        node="node-b",
        consumed_at=NOW + timedelta(seconds=10),
        recorded_at=NOW + timedelta(seconds=11),
    )
    earlier = record(
        "SDA-RELEASE-AUTH-040",
        node="node-a",
        consumed_at=NOW,
        recorded_at=NOW + timedelta(seconds=1),
    )

    events = ddil_records_to_mission_events(
        [later, earlier],
        starting_sequence=20,
    )
    replayed = replay_events(list(events))

    assert [item.sequence for item in replayed] == [20, 21]
    assert [item.payload["authorization_id"] for item in replayed] == [
        "SDA-RELEASE-AUTH-040",
        "SDA-RELEASE-AUTH-041",
    ]
    assert replayed[0].t_seconds == pytest.approx(0.0)
    assert replayed[1].t_seconds == pytest.approx(10.0)
    assert all(item.event_type == "sda_analytic_release_receipt" for item in replayed)
    assert all(
        "does not authorize another release" in item.payload["claims_boundary"]
        for item in replayed
    )


def test_empty_replay_bridge_is_empty_and_sequence_must_be_positive():
    assert ddil_records_to_mission_events([]) == ()
    with pytest.raises(ValueError, match="at least 1"):
        ddil_records_to_mission_events(
            [record("SDA-RELEASE-AUTH-050")],
            starting_sequence=0,
        )
