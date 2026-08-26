from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.mbse_benchmark import benchmark_synthetic_mbse, qualify_synthetic_mbse
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
        requirement_delta_id="PRE-RD-2026-0002",
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title="NAVSEA AI to MBSE synthetic qualification target",
            agency="NAVSEA",
            url="https://example.invalid/navsea-mbse-placeholder",
            solicitation_or_topic="DON26BX05-NP003",
            source_status=SourceStatus.GOVERNMENT_SECONDARY_VERIFIED,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement="Evaluate source-traceable reconstruction against a frozen synthetic ground truth.",
        recurrence="Release-5 capture requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["MBSE", "digital engineering", "provenance"],
        existing_capability=["conservative synthetic relationship extraction"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["general document understanding", "SysML/Cameo interoperability"],
        claims_boundary=["Synthetic fixture only; no Navy production reconstruction claim"],
    )


def test_synthetic_mbse_benchmark_meets_frozen_targets_without_unsupported_inference():
    fixture = json.loads((ROOT / "fixtures" / "mbse_legacy_fixture_v1.json").read_text())
    score = benchmark_synthetic_mbse(fixture)
    assert score.entity_precision == 1.0
    assert score.entity_recall == 1.0
    assert score.relationship_precision == 1.0
    assert score.relationship_recall == 1.0
    assert score.unsupported_entities == ()
    assert score.unsupported_relationships == ()
    assert score.missed_entities == ()
    assert score.missed_relationships == ()


def test_mbse_qualification_bundle_is_reproducible_and_narrowly_scoped():
    fixture = json.loads((ROOT / "fixtures" / "mbse_legacy_fixture_v1.json").read_text())
    first = qualify_synthetic_mbse(
        fixture=fixture,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    second = qualify_synthetic_mbse(
        fixture=fixture,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    assert first["evidence"][0]["result"] == "PASS"
    assert first["bundle_digest"] == second["bundle_digest"]
    assert "Synthetic rule-based extraction benchmark only" in first["scope_note"]
