from fastapi.testclient import TestClient

from worldshepherd_sara.em_intelligence_service import app


def test_maturity_reducer_contract_is_read_only_and_fail_closed():
    client = TestClient(app)
    response = client.get("/v1/em/uc06/maturity/reducer-contract")
    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is True
    assert body["persisted_state_mutation"] is False
    assert body["hardware_actions"] is False
    assert body["verified_source_bytes_required"] is True
    assert body["currently_reducible_evidence"] == ["D5_DIAGNOSTIC", "POWER_RECOVERY"]
    assert "FROZEN_MEDIUM_FINE_CONVERGENCE" in body["evidence_that_remains_separate"]
    assert "HASH_VERIFICATION_IS_INTEGRITY_NOT_PHYSICS_VALIDATION" in body["claims_boundary"]
    assert "NO_HARDWARE_ACTION" in body["claims_boundary"]


def test_health_advertises_reducer_contract_but_no_mutation_route():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is True
    assert body["hardware_actions"] is False
    assert body["endpoints"]["maturity_reducer_contract"] == (
        "/v1/em/uc06/maturity/reducer-contract"
    )
