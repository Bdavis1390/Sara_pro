from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from worldshepherd_sara.em_intelligence import (
    EMCandidate,
    EMEvidenceClass,
    EMIntent,
    EMOperatingMode,
    current_uc06_evidence,
    router,
)


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_uc06_evidence_is_read_only_and_bounded():
    with _client() as client:
        response = client.get("/v1/em/uc06/evidence")
        assert response.status_code == 200
        body = response.json()
        assert body["evidence_class"] == "SIMULATED_ONLY"
        assert body["source_prefix"] == "A001-A026"
        assert body["active_recovery_touched"] is False
        assert body["scientific_gate_change"] is False
        assert body["overall_convergence"] == "NOT_ADJUDICATED"
        assert body["h2_promotion_authorized"] is False
        assert body["full_campaign_authorized"] is False
        assert body["first_two_pc_variance_fraction"] == pytest.approx(0.974061386803)
        assert body["strongest_angle_discriminability"] == pytest.approx(230.238908861)
        assert body["largest_tm_programmable_phase_span_deg"] == pytest.approx(83.9532267062)

        # No mutation endpoint exists on this router.
        denied = client.post("/v1/em/uc06/evidence", json={})
        assert denied.status_code == 405


def test_em_contract_explicitly_disables_hardware_actions():
    with _client() as client:
        response = client.get("/v1/em/contract")
        assert response.status_code == 200
        body = response.json()
        assert body["read_only"] is True
        assert body["hardware_actions"] is False
        assert "PALACE_FULL_WAVE_REMAINS_FORWARD_VALIDATOR" in body["claims_boundary"]
        assert "PRIME_REQUIRED_BEFORE_FUTURE_HARDWARE_ACTION" in body["claims_boundary"]


def test_em_intent_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        EMIntent(
            intent_id="INTENT-1",
            objective="angle characterization",
            operating_mode=EMOperatingMode.AUDIT_CALIBRATION,
            unexpected="not-allowed",
        )


def test_candidate_cannot_default_to_authorized_hardware_action():
    candidate = EMCandidate(
        candidate_id="CAND-1",
        source_model="UC06-P1",
        source_version="D4",
        evidence_class=EMEvidenceClass.SIMULATED_ONLY,
        convergence_status="NOT_ADJUDICATED",
        model_discrepancy_status="OPEN",
    )
    assert candidate.hardware_action_authorized is False


def test_current_evidence_preserves_claims_boundary():
    evidence = current_uc06_evidence()
    assert "MEDIUM_FINE_GATE_PENDING" in evidence.claims_boundary
    assert "ENERGY_CLOSURE_PENDING" in evidence.claims_boundary
    assert "NO_HARDWARE_VALIDATION" in evidence.claims_boundary
    assert evidence.strongest_tm_state_case == "COARSE_TM_60deg_HIGH_C_vs_SAFE_OPEN"
