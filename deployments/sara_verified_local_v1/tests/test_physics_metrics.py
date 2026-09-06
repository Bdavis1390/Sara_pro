from __future__ import annotations


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def concept_record(record_id: str) -> dict[str, object]:
    return {
        "record_id": record_id,
        "artifact_id": "ART-METRICS",
        "project_id": "WS-ALTI",
        "physics_domain": ["materials"],
        "physics_layer": "P2_ESTABLISHED_ENGINEERING",
        "model_scope": "bounded metrics test concept",
        "assumptions": ["concept fixture"],
        "validation_state": "concept",
        "claim_label": "Hypothesis",
        "claim_class": 1,
        "external_safe_statement": "Concept-stage record; no measured performance claimed.",
        "created_at": "2026-09-06T23:30:00Z",
        "updated_at": "2026-09-06T23:30:00Z",
    }


def test_physics_metrics_require_admin(client, tokens):
    relay, _ = tokens
    response = client.get("/v1/physics/metrics", headers=auth(relay))
    assert response.status_code == 403


def test_physics_metrics_expose_validation_counters(client, tokens):
    _, admin = tokens
    for record_id in ("PHYS-METRICS-1", "PHYS-METRICS-2"):
        response = client.post(
            "/admin/physics/records",
            headers=auth(admin),
            json=concept_record(record_id),
        )
        assert response.status_code == 200

    response = client.get("/v1/physics/metrics", headers=auth(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["records_considered"] == 2
    assert body["validation_states"]["concept"] == 2
    assert body["quality_gates"]["physical_records"] == 0
    assert body["quality_gates"]["missing_provenance"] == 0
    assert body["quality_gates"]["p4_records"] == 0
