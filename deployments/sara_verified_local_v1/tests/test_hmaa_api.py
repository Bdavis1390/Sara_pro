from __future__ import annotations

from datetime import datetime, timezone

from worldshepherd_sara.hmaa import (
    HMAAEvent,
    evaluate_event_assurance,
    seal_event,
)


BASE = datetime(2026, 9, 4, 22, 0, tzinfo=timezone.utc)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sealed_event() -> HMAAEvent:
    return seal_event(
        HMAAEvent(
            event_id="API-E1",
            mission_id="SIM-API-001",
            source_system="synthetic-sil",
            event_type="OBSERVATION",
            source_timestamp=BASE,
            ingest_timestamp=BASE,
            payload={"status": "nominal"},
        )
    )


def test_hmaa_read_endpoints_require_admin(client, tokens):
    relay, admin = tokens

    assert client.get("/v1/hmaa/status").status_code == 401
    assert client.get("/v1/hmaa/status", headers=auth(relay)).status_code == 403
    assert client.get("/v1/hmaa/evidence", headers=auth(relay)).status_code == 403
    assert client.get("/v1/hmaa/status", headers=auth(admin)).status_code == 200


def test_hmaa_status_and_evidence_are_read_only_views(client, tokens):
    _, admin = tokens
    event = _sealed_event()
    client.app.state.hmaa_store.append(event, evaluate_event_assurance())

    status = client.get("/v1/hmaa/status", headers=auth(admin))
    assert status.status_code == 200
    assert status.json()["ok"] is True
    assert status.json()["status"]["latest_event_hash"] == event.event_hash
    assert status.json()["status"]["latest_mission_id"] == "SIM-API-001"

    evidence = client.get(
        "/v1/hmaa/evidence?mission_id=SIM-API-001&limit=5",
        headers=auth(admin),
    )
    assert evidence.status_code == 200
    records = evidence.json()["records"]
    assert len(records) == 1
    assert records[0]["event"]["event_id"] == "API-E1"
    assert records[0]["assessment"]["disposition"] == "ALLOW"


def test_hmaa_evidence_filter_does_not_return_other_missions(client, tokens):
    _, admin = tokens
    event = _sealed_event()
    client.app.state.hmaa_store.append(event, evaluate_event_assurance())

    response = client.get(
        "/v1/hmaa/evidence?mission_id=SIM-NOT-PRESENT",
        headers=auth(admin),
    )
    assert response.status_code == 200
    assert response.json()["records"] == []
