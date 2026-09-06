from __future__ import annotations

import json
from pathlib import Path


REGISTRY = Path("fixtures/scientific_validation_campaigns_v1.json")


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_validation_campaign_registry_is_bounded_and_complete():
    payload = load_registry()
    assert payload["schema_version"] == "ws-scientific-validation-campaigns-1"
    assert payload["policy"]["foundation_evidence_is_not_system_validation"] is True
    assert payload["policy"]["simulation_is_not_physical_validation"] is True
    assert payload["policy"]["independent_replication_required_for_extraordinary_claims"] is True

    campaigns = payload["campaigns"]
    ids = [item["campaign_id"] for item in campaigns]
    assert len(ids) == len(set(ids))
    assert len(campaigns) >= 8

    for item in campaigns:
        assert item["project_id"]
        assert item["concept"]
        assert item["foundation_status"]
        assert item["worldshepherd_specific_status"]
        assert item["next_experiments"]
        assert item["minimum_evidence_to_advance"]


def test_registry_does_not_silently_claim_worldshepherd_physical_validation():
    payload = load_registry()
    prohibited_specific_statuses = {
        "VALIDATED",
        "PROVEN",
        "CERTIFIED",
        "FLIGHT_PROVEN",
        "CLINICALLY_VALIDATED",
    }
    for campaign in payload["campaigns"]:
        assert campaign["worldshepherd_specific_status"] not in prohibited_specific_statuses


def test_em_propulsion_campaign_preserves_conservation_boundary():
    payload = load_registry()
    campaign = next(item for item in payload["campaigns"] if item["project_id"] == "RESONANT_EM_PROPULSION")
    unsupported = {value.lower() for value in campaign["not_yet_supported"]}
    assert "reactionless propulsion" in unsupported
    assert any("photon" in step.lower() for step in campaign["next_experiments"])
    assert any("independent replication" in item.lower() for item in campaign["minimum_evidence_to_advance"])
