from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.manufacturing_qualification import qualify_synthetic_manufacturing_thread
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
        requirement_delta_id="PRE-RD-2026-0017",
        demand_class=DemandClass.EMERGING_DEMAND,
        source=SourceRecord(title="DED/manufacturing digital-thread readiness target", agency="Worldshepherd PRE", url="internal://pre/mfg-thread-v1", source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE, retrieved_utc="2026-08-26T00:00:00Z"),
        statement="Establish machine-readable material/process/specimen provenance before physical qualification claims.",
        recurrence="Reusable additive-manufacturing qualification requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["DED","additive manufacturing","digital thread","qualification evidence"],
        existing_capability=["manufacturing digital-thread schema"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["physical coupon","machine calibration evidence","property measurement","partner lab validation"],
        claims_boundary=["Digital thread only"],
    )


def test_manufacturing_qualification_bundle_stays_digital_thread_only():
    fixture = json.loads((ROOT / "fixtures" / "manufacturing_thread_synthetic_v1.json").read_text())
    bundle = qualify_synthetic_manufacturing_thread(fixture=fixture, requirement=_requirement(), software_commit="test-commit", executed_utc="2026-08-26T00:00:00Z", operator="pytest")
    record = bundle["evidence"][0]
    assert record["result"] == "PASS"
    assert record["evidence_scope"] == "SOFTWARE"
    assert record["physical_validation_performed"] is False
    assert record["outputs"][0]["qualification_state"] == "DIGITAL_THREAD_ONLY"
    assert "no physical coupon" in bundle["scope_note"]
