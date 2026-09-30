from fastapi.testclient import TestClient

from worldshepherd_sara.em_intelligence_service import app


def test_em_service_health_is_read_only():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["read_only"] is True
        assert body["hardware_actions"] is False
        assert body["endpoints"]["uc06_evidence"] == "/v1/em/uc06/evidence"


def test_em_service_exposes_uc06_diagnostic_summary():
    with TestClient(app) as client:
        response = client.get("/v1/em/uc06/evidence")
        assert response.status_code == 200
        body = response.json()
        assert body["evidence_version"] == "uc06-p1-d4-20260930"
        assert body["overall_convergence"] == "NOT_ADJUDICATED"
        assert body["scientific_gate_change"] is False
        assert body["full_campaign_authorized"] is False


def test_em_service_has_no_mutation_route():
    with TestClient(app) as client:
        response = client.post("/v1/em/uc06/evidence", json={})
        assert response.status_code == 405
