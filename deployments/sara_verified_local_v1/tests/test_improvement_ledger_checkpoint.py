import sqlite3

import pytest

from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.improvement_checkpoint import (
    ImprovementCheckpointError,
    build_ledger_checkpoint,
    build_ledger_checkpoint_event,
    ingest_ledger_checkpoint_into_echo,
    verify_signed_echo_membership,
    verify_stored_ledger_checkpoint,
)
from worldshepherd_sara.improvement_cycle import (
    ImprovementProposal,
    ImprovementRisk,
    ImprovementState,
    ImprovementTriggerKind,
    apply_assessment,
    assess_improvement,
    record_human_decision,
)
from worldshepherd_sara.improvement_ledger import ImprovementLedger, ImprovementLedgerError
from worldshepherd_sara.qualification import CapabilityStatus, ResultStatus


def proposal(improvement_id="WS-IR-2026-9101"):
    return ImprovementProposal(
        improvement_id=improvement_id,
        trigger_kind=ImprovementTriggerKind.NEW_EVIDENCE,
        title="ledger candidate",
        source_refs=["SRC-LEDGER"],
        affected_lanes=["ECHO", "WS-RI"],
        baseline_capability_status=[CapabilityStatus.NOT_CURRENTLY_CLAIMED],
        proposed_change="Evaluate a bounded candidate.",
        expected_benefit="Preserve lifecycle custody.",
        risk_level=ImprovementRisk.MODERATE,
        required_tests=["gate-a"],
        success_metrics=["gate-a passes"],
        generated_by="test",
        created_utc="2026-09-12T20:00:00Z",
    )


def append(ledger, item, reason="seed"):
    return ledger.append(
        item,
        actor="CRE1AWS",
        recorded_utc="2026-09-12T20:01:00Z",
        reason=reason,
    )


def test_ledger_records_valid_lifecycle_and_verifies_chain(tmp_path):
    ledger = ImprovementLedger(tmp_path.resolve())
    item = proposal()
    append(ledger, item)
    reviewable = apply_assessment(
        item,
        assess_improvement(item, {"gate-a": ResultStatus.PASS}),
    )
    append(ledger, reviewable, "qualification passed")
    promoted = record_human_decision(
        reviewable,
        accepted=True,
        reviewer="CRE1AWS",
        reviewed_utc="2026-09-12T20:02:00Z",
        rationale="Bounded qualification accepted.",
        qualification_refs=["WS-QE-2026-9101"],
        authorization_ref="PRIME-AUTH-9101",
    )
    append(ledger, promoted, "authorization recorded")
    assert ledger.verify_chain()
    assert ledger.latest(item.improvement_id).state == ImprovementState.PROMOTED.value


def test_replay_deduplicates_and_same_state_rewrite_fails(tmp_path):
    ledger = ImprovementLedger(tmp_path.resolve())
    item = proposal()
    first = append(ledger, item)
    second = append(ledger, item)
    assert second.outcome == "DEDUPLICATED"
    assert first.record.record_digest == second.record.record_digest
    changed = item.model_copy(update={"expected_benefit": "changed content"})
    with pytest.raises(ImprovementLedgerError):
        append(ledger, changed)


def test_tampering_breaks_ledger_verification(tmp_path):
    ledger = ImprovementLedger(tmp_path.resolve())
    append(ledger, proposal())
    connection = sqlite3.connect(ledger.db_path)
    try:
        connection.execute("UPDATE wsri_records SET reason='tampered' WHERE sequence=1")
        connection.commit()
    finally:
        connection.close()
    assert not ledger.verify_chain()


def test_checkpoint_requires_nonempty_valid_ledger(tmp_path):
    ledger = ImprovementLedger(tmp_path.resolve())
    with pytest.raises(ImprovementCheckpointError):
        build_ledger_checkpoint(ledger, created_utc="2026-09-12T20:03:00Z")
    append(ledger, proposal())
    checkpoint = build_ledger_checkpoint(
        ledger, created_utc="2026-09-12T20:03:00Z"
    )
    assert checkpoint.record_count == 1
    assert checkpoint.state_counts == {"PROPOSED": 1}


def test_checkpoint_event_is_not_a_feedback_signal(tmp_path):
    ledger = ImprovementLedger(tmp_path.resolve())
    append(ledger, proposal())
    record, checkpoint = build_ledger_checkpoint_event(
        ledger,
        event_id="SARA-EVENT-wsri-ledger-anchor-1",
        actor="SARA",
        timestamp="2026-09-12T20:04:00+00:00",
    )
    assert "_ws_improvement_signal" not in record.payload
    assert (
        record.payload["_ws_ri_ledger_checkpoint"]["checkpoint_digest"]
        == checkpoint.checkpoint_digest
    )


def test_echo_ingest_and_signed_membership_verification(
    tmp_path, echo_checkpoint_key
):
    key, _path = echo_checkpoint_key
    ledger_root = tmp_path / "ledger"
    ledger = ImprovementLedger(ledger_root.resolve())
    append(ledger, proposal())
    echo_root = tmp_path / "echo"
    echo_root.mkdir(mode=0o700)
    store = EchoEventStore(echo_root.resolve())
    result, checkpoint = ingest_ledger_checkpoint_into_echo(
        store,
        ledger,
        event_id="SARA-EVENT-wsri-ledger-anchor-2",
        actor="SARA",
        timestamp="2026-09-12T20:05:00+00:00",
    )
    assert verify_stored_ledger_checkpoint(result.record, checkpoint)
    manager = EchoCheckpointManager(
        store,
        private_key=key,
        key_id="WS-RI-CHECKPOINT-TEST-V1",
    )
    bundle = manager.create_checkpoint()
    summary = verify_signed_echo_membership(
        bundle,
        trusted_fingerprint_sha256=manager.fingerprint_sha256,
        event_id=result.record.event_id,
        semantic_digest=result.record.semantic_sha256,
    )
    assert summary["status"] == "PASS"
    assert summary["echo_checkpoint_id"] == bundle["manifest"]["checkpoint_id"]
