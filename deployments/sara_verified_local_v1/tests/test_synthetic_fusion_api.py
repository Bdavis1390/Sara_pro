from __future__ import annotations

from worldshepherd_sara.synthetic_fusion_api import (
    MAX_SYNTHETIC_FUSION_OBSERVATIONS,
    SYNTHETIC_FUSION_SCOPE,
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def observation(index: int, *, observation_id: str | None = None) -> dict[str, object]:
    return {
        "observation_id": observation_id or f"OBS-{index:04d}",
        "sensor_id": f"SENSOR-{index % 4}",
        "t_seconds": float(index % 3),
        "x": float(index * 2),
        "y": float(index * 2),
        "confidence": 0.9,
    }


def request_body(count: int = 4) -> dict[str, object]:
    return {
        "scenario_id": "API-EVAL-001",
        "observations": [observation(index) for index in range(count)],
        "max_spatial_distance": 3.0,
        "max_time_delta_seconds": 5.0,
    }


def test_synthetic_fusion_is_admin_only(client, tokens):
    relay, _ = tokens
    response = client.post(
        "/v1/synthetic-fusion",
        headers=auth(relay),
        json=request_body(),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator role required"


def test_synthetic_fusion_preserves_lineage_and_records_audit(client, tokens):
    _, admin = tokens
    body = request_body(8)
    response = client.post(
        "/v1/synthetic-fusion",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == SYNTHETIC_FUSION_SCOPE
    assert payload["scenario_id"] == body["scenario_id"]
    assert payload["observation_count"] == 8
    assert payload["track_count"] >= 1
    assert payload["request_digest"].startswith("sha256:")
    assert payload["result_digest"].startswith("sha256:")
    assert payload["elapsed_ms"] >= 0
    source_ids = sorted(
        observation_id
        for track in payload["tracks"]
        for observation_id in track["source_observation_ids"]
    )
    assert source_ids == sorted(item["observation_id"] for item in body["observations"])

    audit = client.get("/v1/audit?limit=20", headers=auth(admin))
    assert audit.status_code == 200
    matching = [
        item
        for item in audit.json()["records"]
        if item.get("event") == "synthetic_fusion_completed"
    ]
    assert matching
    record = matching[-1]
    assert record["actor"] == "admin"
    assert record["payload"]["request_digest"] == payload["request_digest"]
    assert record["payload"]["result_digest"] == payload["result_digest"]
    assert record["payload"]["observation_count"] == 8


def test_duplicate_observation_ids_are_rejected_without_audit_mutation(client, tokens):
    _, admin = tokens
    body = request_body(2)
    body["observations"][1]["observation_id"] = body["observations"][0]["observation_id"]
    before = client.app.state.store.audit_path.read_bytes()
    response = client.post(
        "/v1/synthetic-fusion",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 422
    assert client.app.state.store.audit_path.read_bytes() == before


def test_observation_count_is_bounded_without_audit_mutation(client, tokens):
    _, admin = tokens
    before = client.app.state.store.audit_path.read_bytes()
    response = client.post(
        "/v1/synthetic-fusion",
        headers=auth(admin),
        json=request_body(MAX_SYNTHETIC_FUSION_OBSERVATIONS + 1),
    )
    assert response.status_code == 422
    assert client.app.state.store.audit_path.read_bytes() == before


def test_result_is_withheld_when_audit_persistence_fails(client, tokens, monkeypatch):
    _, admin = tokens
    durable_store = client.app.state.store
    original_append = durable_store.append_audit

    def fail_append(_record):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(durable_store, "append_audit", fail_append)
    try:
        response = client.post(
            "/v1/synthetic-fusion",
            headers=auth(admin),
            json=request_body(),
        )
    finally:
        monkeypatch.setattr(durable_store, "append_audit", original_append)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Synthetic fusion result withheld because audit persistence failed"
    )
