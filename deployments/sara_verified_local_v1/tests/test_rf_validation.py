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
from worldshepherd_sara.rf_validation import qualify_synthetic_rf_discrepancy

ROOT = Path(__file__).resolve().parents[1]


def _requirement() -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id="PRE-RD-2026-0015",
        demand_class=DemandClass.EMERGING_DEMAND,
        source=SourceRecord(
            title="RF/metasurface simulation-to-measurement readiness target",
            agency="Worldshepherd PRE",
            url="internal://pre/rf-discrepancy-v1",
            source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement="Quantify simulation-to-measurement discrepancy before any physical RF performance claim.",
        recurrence="Reusable RF/metasurface readiness requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["RF", "metasurfaces", "simulation governance"],
        existing_capability=["generic discrepancy accounting"],
        capability_status=[CapabilityStatus.SIMULATED_ONLY],
        missing_capability=["fabricated coupon", "VNA/chamber measurement", "independent physical validation"],
        claims_boundary=["Synthetic RF values only"],
    )


def test_rf_synthetic_discrepancy_bundle_passes_frozen_targets_without_physical_claim():
    fixture = json.loads((ROOT / "fixtures" / "rf_sparams_synthetic_v1.json").read_text())
    bundle = qualify_synthetic_rf_discrepancy(
        fixture=fixture,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    record = bundle["evidence"][0]
    assert record["result"] == "PASS"
    assert record["evidence_scope"] == "SIMULATION"
    assert record["capability_status"] == "SIMULATED_ONLY"
    assert record["physical_validation_performed"] is False
    assert "no VNA" in bundle["scope_note"]
