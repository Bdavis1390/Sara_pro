import pytest

from worldshepherd_sara.fusion_audit_bridge import (
    fusion_record_to_sara_event,
    fusion_records_to_sara_events,
)
from worldshepherd_sara.fusion_control import FusionAuditLedger


def ledger_with_two_records():
    ledger = FusionAuditLedger()
    ledger.append("fusion_sensor_sample", {"value": 1}, timestamp=1.0)
    ledger.append("fusion_gate_decision", {"accepted": True}, timestamp=2.0)
    return ledger


def test_bridge_preserves_hash_evidence_and_sara_shape():
    ledger = ledger_with_two_records()
    event = fusion_record_to_sara_event(ledger.records[0])

    assert event["ts"] == 1.0
    assert event["event"] == "fusion.fusion_sensor_sample"
    assert event["actor"] == "SARA_FUSION_SIM"
    assert event["payload"]["fusion_sequence"] == 0
    assert event["payload"]["fusion_previous_hash"] == "GENESIS"
    assert event["payload"]["fusion_record_hash"] == ledger.records[0].record_hash
    assert event["payload"]["fusion_payload"] == {"value": 1}


def test_bridge_cannot_impersonate_privileged_sara_actor():
    ledger = ledger_with_two_records()
    for actor in ("admin", "operator", "SSPADAWANZZ_ADMIN"):
        with pytest.raises(ValueError, match="cannot_impersonate"):
            fusion_record_to_sara_event(ledger.records[0], actor=actor)


def test_batch_bridge_requires_contiguous_sequence():
    ledger = ledger_with_two_records()
    events = fusion_records_to_sara_events(ledger.records)
    assert [event["payload"]["fusion_sequence"] for event in events] == [0, 1]

    ledger._records[1].sequence = 3
    with pytest.raises(ValueError, match="sequence_not_contiguous"):
        fusion_records_to_sara_events(ledger.records)
