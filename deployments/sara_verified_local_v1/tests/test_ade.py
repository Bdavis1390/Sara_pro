from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.ade import discover_expression
from worldshepherd_sara.ade_qualification import qualify_synthetic_discovery
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
        requirement_delta_id="PRE-RD-2026-0012",
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title="DARPA SPEED DIAL algorithm-discovery readiness target",
            agency="DARPA",
            url="https://www.darpa.mil/research/programs/speed-dial",
            solicitation_or_topic="DPA26TZ05-DV003",
            source_status=SourceStatus.OFFICIAL_SOURCE_VERIFIED,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement="Develop bounded automated discovery evidence without overstating D2P2/SOTA maturity.",
        recurrence="SPEED DIAL and predictive algorithm-discovery readiness",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["ADE-G", "AI governance", "digital engineering"],
        existing_capability=["bounded symbolic search kernel"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["SOTA benchmark", "real engineering workflow integration", "D2P2 prior evidence"],
        claims_boundary=["Synthetic discovery benchmark only; not SPEED DIAL D2P2 eligibility"],
    )


def test_ade_discovers_zero_error_interpretable_rule_deterministically():
    fixture = json.loads((ROOT / "fixtures" / "ade_symbolic_v1.json").read_text())
    kwargs = {
        "constants": tuple(fixture["search"]["constants"]),
        "max_depth": fixture["search"]["max_depth"],
        "beam_width": fixture["search"]["beam_width"],
    }
    first = discover_expression(fixture["problem"]["samples"], **kwargs)
    second = discover_expression(fixture["problem"]["samples"], **kwargs)
    assert first.mse == 0.0
    assert first.mse < first.baseline_mse
    assert first.human_interpretable is True
    assert first.expression.canonical() == second.expression.canonical()
    assert first.evaluated_candidates == second.evaluated_candidates


def test_ade_qualification_is_claims_bounded_and_reproducible():
    fixture = json.loads((ROOT / "fixtures" / "ade_symbolic_v1.json").read_text())
    first = qualify_synthetic_discovery(
        fixture=fixture,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    second = qualify_synthetic_discovery(
        fixture=fixture,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    assert first["evidence"][0]["result"] == "PASS"
    assert first["bundle_digest"] == second["bundle_digest"]
    assert "no SOTA" in first["scope_note"]
