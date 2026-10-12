from fastapi.testclient import TestClient

from worldshepherd_sara.em_intelligence_service import app


client = TestClient(app)


def test_maturity_endpoint_preserves_open_scientific_gates() -> None:
    response = client.get("/v1/em/uc06/maturity")
    assert response.status_code == 200
    body = response.json()
    assert body["d4_capability_attribution"] == "ESTABLISHED_DIAGNOSTIC"
    assert body["d5_interaction_sparse_analysis"] == "PENDING"
    assert body["recovery_a027_a054_completion"] == "NOT_INGESTED"
    assert body["medium_fine_convergence"] == "NOT_ADJUDICATED"
    assert body["physical_validation"] == "NOT_VALIDATED"
    assert body["hardware_action"] == "NOT_AUTHORIZED"
    assert body["software_ci_is_physics_validation"] is False
    assert body["read_only"] is True


def test_latent_contract_refuses_current_anomaly_authority() -> None:
    response = client.get("/v1/em/uc06/latent/contract")
    assert response.status_code == 200
    body = response.json()
    assert body["diagnostic_component_count_95pct"] == 2
    assert body["diagnostic_component_count_99pct"] == 3
    assert body["qualified_projection_basis_available"] is False
    assert body["held_out_validation_available"] is False
    assert body["hardware_repeatability_available"] is False
    assert body["anomaly_threshold_available"] is False
    assert body["anomaly_classification_authorized"] is False


def test_maturity_and_latent_endpoints_are_not_mutable() -> None:
    assert client.post("/v1/em/uc06/maturity", json={}).status_code == 405
    assert client.post("/v1/em/uc06/latent/contract", json={}).status_code == 405


def test_health_lists_read_only_science_status_endpoints() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is True
    assert body["hardware_actions"] is False
    assert body["endpoints"]["maturity"] == "/v1/em/uc06/maturity"
    assert body["endpoints"]["latent_contract"] == "/v1/em/uc06/latent/contract"
