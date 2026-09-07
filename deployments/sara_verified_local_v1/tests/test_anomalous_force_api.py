from __future__ import annotations


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payload() -> dict[str, object]:
    return {
        "campaign_id": "AFEM-API-001",
        "article_id": "ARTICLE-API-001",
        "preregistered": True,
        "input_power_w": 1000.0,
        "measured_force_n": 50e-6,
        "expanded_uncertainty_n": 2e-6,
        "known_momentum_force_bound_n": 3e-6,
        "af0_instrument_competence": "PASS",
        "af1_null_control_separation": "PASS",
        "af2_directionality": "PASS",
        "af3_confounder_closure": "PASS",
        "af4_scaling_law": "PASS",
        "af5_internal_replication": "PASS",
        "af6_instrument_independence": "OPEN",
        "af7_external_replication": "OPEN",
    }


def test_anomalous_force_endpoint_requires_admin(client, tokens):
    relay, _ = tokens
    response = client.post(
        "/admin/physics/anomalous-force/assess",
        headers=_auth(relay),
        json=_payload(),
    )
    assert response.status_code == 403


def test_anomalous_force_endpoint_is_conservative_and_audited(client, tokens):
    _, admin = tokens
    response = client.post(
        "/admin/physics/anomalous-force/assess",
        headers=_auth(admin),
        json=_payload(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["classification"] == "ANOMALY_CANDIDATE"
    assert body["photon_ratio_abs"] > 1.0
    assert body["reactionless_claim_allowed"] is False
    assert body["electrogravitic_claim_allowed"] is False
    assert body["new_physics_confirmed"] is False

    audit = client.get("/v1/audit?limit=100", headers=_auth(admin))
    assert audit.status_code == 200
    records = audit.json()["records"]
    matching = [
        record
        for record in records
        if record.get("event") == "physics_anomalous_force_assessed"
    ]
    assert matching
    payload = matching[-1]["payload"]
    assert payload["campaign_id"] == "AFEM-API-001"
    assert payload["classification"] == "ANOMALY_CANDIDATE"
    assert payload["new_physics_confirmed"] is False
