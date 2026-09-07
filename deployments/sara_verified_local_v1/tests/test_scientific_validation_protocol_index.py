from __future__ import annotations

import json
from pathlib import Path


def test_every_validation_campaign_has_a_protocol_index_entry():
    campaigns = json.loads(
        Path("fixtures/scientific_validation_campaigns_v1.json").read_text(encoding="utf-8")
    )["campaigns"]
    index = json.loads(
        Path("fixtures/scientific_validation_protocol_index_v1.json").read_text(
            encoding="utf-8"
        )
    )["entries"]

    campaign_ids = {item["campaign_id"] for item in campaigns}
    indexed_ids = {item["campaign_id"] for item in index}
    assert indexed_ids == campaign_ids


def test_every_indexed_protocol_exists_and_has_minimum_evidence():
    entries = json.loads(
        Path("fixtures/scientific_validation_protocol_index_v1.json").read_text(
            encoding="utf-8"
        )
    )["entries"]

    for entry in entries:
        path = Path(entry["protocol_path"])
        assert path.is_file(), entry["campaign_id"]
        assert path.stat().st_size > 500, entry["campaign_id"]
        assert entry["current_worldshepherd_state"]
        assert entry["next_gate"]
        assert len(entry["minimum_evidence"]) >= 5


def test_protocol_index_preserves_maturity_boundaries():
    payload = json.loads(
        Path("fixtures/scientific_validation_protocol_index_v1.json").read_text(
            encoding="utf-8"
        )
    )
    policy = payload["policy"]
    assert policy["protocol_presence_does_not_promote_maturity"] is True
    assert policy["external_foundation_does_not_validate_worldshepherd_artifact"] is True
    assert policy["raw_evidence_and_provenance_required_for_physical_test"] is True
    assert policy["independent_replication_required_for_extraordinary_claims"] is True
