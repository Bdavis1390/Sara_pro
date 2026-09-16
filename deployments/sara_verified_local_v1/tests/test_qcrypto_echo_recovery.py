from __future__ import annotations

import pytest

import worldshepherd_sara.qcrypto_audit_api as qcrypto_api
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.qcrypto_audit_adapter import QCRYPTO_AUDIT_SCHEMA
from worldshepherd_sara.qcrypto_echo_forwarder import (
    QCryptoEchoForwarder,
    QCryptoEchoForwarderError,
    QCryptoEchoSyncResult,
)


EVENTS = (
    "qcrypto_echo_state",
    "qcrypto_prime_state",
    "qcrypto_sara_state",
    "qcrypto_overwatch_state",
)


def source_records() -> list[AuditRecord]:
    return [
        AuditRecord(
            timestamp=f"2026-09-14T12:30:0{index}+00:00",
            event=event,
            actor="admin_operator",
            payload={
                "_outbox_event_id": f"SARA-EVENT-QCRYPTO-ACKLOSS-{index}",
                "_delivery_semantics": "AT_LEAST_ONCE",
                "decision_digest": "sha256:" + "a" * 64,
                "audit_instance_id": "QCRYPTO-AUDIT-" + "b" * 32,
                "execution_authority": False,
                "live_value_authorized": False,
            },
        )
        for index, event in enumerate(EVENTS)
    ]


def reconciliation(records_payload, *, echo_only: int = 1) -> dict[str, object]:
    submitted = [item["payload"]["_outbox_event_id"] for item in records_payload["records"]]
    return {
        "schema": "WS-ECHO-SARA-RECONCILIATION-V1",
        "scope": "PROVIDED_SARA_AUDIT_WINDOW",
        "counts": {
            "MATCHED": 4,
            "SARA_ONLY": 0,
            "ECHO_ONLY": echo_only,
            "PAYLOAD_MISMATCH": 0,
        },
        "entries": [
            *(
                {"event_id": event_id, "classification": "MATCHED"}
                for event_id in submitted
            ),
            *(
                {
                    "event_id": f"SARA-EVENT-RETAINED-ACKLOSS-{index}",
                    "classification": "ECHO_ONLY",
                }
                for index in range(echo_only)
            ),
        ],
    }


def test_forwarder_recovers_when_echo_stored_record_but_acknowledgement_was_lost():
    stored_ids: set[str] = set()
    ingest_calls = 0
    lose_ack_once = True

    def transport(base_url, path, payload, token):
        nonlocal ingest_calls, lose_ack_once
        assert base_url == "http://echo:9550"
        assert token == "e" * 40
        if path == "/v1/ingest":
            ingest_calls += 1
            event_id = payload["payload"]["_outbox_event_id"]
            if event_id in stored_ids:
                return 200, {"outcome": "DEDUPLICATED", "event_id": event_id}

            stored_ids.add(event_id)
            # The third record is durably accepted by ECHO, but the caller sees
            # an ambiguous 503 instead of the acknowledgement.
            if lose_ack_once and ingest_calls == 3:
                lose_ack_once = False
                return 503, {"detail": "simulated acknowledgement loss"}
            return 200, {"outcome": "STORED", "event_id": event_id}

        assert path == "/v1/reconcile"
        return 200, reconciliation(payload, echo_only=1)

    forwarder = QCryptoEchoForwarder(
        base_url="http://echo:9550",
        token="e" * 40,
        transport=transport,
    )
    records = source_records()

    with pytest.raises(QCryptoEchoForwarderError, match="HTTP 503"):
        forwarder.sync(records)
    assert stored_ids == {
        "SARA-EVENT-QCRYPTO-ACKLOSS-0",
        "SARA-EVENT-QCRYPTO-ACKLOSS-1",
        "SARA-EVENT-QCRYPTO-ACKLOSS-2",
    }

    recovered = forwarder.sync(records)
    assert recovered.stored == 1
    assert recovered.deduplicated == 3
    assert set(recovered.event_ids) == stored_ids
    assert recovered.reconciliation["counts"] == {
        "MATCHED": 4,
        "SARA_ONLY": 0,
        "ECHO_ONLY": 1,
        "PAYLOAD_MISMATCH": 0,
    }


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def projection() -> dict[str, object]:
    return {
        "schema": QCRYPTO_AUDIT_SCHEMA,
        "asset_id": "asset-api-recovery-001",
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
        "correlation_id": "QCRYPTO-API-RECOVERY-001",
    }


