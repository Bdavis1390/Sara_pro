from fastapi.testclient import TestClient

from worldshepherd_sara.em_intelligence_service import app


client = TestClient(app)


def test_d5_status_is_read_only_pending() -> None:
    response = client.get("/v1/em/uc06/d5/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["sealed_result_ingested"] is False
    assert body["result_values_available"] is False
    assert body["overall_convergence"] == "NOT_ADJUDICATED"


def test_d5_contract_disallows_hardware_actions() -> None:
    response = client.get("/v1/em/uc06/d5/contract")
    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is True
    assert body["hardware_actions"] is False
    assert body["current_status"] == "PENDING"


def test_d5_has_no_mutation_route() -> None:
    response = client.post("/v1/em/uc06/d5/status", json={})
    assert response.status_code == 405
