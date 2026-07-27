from __future__ import annotations


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_and_ui(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    ui = client.get("/ui")
    assert ui.status_code == 200
    assert "Worldshepherd SARA" in ui.text


def test_authentication_required(client):
    response = client.get("/v1/audit")
    assert response.status_code == 401


def test_relay_token_can_record_local_relay(client, tokens):
    relay, _ = tokens
    response = client.post(
        "/v1/relay",
        headers=auth(relay),
        json={"target": "SSPADAWANZZ", "action": "status_check", "payload": {"scope": "local"}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "recorded_local_only"


def test_relay_token_cannot_read_admin_audit(client, tokens):
    relay, _ = tokens
    response = client.get("/v1/audit", headers=auth(relay))
    assert response.status_code == 403


def test_admin_registry_and_audit(client, tokens):
    _, admin = tokens
    patch = client.patch(
        "/admin/registry",
        headers=auth(admin),
        json={"values": {"SARA_CORE": {"role": "core", "status": "online"}}},
    )
    assert patch.status_code == 200
    assert patch.json()["registry"]["SARA_CORE"]["status"] == "online"

    audit = client.get("/v1/audit?limit=50", headers=auth(admin))
    assert audit.status_code == 200
    assert any(item["event"] == "registry_patched" for item in audit.json()["records"])


def test_admin_selftest(client, tokens):
    _, admin = tokens
    response = client.get("/admin/selftest", headers=auth(admin))
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["checks"]["external_dispatch_disabled"] is True
