from __future__ import annotations

import pytest

from worldshepherd_sara.event_outbox import drain_event_outbox, outbox_status
from worldshepherd_sara.qcrypto_audit_adapter import (
    QCRYPTO_AUDIT_SCHEMA,
    QCryptoAuditAdapterError,
    qcrypto_outbox_events,
    queue_qcrypto_projection_patch,
)
from worldshepherd_sara.storage import DurableStore


def projection(**overrides):
    value = {
        "schema": QCRYPTO_AUDIT_SCHEMA,
        "asset_id": "asset-001",
        "echo_state": "ECHO_PROVENANCE_ACCEPTED",
        "prime_state": "PRIME_RECOMMENDS_PRIORITY_MIGRATION_PLAN",
        "sara_state": "SARA_PLAN_AUTHORIZED",
        "overwatch_state": "OVERWATCH_TRACK_AUTHORIZED_PLAN",
        "priority": "P0_MIGRATION_PRIORITY",
        "human_approval_required": True,
        "migration_executed": False,
        "execution_authority": False,
        "live_value_authorized": False,
        "federal_compliance_established": False,
        "ws_cae_conformance_established": False,
        "claim_boundary": "INTERNAL_PQC_CONTROL_PLANE_NOT_FEDERAL_COMPLIANCE",
        "correlation_id": "QCRYPTO-AUDIT-001",
    }
    value.update(overrides)
    return value


def test_projection_maps_to_four_native_sara_events():
    events = qcrypto_outbox_events(projection(), actor="SSPADAWANZZ")
    assert [item["event"] for item in events] == [
        "qcrypto_echo_state",
        "qcrypto_prime_state",
        "qcrypto_sara_state",
        "qcrypto_overwatch_state",
    ]
    assert [item["payload"]["stage"] for item in events] == [
        "ECHO",
        "PRIME",
        "SARA",
        "OVERWATCH",
    ]
    for item in events:
        payload = item["payload"]
        assert payload["migration_executed"] is False
        assert payload["execution_authority"] is False
        assert payload["live_value_authorized"] is False
        assert payload["federal_compliance_established"] is False
        assert payload["ws_cae_conformance_established"] is False
        assert payload["human_approval_required"] is True
        assert payload["correlation_id"] == "QCRYPTO-AUDIT-001"


def test_projection_persists_through_native_outbox_and_audit_log(tmp_path):
    store = DurableStore(tmp_path / "data")

    def operation(registry):
        patch, ids = queue_qcrypto_projection_patch(
            registry,
            projection(),
            actor="SSPADAWANZZ",
        )
        return patch, ids

    event_ids = store.transact_registry(operation)
    assert len(event_ids) == 4
    assert len(set(event_ids)) == 4
    assert outbox_status(store.get_registry()) == {
        "pending": 4,
        "delivered_retained": 0,
        "malformed": 0,
    }

    assert drain_event_outbox(store, limit=4) == 4
    assert outbox_status(store.get_registry())["pending"] == 0

    records = [
        record
        for record in store.read_audit(50)
        if str(record.get("event", "")).startswith("qcrypto_")
    ]
    assert len(records) == 4
    assert {record["payload"]["_outbox_event_id"] for record in records} == set(event_ids)
    assert all(record["payload"]["_delivery_semantics"] == "AT_LEAST_ONCE" for record in records)
    assert all(record["payload"]["migration_executed"] is False for record in records)
    assert all(record["payload"]["execution_authority"] is False for record in records)


def test_incomplete_evidence_states_are_recordable_without_policy_promotion():
    events = qcrypto_outbox_events(
        projection(
            echo_state="ECHO_REJECTED_INCOMPLETE_EVIDENCE",
            prime_state="PRIME_NOT_EVALUATED",
            sara_state="SARA_BLOCKED",
            overwatch_state="OVERWATCH_EVIDENCE_GAP",
            priority="INCOMPLETE_EVIDENCE",
        ),
        actor="SSPADAWANZZ",
    )
    assert events[0]["payload"]["state"] == "ECHO_REJECTED_INCOMPLETE_EVIDENCE"
    assert events[1]["payload"]["state"] == "PRIME_NOT_EVALUATED"
    assert events[2]["payload"]["state"] == "SARA_BLOCKED"
    assert events[3]["payload"]["state"] == "OVERWATCH_EVIDENCE_GAP"


@pytest.mark.parametrize(
    "field",
    [
        "migration_executed",
        "execution_authority",
        "live_value_authorized",
        "federal_compliance_established",
        "ws_cae_conformance_established",
    ],
)
def test_adapter_rejects_authority_or_compliance_escalation(field):
    with pytest.raises(QCryptoAuditAdapterError, match=field):
        qcrypto_outbox_events(projection(**{field: True}), actor="SSPADAWANZZ")


def test_adapter_requires_explicit_human_gate():
    with pytest.raises(QCryptoAuditAdapterError, match="human approval gate"):
        qcrypto_outbox_events(
            projection(human_approval_required=False),
            actor="SSPADAWANZZ",
        )


def test_adapter_requires_actor():
    with pytest.raises(QCryptoAuditAdapterError, match="actor"):
        qcrypto_outbox_events(projection(), actor="")
