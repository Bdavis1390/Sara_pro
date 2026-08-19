from __future__ import annotations


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_nvidia_status_requires_authentication(client):
    response = client.get("/v1/integrations/nvidia/status")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Authorization header"


def test_nvidia_status_accepts_relay_and_admin_without_mutating_audit(client, tokens):
    relay, admin = tokens
    audit_before = client.app.state.store.audit_path.read_bytes()

    for token in (relay, admin):
        response = client.get(
            "/v1/integrations/nvidia/status",
            headers=auth(token),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["integration_id"] == "WS-NV-01"
        assert body["status"] == "proof_contracts_ready_runtime_unverified"
        assert body["runtime_verified"] is False
        assert body["network_calls_enabled"] is False
        assert body["contract_digest"].startswith("sha256:")
        assert len(body["implemented_increments"]) == 8
        assert body["promotion_gate"]["auto_promotion_allowed"] is False
        assert body["promotion_gate"]["human_review_required"] is True
        assert set(body["proof_contracts"]) == {
            "omniverse_kit",
            "isaac_sim_ros2",
            "jetson_platform_services",
            "cuda_acceleration",
        }

    assert client.app.state.store.audit_path.read_bytes() == audit_before


def test_health_advertises_nvidia_status_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["endpoints"]["nvidia_status"] == (
        "/v1/integrations/nvidia/status"
    )
