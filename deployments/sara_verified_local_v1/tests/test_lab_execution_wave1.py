import json
from pathlib import Path


MANIFEST = Path("fixtures/lab_execution_campaigns_wave1_v1.json")
FROZEN_PVK_HEAD = "9165fcae4b82277e050b76f606687f1179c31021"


def _load():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_wave1_manifest_is_preregistration_only():
    payload = _load()
    assert payload["schema_version"] == "ws-lab-execution-wave1-1"
    assert payload["status"] == "PREREGISTRATION_TEMPLATE_NOT_EXPERIMENTAL_EVIDENCE"
    assert payload["source_candidate_commit"] == FROZEN_PVK_HEAD
    assert payload["maturity_promoted"] is False


def test_wave1_has_exactly_the_two_first_physical_campaigns():
    payload = _load()
    campaigns = {item["campaign_id"]: item for item in payload["campaigns"]}
    assert set(campaigns) == {"SV-WSALTI-001-P1", "SV-META-001-P1"}
    assert all(item["current_claim_boundary"] == "REQUIRES_LAB_VALIDATION" for item in campaigns.values())


def test_ws_alti_preserves_independent_build_and_specimen_minima():
    payload = _load()
    campaign = next(item for item in payload["campaigns"] if item["campaign_id"] == "SV-WSALTI-001-P1")
    conditions = {item["condition_id"]: item for item in campaign["conditions"]}
    assert len(conditions["BASELINE"]["build_ids"]) == 3
    assert len(conditions["CANDIDATE"]["build_ids"]) == 3
    assert len(set(conditions["BASELINE"]["build_ids"] + conditions["CANDIDATE"]["build_ids"])) == 6

    roles = {item["specimen_role"]: item["count"] for item in campaign["specimen_plan_per_build"]}
    assert roles == {"MET-CHEM": 1, "HARD-MAP": 1, "TEN": 3}

    ids = campaign["minimum_expected_specimen_ids"]
    assert len(ids) == 30
    assert len(set(ids)) == 30
    assert sum("-TEN-" in item for item in ids) == 18


def test_ws_alti_blocks_overclaiming():
    payload = _load()
    campaign = next(item for item in payload["campaigns"] if item["campaign_id"] == "SV-WSALTI-001-P1")
    blocked = set(campaign["blocked_claims_until_gate_closes"])
    assert "aerospace-qualified material" in blocked
    assert "programmable zoning established" in blocked
    assert campaign["advancement_gate"]["target_state"] == "INTERNAL_TEST"


def test_metasurface_requires_replication_and_bounded_claims():
    payload = _load()
    campaign = next(item for item in payload["campaigns"] if item["campaign_id"] == "SV-META-001-P1")
    devices = {item["device_id"]: item for item in campaign["device_plan"]}
    assert {"META-REF-01", "META-UC-01", "META-ACT-01", "META-ACT-02", "META-ACT-03"} <= set(devices)
    assert sum(key.startswith("META-ACT-") for key in devices) == 3
    assert len(campaign["command_state_template"]) >= 3

    blocked = set(campaign["blocked_claims_until_later_application_specific_validation"])
    assert {"stealth", "cloaking", "broad-spectrum cancellation"} <= blocked
    assert campaign["advancement_gate"]["target_state"] == "INTERNAL_TEST"


def test_both_campaigns_require_raw_and_uncertainty_evidence():
    payload = _load()
    for campaign in payload["campaigns"]:
        text = " ".join(campaign["required_return_evidence"]).lower()
        assert "raw" in text
        assert "uncertainty" in text or "limitations" in text
        assert "calibration" in text
