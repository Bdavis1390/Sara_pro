import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "osd_rf_classification_capture_gate_v1.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_direct_phase_ii_prime_status_fails_closed():
    payload = _payload()
    assert payload["topic"]["award_path"] == "DIRECT_TO_PHASE_II"
    assert payload["capture_decision"]["prime_status"] == "NO_GO_WITH_CURRENT_EVIDENCE"


def test_adjacent_rf_work_does_not_become_classifier_maturity():
    state = _payload()["current_worldshepherd_state"]
    assert state["rf_signal_classifier_implemented"] is False
    assert state["rf_classifier_benchmark_evidence"] == "NONE_FOUND_IN_CURRENT_MAIN_REPOSITORY"
    assert state["metasurface_or_rf_physics_work_relevance"] == "ADJACENT_ONLY_NOT_CLASSIFICATION_MATURITY"


def test_all_solicitation_attributes_have_evidence_gates():
    mapping = _payload()["requirement_mapping"]
    assert len(mapping) == 6
    assert all(item["minimum_evidence"] for item in mapping)
    assert sum(item["status"] == "GAP" for item in mapping) >= 5


def test_claims_boundary_rejects_operational_rf_claims():
    boundary = " ".join(_payload()["claims_boundary"]).lower()
    for phrase in (
        "no worldshepherd rf signal classifier is currently claimed",
        "does not establish signal-classification maturity",
        "no expert-analyst speed advantage",
        "no sigint data",
    ):
        assert phrase in boundary
