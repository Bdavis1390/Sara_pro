from __future__ import annotations

import worldshepherd_sara.qcrypto_audit_api as qcrypto_api
from worldshepherd_sara.qcrypto_audit_adapter import QCRYPTO_AUDIT_SCHEMA
from worldshepherd_sara.qcrypto_echo_forwarder import (
    QCryptoEchoConflict,
    QCryptoEchoSyncResult,
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def projection(asset_id: str = "asset-sync-001") -> dict[str, object]:
    return {
        "schema": QCRYPTO_AUDIT_SCHEMA,
        "asset_id": asset_id,
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
        "correlation_id": "QCRYPTO-SYNC-001",
    }


def submit(client, admin: str, asset_id: str = "asset-sync-001") -> str:
    response = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(asset_id),
    )
    assert response.status_code == 202
    return response.json()["decision_digest"]


class FakeForwarder:
    def __init__(self) -> None:
        self.calls = 0

    def sync(self, records):
        self.calls += 1
        event_ids = tuple(record.payload["_outbox_event_id"] for record in records)
        replay = self.calls > 1
        return QCryptoEchoSyncResult(
            stored=0 if replay else 4,
            deduplicated=4 if replay else 0,
            event_ids=event_ids,
            reconciliation={
                "schema": "WS-ECHO-SARA-RECONCILIATION-V1",
                "scope": "PROVIDED_SARA_AUDIT_WINDOW",
                "counts": {
                    "MATCHED": 4,
                    "SARA_ONLY": 0,
                    "ECHO_ONLY": 0,
                    "PAYLOAD_MISMATCH": 0,
                },
                "entries": [],
            },
        )


class ConflictForwarder:
    def sync(self, records):
        raise QCryptoEchoConflict("simulated semantic conflict")


def test_echo_sync_requires_admin(client, tokens):
    relay, admin = tokens
    digest = submit(client, admin)
    response = client.post(
        f"/admin/qcrypto/audit/echo-sync?decision_digest={digest}",
        headers=auth(relay),
    )
    assert response.status_code == 403


def test_echo_sync_success_and_replay_are_bounded(client, tokens, monkeypatch):
    _, admin = tokens
    digest = submit(client, admin)
    fake = FakeForwarder()
    monkeypatch.setattr(qcrypto_api, "forwarder_from_environment", lambda: fake)

    first = client.post(
        f"/admin/qcrypto/audit/echo-sync?decision_digest={digest}",
        headers=auth(admin),
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["verification"]["verdict"] == "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    assert first_body["sync"]["stored_count"] == 4
    assert first_body["sync"]["deduplicated_count"] == 0
    assert first_body["sync"]["execution_authority"] is False
    assert first_body["sync"]["live_value_authorized"] is False

    second = client.post(
        f"/admin/qcrypto/audit/echo-sync?decision_digest={digest}",
        headers=auth(admin),
    )
    assert second.status_code == 200
    assert second.json()["sync"]["stored_count"] == 0
    assert second.json()["sync"]["deduplicated_count"] == 4
    assert fake.calls == 2

    verified = client.get(
        f"/admin/qcrypto/audit/verify?decision_digest={digest}",
        headers=auth(admin),
    )
    assert verified.status_code == 200
    verification = verified.json()["verification"]
    assert verification["complete"] is True
    assert verification["consistent"] is True
    assert verification["logical_event_count"] == 4

    audit = client.get("/v1/audit?limit=100", headers=auth(admin)).json()["records"]
    sync_records = [item for item in audit if item.get("event") == "qcrypto_echo_sync_completed"]
    assert len(sync_records) == 2
    assert all(item["payload"]["source_decision_digest"] == digest for item in sync_records)
    assert all("decision_digest" not in item["payload"] for item in sync_records)


def test_echo_sync_unconfigured_is_replayable_failure(client, tokens, monkeypatch):
    _, admin = tokens
    digest = submit(client, admin, "asset-sync-unconfigured")
    monkeypatch.setattr(qcrypto_api, "forwarder_from_environment", lambda: None)

    response = client.post(
        f"/admin/qcrypto/audit/echo-sync?decision_digest={digest}",
        headers=auth(admin),
    )
    assert response.status_code == 503

    audit = client.get("/v1/audit?limit=100", headers=auth(admin)).json()["records"]
    pending = [item for item in audit if item.get("event") == "qcrypto_echo_sync_pending"]
    assert len(pending) == 1
    assert pending[0]["payload"]["source_decision_digest"] == digest


def test_echo_sync_conflict_is_fail_closed(client, tokens, monkeypatch):
    _, admin = tokens
    digest = submit(client, admin, "asset-sync-conflict")
    monkeypatch.setattr(qcrypto_api, "forwarder_from_environment", lambda: ConflictForwarder())

    response = client.post(
        f"/admin/qcrypto/audit/echo-sync?decision_digest={digest}",
        headers=auth(admin),
    )
    assert response.status_code == 409

    audit = client.get("/v1/audit?limit=100", headers=auth(admin)).json()["records"]
    conflicts = [item for item in audit if item.get("event") == "qcrypto_echo_sync_conflict"]
    assert len(conflicts) == 1


def test_echo_sync_rejects_missing_decision_before_forwarding(client, tokens, monkeypatch):
    _, admin = tokens
    calls = {"count": 0}

    def should_not_configure():
        calls["count"] += 1
        return FakeForwarder()

    monkeypatch.setattr(qcrypto_api, "forwarder_from_environment", should_not_configure)
    missing = "sha256:" + "0" * 64
    response = client.post(
        f"/admin/qcrypto/audit/echo-sync?decision_digest={missing}",
        headers=auth(admin),
    )
    assert response.status_code == 409
    assert calls["count"] == 0
