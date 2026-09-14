from __future__ import annotations

from copy import deepcopy

import pytest

from worldshepherd_sara.echo_checkpoint import EchoCheckpointManager
from worldshepherd_sara.echo_checkpoint_verify import verify_bundle
from worldshepherd_sara.echo_event_store import EchoEventConflict, EchoEventStore
from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.qcrypto_audit_adapter import QCRYPTO_AUDIT_SCHEMA


CLASSICAL_INTEGRITY_BOUNDARY = (
    "ECHO checkpoint verification uses the existing Ed25519 checkpoint path and "
    "therefore establishes local classical integrity only; it is not post-quantum "
    "assurance, external attestation, Federal compliance, or WS-CAE conformance."
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def projection(asset_id: str = "asset-echo-001") -> dict[str, object]:
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
        "correlation_id": "QCRYPTO-ECHO-001",
    }


def qcrypto_records(client, admin: str, decision_digest: str) -> list[AuditRecord]:
    response = client.get("/v1/audit?limit=100", headers=auth(admin))
    assert response.status_code == 200
    records = []
    for item in response.json()["records"]:
        payload = item.get("payload")
        if isinstance(payload, dict) and payload.get("decision_digest") == decision_digest:
            records.append(AuditRecord.model_validate(item))
    return records


def test_qcrypto_sara_audit_flows_into_echo_and_signed_checkpoint(
    client,
    tokens,
    tmp_path,
    echo_checkpoint_key,
):
    _, admin = tokens
    submitted = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(),
    )
    assert submitted.status_code == 202
    body = submitted.json()
    assert body["provenance_delivery"] == "DELIVERED"
    digest = body["decision_digest"]

    records = qcrypto_records(client, admin, digest)
    assert len(records) == 4
    assert {record.event for record in records} == {
        "qcrypto_echo_state",
        "qcrypto_prime_state",
        "qcrypto_sara_state",
        "qcrypto_overwatch_state",
    }
    assert all(record.payload["migration_executed"] is False for record in records)
    assert all(record.payload["execution_authority"] is False for record in records)
    assert all(record.payload["live_value_authorized"] is False for record in records)

    echo_root = tmp_path / "qcrypto-echo"
    echo_root.mkdir(mode=0o700)
    echo = EchoEventStore(echo_root.resolve())
    outcomes = [echo.ingest(record) for record in records]
    assert [outcome.outcome for outcome in outcomes] == ["STORED"] * 4
    assert echo.health()["stored_events"] == 4

    replay = deepcopy(records[0])
    replay.timestamp = "2026-09-14T03:00:00+00:00"
    replay_outcome = echo.ingest(replay)
    assert replay_outcome.outcome == "DEDUPLICATED"
    assert replay_outcome.record.delivery_count == 2

    reconciliation = echo.reconcile(records)
    assert reconciliation["scope"] == "PROVIDED_SARA_AUDIT_WINDOW"
    assert reconciliation["counts"]["MATCHED"] == 4
    assert reconciliation["counts"]["SARA_ONLY"] == 0
    assert reconciliation["counts"]["DIGEST_MISMATCH"] == 0

    key, _key_path = echo_checkpoint_key
    checkpoints = EchoCheckpointManager(
        echo,
        private_key=key,
        key_id="ECHO-CHECKPOINT-QCRYPTO-TEST-V1",
    )
    checkpoint = checkpoints.create_checkpoint()
    verification = verify_bundle(checkpoint, checkpoints.fingerprint_sha256)
    assert verification["status"] == "PASS"
    assert verification["event_count"] == 4
    assert checkpoint["manifest"]["event_count"] == 4
    assert {
        event["event_id"] for event in checkpoint["manifest"]["events"]
    } == {
        record.payload["_outbox_event_id"] for record in records
    }
    assert "Ed25519" in checkpoint["manifest"]["signing_algorithm"]
    assert "not post-quantum" in CLASSICAL_INTEGRITY_BOUNDARY


def test_echo_rejects_semantic_substitution_of_qcrypto_event(
    client,
    tokens,
    tmp_path,
):
    _, admin = tokens
    submitted = client.post(
        "/admin/qcrypto/audit",
        headers=auth(admin),
        json=projection(asset_id="asset-echo-conflict-001"),
    )
    assert submitted.status_code == 202
    digest = submitted.json()["decision_digest"]
    records = qcrypto_records(client, admin, digest)
    assert len(records) == 4

    echo_root = tmp_path / "qcrypto-echo-conflict"
    echo_root.mkdir(mode=0o700)
    echo = EchoEventStore(echo_root.resolve())
    original = records[0]
    assert echo.ingest(original).outcome == "STORED"

    substituted = deepcopy(original)
    substituted.payload["priority"] = "P3_MONITOR"
    with pytest.raises(EchoEventConflict, match="different semantic content"):
        echo.ingest(substituted)

    retained = echo.get(original.payload["_outbox_event_id"])
    assert retained is not None
    assert retained.payload()["priority"] == "P0_MIGRATION_PRIORITY"
    assert echo.health()["rejected_conflicts"] == 1
