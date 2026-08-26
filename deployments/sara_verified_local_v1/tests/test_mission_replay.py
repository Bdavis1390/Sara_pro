from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.mission_qualification import qualify_synthetic_mission_replay
from worldshepherd_sara.mission_replay import MissionEvent, derive_findings, propose_follow_on_actions, replay_events
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
        requirement_delta_id="PRE-RD-2026-0013",
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title="Navy post-mission debrief and replanning readiness target",
            agency="Navy",
            url="https://www.sbir.gov/",
            solicitation_or_topic="DON26BZ05-NV074",
            source_status=SourceStatus.GOVERNMENT_SECONDARY_VERIFIED,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement="Preserve mission evidence, reconstruct events, derive bounded findings, and keep follow-on COAs behind human authorization.",
        recurrence="Release-5 post-mission autonomy demand",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["OVERWATCH", "ECHO", "PRIME", "autonomy governance"],
        existing_capability=["synthetic deterministic mission replay"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["operational mission data", "validated causal reasoning", "CCA integration"],
        claims_boundary=["Synthetic mission-event evidence only"],
    )


def test_mission_replay_derives_expected_findings_and_proposals():
    fixture = json.loads((ROOT / "fixtures" / "mission_replay_synthetic_v1.json").read_text())
    events = [MissionEvent.model_validate(event) for event in fixture["events"]]
    findings = derive_findings(replay_events(events))
    proposals = propose_follow_on_actions(findings)
    assert sorted(f.finding_type for f in findings) == sorted(fixture["expected"]["finding_types"])
    assert sorted(p.action for p in proposals) == sorted(fixture["expected"]["proposal_actions"])
    assert all(p.state.value == "PROPOSED" for p in proposals)


def test_mission_qualification_bundle_retains_event_to_finding_to_proposal_lineage():
    fixture = json.loads((ROOT / "fixtures" / "mission_replay_synthetic_v1.json").read_text())
    bundle = qualify_synthetic_mission_replay(
        fixture=fixture,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    assert bundle["evidence"][0]["result"] == "PASS"
    graph = bundle["evidence_graph"]
    node_types = {node["node_type"] for node in graph["nodes"]}
    relations = {edge["relation"] for edge in graph["edges"]}
    assert {"mission_event", "debrief_finding", "prime_action_proposal"}.issubset(node_types)
    assert {"supports", "informs"}.issubset(relations)
    assert all(p["state"] == "PROPOSED" for p in bundle["prime_action_proposals"])
