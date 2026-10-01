from fastapi.testclient import TestClient

from worldshepherd_sara.em_intelligence_service import app


client = TestClient(app)


def test_recovery_status_is_not_ingested_and_non_actuating() -> None:
    response = client.get("/v1/em/uc06/recovery/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NOT_INGESTED"
    assert body["sealed_completion_receipt_ingested"] is False
    assert body["scientific_convergence"] == "NOT_ADJUDICATED"
    assert body["hardware_actions"] is False


def test_recovery_contract_preserves_p1_controls() -> None:
    response = client.get("/v1/em/uc06/recovery/contract")
    assert response.status_code == 200
    body = response.json()
    assert body["segment"] == "A027-A054"
    assert body["planned_job_count"] == 28
    assert body["fresh_A027_replacement_required"] is True
    assert body["original_A027_partial_reuse_allowed"] is False
    assert body["automatic_retries_allowed"] == 0
    assert body["sleep_inhibitor_required"] is True
    assert body["hardware_actions"] is False


def test_frozen_convergence_contract_has_no_current_result() -> None:
    response = client.get("/v1/em/uc06/convergence/contract")
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_contract_id"] == "r2q-d6e-20260821T225252Z"
    assert body["current_result_ingested"] is False
    assert body["overall_convergence"] == "NOT_ADJUDICATED"
    assert body["expected_anchor_count"] == 54
    assert body["expected_medium_fine_pair_count"] == 18
    assert body["frozen_thresholds"]["complex_s11_max_delta"] == 0.02
    assert body["frozen_thresholds"]["resonance_shift_fraction"] == 0.0025
    assert body["frozen_thresholds"]["energy_closure_fraction"] == 0.02


def test_recovery_and_convergence_endpoints_are_read_only() -> None:
    assert client.post("/v1/em/uc06/recovery/status", json={}).status_code == 405
    assert client.post("/v1/em/uc06/recovery/contract", json={}).status_code == 405
    assert client.post("/v1/em/uc06/convergence/contract", json={}).status_code == 405
