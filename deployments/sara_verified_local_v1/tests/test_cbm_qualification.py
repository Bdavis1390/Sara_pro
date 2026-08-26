from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.cbm_qualification import qualify_synthetic_cbm
from worldshepherd_sara.qualification import (
    CapabilityStatus,
    DemandClass,
    ForecastHorizon,
    RequirementDeltaRecord,
    SourceRecord,
    SourceStatus,
)

ROOT = Path(__file__).resolve().parents[1]


def _requirement() -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id="PRE-RD-2026-0016",
        demand_class=DemandClass.EMERGING_DEMAND,
        source=SourceRecord(title="CBM+ / digital-twin readiness target", agency="Worldshepherd PRE", url="internal://pre/cbm-v1", source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE, retrieved_utc="2026-08-26T00:00:00Z"),
        statement="Establish traceable synthetic health-state classification before predictive-maintenance claims.",
        recurrence="Reusable CBM+/digital-twin readiness requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["CBM+","digital twins","ECHO","maintenance"],
        existing_capability=["bounded envelope-based health classification"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["real asset telemetry","failure labels","RUL validation"],
        claims_boundary=["Synthetic telemetry only"],
    )


def test_cbm_qualification_bundle_is_traceable_and_claims_bounded():
    fixture = json.loads((ROOT / "fixtures" / "cbm_twin_synthetic_v1.json").read_text())
    bundle = qualify_synthetic_cbm(fixture=fixture, requirement=_requirement(), software_commit="test-commit", executed_utc="2026-08-26T00:00:00Z", operator="pytest")
    assert bundle["evidence"][0]["result"] == "PASS"
    assert bundle["evidence"][0]["outputs"][0]["anomaly_count"] == 2
    assert bundle["evidence"][0]["outputs"][0]["traceable"] is True
    assert "no real platform" in bundle["scope_note"]
