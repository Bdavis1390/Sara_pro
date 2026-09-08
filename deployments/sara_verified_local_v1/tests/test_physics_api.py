from __future__ import annotations


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def concept_record(project_id: str = "WORLDSHEPHERD-CORE") -> dict[str, object]:
    return {
        "record_id": "PHYS-API-0001",
        "artifact_id": "ART-API-0001",
        "project_id": project_id,
        "physics_domain": ["electromagnetics"],
        "physics_layer": "P2_ESTABLISHED_ENGINEERING",
        "model_scope": "bounded concept record for API verification",
        "assumptions": ["laboratory frame"],
        "validation_state": "concept",
        "claim_label": "Hypothesis",
        "claim_class": 1,
        "external_safe_statement": "Concept-stage model; no measured performance claimed.",
        "created_at": "2026-09-06T23:00:00Z",
        "updated_at": "2026-09-06T23:00:00Z",
    }


def perfect_score() -> dict[str, float]:
    return {
        "repeatability": 100,
        "control_quality": 100,
        "signal_quality": 100,
        "background_characterization": 100,
        "instrument_independence": 100,
        "model_consistency": 100,
        "falsification_strength": 100,
    }


def test_physics_endpoints_require_admin(client, tokens):
    relay, _ = tokens
    for method, path, body in [
        ("get", "/v1/physics/status", None),
        ("get", "/v1/physics/records", None),
        ("post", "/admin/physics/records", concept_record()),
        ("post", "/admin/physics/lint", {"text": "concept-stage quantum model"}),
        (
            "post",
            "/admin/physics/evaluate",
            {"record": concept_record(), "score": perfect_score()},
        ),
    ]:
        response = client.request(method, path, headers=auth(relay), json=body)
        assert response.status_code == 403


def test_physics_record_persists_and_filters(client, tokens):
    _, admin = tokens
    record = concept_record(project_id="WS-ALTI")
    response = client.post(
        "/admin/physics/records",
        headers=auth(admin),
        json=record,
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True

    status = client.get("/v1/physics/status", headers=auth(admin))
    assert status.status_code == 200
    assert status.json()["ok"] is True
    assert status.json()["status"]["records"] == 1

    records = client.get(
        "/v1/physics/records?project_id=WS-ALTI&limit=10",
        headers=auth(admin),
    )
    assert records.status_code == 200
    values = records.json()["records"]
    assert len(values) == 1
    assert values[0]["project_id"] == "WS-ALTI"
    assert values[0]["validation_state"] == "concept"


def test_physics_claim_lint_blocks_reactionless_maturity_claim(client, tokens):
    _, admin = tokens
    response = client.post(
        "/admin/physics/lint",
        headers=auth(admin),
        json={
            "text": "This is proven reactionless propulsion.",
            "record": concept_record(),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["blocked"] is True
    rule_ids = {item["rule_id"] for item in body["findings"]}
    assert "PROP-01" in rule_ids
    assert "MATURITY-01" in rule_ids


def test_high_score_is_still_bounded_without_physical_evidence(client, tokens):
    _, admin = tokens
    response = client.post(
        "/admin/physics/evaluate",
        headers=auth(admin),
        json={"record": concept_record(), "score": perfect_score()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["weighted_score"] == 100
    assert body["new_physics_confirmed"] is False
    assert body["external_claim_allowed"] is False
    assert "NO_PHYSICAL_EXPERIMENT" in body["hard_gate_blocks"]


def test_physics_actions_are_audited(client, tokens):
    _, admin = tokens
    client.post(
        "/admin/physics/records",
        headers=auth(admin),
        json=concept_record(),
    )
    client.post(
        "/admin/physics/lint",
        headers=auth(admin),
        json={"text": "Concept-stage quantum model."},
    )
    client.post(
        "/admin/physics/evaluate",
        headers=auth(admin),
        json={"record": concept_record(), "score": perfect_score()},
    )
    audit = client.get("/v1/audit?limit=100", headers=auth(admin))
    events = {item.get("event") for item in audit.json()["records"]}
    assert "physics_record_appended" in events
    assert "physics_claim_linted" in events
    assert "physics_evidence_evaluated" in events
