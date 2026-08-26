from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.qualification import (
    CapabilityStatus,
    DemandClass,
    ForecastHorizon,
    RequirementDeltaRecord,
    SourceRecord,
    SourceStatus,
)
from worldshepherd_sara.sensor_fusion import Observation, fuse_observations
from worldshepherd_sara.sensor_fusion_qualification import qualify_synthetic_sensor_fusion

ROOT = Path(__file__).resolve().parents[1]


def _requirement() -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id="PRE-RD-2026-0014",
        demand_class=DemandClass.EMERGING_DEMAND,
        source=SourceRecord(
            title="Synthetic distributed sensing readiness target",
            agency="Worldshepherd PRE",
            url="internal://pre/sensor-fusion-v1",
            source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement="Establish a source-traceable deterministic fusion baseline before learned or operational sensor-fusion work.",
        recurrence="Reusable distributed sensing readiness requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["distributed sensing", "sensor fusion", "ECHO", "mission assurance"],
        existing_capability=["deterministic weighted 2-D synthetic fusion baseline"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["operational sensor data", "validated multi-target association", "edge deployment"],
        claims_boundary=["Synthetic 2-D point observations only"],
    )


def test_synthetic_fusion_is_deterministic_and_preserves_observation_lineage():
    fixture = json.loads((ROOT / "fixtures" / "sensor_fusion_synthetic_v1.json").read_text())
    observations = [Observation.model_validate(item) for item in fixture["observations"]]
    association = fixture["association"]
    first = fuse_observations(
        observations,
        max_spatial_distance=association["max_spatial_distance"],
        max_time_delta_seconds=association["max_time_delta_seconds"],
    )
    second = fuse_observations(
        observations,
        max_spatial_distance=association["max_spatial_distance"],
        max_time_delta_seconds=association["max_time_delta_seconds"],
    )
    assert first == second
    assert len(first) == 2
    assert sorted(obs for track in first for obs in track.source_observation_ids) == sorted(
        item["observation_id"] for item in fixture["observations"]
    )


def test_sensor_fusion_qualification_meets_frozen_truth_target_and_retains_graph_lineage():
    fixture = json.loads((ROOT / "fixtures" / "sensor_fusion_synthetic_v1.json").read_text())
    bundle = qualify_synthetic_sensor_fusion(
        fixture=fixture,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    assert bundle["evidence"][0]["result"] == "PASS"
    assert bundle["evidence"][0]["outputs"][0]["max_position_error"] <= fixture["expected"]["max_position_error"]
    assert bundle["evidence"][0]["outputs"][0]["source_observations_preserved"] is True
    assert {edge["relation"] for edge in bundle["evidence_graph"]["edges"]} == {"contributes_to"}
    assert "no AESA" in bundle["scope_note"]