class RecoveringForwarder:
    def __init__(self) -> None:
        self.calls = 0

    def sync(self, records: list[AuditRecord]) -> QCryptoEchoSyncResult:
        self.calls += 1
        event_ids = tuple(record.payload["_outbox_event_id"] for record in records)
        if self.calls == 1:
            raise QCryptoEchoForwarderError("simulated ambiguous transport failure")
        return QCryptoEchoSyncResult(
            stored=1,
            deduplicated=3,
            event_ids=event_ids,
            reconciliation={
                "schema": "WS-ECHO-SARA-RECONCILIATION-V1",
                "scope": "PROVIDED_SARA_AUDIT_WINDOW",
                "counts": {
                    "MATCHED": 4,
                    "SARA_ONLY": 0,
                    "ECHO_ONLY": 2,
                    "PAYLOAD_MISMATCH": 0,
                },
                "entries": [
                    {
                        "event_id": event_id,
                        "classification": "MATCHED",
                    }
                    for event_id in event_ids
                ],
            },
        )


def test_api_pending_sync_can_retry_same_instance_without_contaminating_audit_chain(
    client,
    tokens,
    monkeypatch,
):
    _, admin = tokens
    submitted = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(),
    )
    assert submitted.status_code == 202
    body = submitted.json()
    digest = body["decision_digest"]
    instance = body["audit_instance_id"]
    sync_url = (
        "/admin/qcrypto/audit/echo-sync"
        f"?decision_digest={digest}&audit_instance_id={instance}"
    )

    recovering = RecoveringForwarder()
    monkeypatch.setattr(qcrypto_api, "forwarder_from_environment", lambda: recovering)

    failed = client.post(sync_url, headers=auth(admin))
    assert failed.status_code == 503
    assert recovering.calls == 1

    after_failure = client.get(
        "/admin/qcrypto/audit/verify",
        headers=auth(admin),
        params={"decision_digest": digest, "audit_instance_id": instance},
    )
    assert after_failure.status_code == 200
    failure_verification = after_failure.json()["verification"]
    assert failure_verification["verdict"] == "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    assert failure_verification["logical_event_count"] == 4

    retried = client.post(sync_url, headers=auth(admin))
    assert retried.status_code == 200
    result = retried.json()
    assert result["verification"]["verdict"] == "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    assert result["sync"]["stored_count"] == 1
    assert result["sync"]["deduplicated_count"] == 3
    assert result["sync"]["reconciliation"]["counts"] == {
        "MATCHED": 4,
        "SARA_ONLY": 0,
        "ECHO_ONLY": 2,
        "PAYLOAD_MISMATCH": 0,
    }
    assert recovering.calls == 2

    audit = client.get("/v1/audit?limit=100", headers=auth(admin)).json()["records"]
    pending = [item for item in audit if item.get("event") == "qcrypto_echo_sync_pending"]
    completed = [item for item in audit if item.get("event") == "qcrypto_echo_sync_completed"]
    assert len(pending) == 1
    assert len(completed) == 1
    for record in (*pending, *completed):
        assert record["payload"]["source_decision_digest"] == digest
        assert record["payload"]["source_audit_instance_id"] == instance
        assert "decision_digest" not in record["payload"]
        assert "audit_instance_id" not in record["payload"]

    after_retry = client.get(
        "/admin/qcrypto/audit/verify",
        headers=auth(admin),
        params={"decision_digest": digest, "audit_instance_id": instance},
    )
    assert after_retry.status_code == 200
    retry_verification = after_retry.json()["verification"]
    assert retry_verification["verdict"] == "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    assert retry_verification["logical_event_count"] == 4
