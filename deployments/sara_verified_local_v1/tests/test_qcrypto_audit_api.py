from __future__ import annotations

import pytest

from worldshepherd_sara.event_outbox import (
    MAX_PENDING_OUTBOX_EVENTS,
    drain_event_outbox,
    outbox_status,
    queue_events_outbox_patch,
)
from worldshepherd_sara.qcrypto_audit_adapter import QCRYPTO_AUDIT_SCHEMA


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def projection(**overrides):
    value = {
        "schema": QCRYPTO_AUDIT_SCHEMA,
        "asset_id": "asset-api-001",
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
        "correlation_id": "QCRYPTO-API-001",
    }
    value.update(overrides)
    return value


def qcrypto_records(client, admin: str):
    response = client.get("/v1/audit?limit=100", headers=auth(admin))
    assert response.status_code == 200
    return [
        item
        for item in response.json()["records"]
        if str(item.get("event", "")).startswith("qcrypto_")
    ]


def test_admin_can_record_qcrypto_governance_evidence(client, tokens):
    _, admin = tokens
    response = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["asset_id"] == "asset-api-001"
    assert len(body["event_ids"]) == 4
    assert len(set(body["event_ids"])) == 4
    assert body["provenance_delivery"] == "DELIVERED"
    assert body["migration_executed"] is False
    assert body["execution_authority"] is False
    assert body["live_value_authorized"] is False
    assert body["federal_compliance_established"] is False
    assert body["ws_cae_conformance_established"] is False

    records = qcrypto_records(client, admin)
    assert [record["event"] for record in records] == [
        "qcrypto_echo_state",
        "qcrypto_prime_state",
        "qcrypto_sara_state",
        "qcrypto_overwatch_state",
    ]
    assert all(record["actor"] == "admin" for record in records)
    assert all(record["payload"]["asset_id"] == "asset-api-001" for record in records)
    assert all(record["payload"]["_delivery_semantics"] == "AT_LEAST_ONCE" for record in records)


def test_relay_role_cannot_write_qcrypto_governance_audit(client, tokens):
    relay, _ = tokens
    response = client.post(
        "/admin/qcrypto/audit",
        headers=auth(relay),
        json=projection(),
    )
    assert response.status_code == 403


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
def test_api_rejects_authority_or_compliance_escalation(client, tokens, field):
    _, admin = tokens
    response = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(**{field: True}),
    )
    assert response.status_code == 422
    assert field in response.json()["detail"]


def test_api_rejects_missing_human_gate(client, tokens):
    _, admin = tokens
    response = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(human_approval_required=False),
    )
    assert response.status_code == 422
    assert "human approval gate" in response.json()["detail"]


def test_api_rejects_extra_fields(client, tokens):
    _, admin = tokens
    response = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json={**projection(), "execute_now": True},
    )
    assert response.status_code == 422


def test_saturated_outbox_fails_closed_without_qcrypto_audit(client, tokens):
    _, admin = tokens
    store = client.app.state.store

    def saturate(registry):
        events = [
            {
                "event": "synthetic_pending",
                "actor": "test",
                "payload": {"index": index},
                "event_id": f"SARA-EVENT-QCRYPTO-SAT-{index:02d}",
            }
            for index in range(MAX_PENDING_OUTBOX_EVENTS)
        ]
        patch, _ids = queue_events_outbox_patch(registry, events)
        return patch, None

    store.transact_registry(saturate)
    assert outbox_status(store.get_registry())["pending"] == MAX_PENDING_OUTBOX_EVENTS

    response = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "QCRYPTO governance audit outbox is unavailable"
    assert qcrypto_records(client, admin) == []
    assert outbox_status(store.get_registry())["pending"] == MAX_PENDING_OUTBOX_EVENTS


def test_audit_delivery_failure_preserves_events_for_replay(client, tokens, monkeypatch):
    _, admin = tokens
    store = client.app.state.store
    original_append = store.append_audit

    def fail_append(_record):
        raise OSError("simulated QCRYPTO audit delivery failure")

    monkeypatch.setattr(store, "append_audit", fail_append)
    response = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(asset_id="asset-replay-001"),
    )
    assert response.status_code == 202
    assert response.json()["provenance_delivery"] == "PENDING_REPLAY"
    assert outbox_status(store.get_registry())["pending"] == 4

    monkeypatch.setattr(store, "append_audit", original_append)
    assert drain_event_outbox(store, limit=4) == 4
    assert outbox_status(store.get_registry())["pending"] == 0

    records = qcrypto_records(client, admin)
    assert len(records) == 4
    assert all(record["payload"]["asset_id"] == "asset-replay-001" for record in records)


def test_health_advertises_qcrypto_governance_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["endpoints"]["qcrypto_audit"] == "/admin/qcrypto/audit"
