from __future__ import annotations

from worldshepherd_sara.event_outbox import (
    drain_event_outbox,
    outbox_status,
    queue_event_outbox_patch,
)
from worldshepherd_sara.qcrypto_audit_adapter import QCRYPTO_AUDIT_SCHEMA


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def projection():
    return {
        "schema": QCRYPTO_AUDIT_SCHEMA,
        "asset_id": "asset-queue-order-001",
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
        "correlation_id": "QCRYPTO-QUEUE-ORDER-001",
    }


def test_preexisting_pending_event_cannot_create_false_qcrypto_delivered_status(client, tokens):
    _, admin = tokens
    store = client.app.state.store

    def seed_older_event(registry):
        patch, event_id = queue_event_outbox_patch(
            registry,
            event="older_unrelated_event",
            actor="test",
            payload={"order": "before-qcrypto"},
            event_id="SARA-EVENT-OLDER-001",
        )
        return patch, event_id

    assert store.transact_registry(seed_older_event) == "SARA-EVENT-OLDER-001"
    assert outbox_status(store.get_registry())["pending"] == 1

    response = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(),
    )
    assert response.status_code == 202
    body = response.json()

    # The endpoint drains four oldest events: the unrelated event plus only
    # three of this decision's four events. Stable-ID verification must prevent
    # that count from being mistaken for complete QCRYPTO delivery.
    assert body["provenance_delivery"] == "PENDING_REPLAY"
    assert outbox_status(store.get_registry())["pending"] == 1

    assert drain_event_outbox(store, limit=1) == 1
    assert outbox_status(store.get_registry())["pending"] == 0

    verification = client.get(
        "/admin/qcrypto/audit/verify",
        headers=auth(admin),
        params={"decision_digest": body["decision_digest"], "limit": 100},
    )
    assert verification.status_code == 200
    result = verification.json()["verification"]
    assert result["verdict"] == "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    assert result["complete"] is True
    assert result["consistent"] is True
