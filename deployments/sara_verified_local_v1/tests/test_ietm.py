from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.ietm import (
    inspect_synthetic_projection,
    project_synthetic_manual_to_xml,
    qualify_synthetic_ietm,
)
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
        requirement_delta_id="PRE-RD-2026-0003",
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title="NAVAIR IETM synthetic qualification target",
            agency="NAVAIR",
            url="https://example.invalid/navair-ietm-placeholder",
            solicitation_or_topic="DON26BZ05-NV078",
            source_status=SourceStatus.GOVERNMENT_SECONDARY_VERIFIED,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement="Preserve structure and source markings through a synthetic technical-data XML projection.",
        recurrence="Release-5 capture requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["technical data", "IETM", "provenance"],
        existing_capability=["synthetic XML projection"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["S1000D validation", "Navy viewer compatibility"],
        claims_boundary=["Synthetic XML only; no standards-compliance claim"],
    )


def test_synthetic_ietm_projection_preserves_structure_and_marking():
    fixture = json.loads((ROOT / "fixtures" / "ietm_synthetic_v1.json").read_text())
    xml_text = project_synthetic_manual_to_xml(fixture)
    observed = inspect_synthetic_projection(xml_text, fixture)
    assert observed == fixture["expected"]
    assert "SYNTHETIC DISTRIBUTION MARKING - TEST ONLY" in xml_text


def test_synthetic_ietm_uses_shared_qualification_bundle():
    fixture = json.loads((ROOT / "fixtures" / "ietm_synthetic_v1.json").read_text())
    bundle = qualify_synthetic_ietm(
        fixture=fixture,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    assert bundle["evidence"][0]["result"] == "PASS"
    assert bundle["evidence"][0]["evidence_scope"] == "SOFTWARE"
    assert bundle["fixture_id"] == "WS-IETM-SYNTH-001"
    assert "no S1000D" in bundle["scope_note"]
