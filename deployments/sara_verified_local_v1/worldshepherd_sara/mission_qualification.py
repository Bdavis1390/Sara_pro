from __future__ import annotations

from typing import Any

from .mission_replay import (
    MissionEvent,
    derive_findings,
    mission_replay_graph,
    propose_follow_on_actions,
    replay_events,
)
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def qualify_synthetic_mission_replay(
    *,
    fixture: dict[str, Any],
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    events = [MissionEvent.model_validate(event) for event in fixture["events"]]
    replay = replay_events(events)
    findings = derive_findings(replay)
    proposals = propose_follow_on_actions(findings)
    graph = mission_replay_graph(
        graph_id=fixture["fixture_id"],
        events=replay,
        findings=findings,
        proposals=proposals,
    )
    observed_finding_types = sorted(finding.finding_type for finding in findings)
    observed_actions = sorted(proposal.action for proposal in proposals)
    expected_findings = sorted(fixture["expected"]["finding_types"])
    expected_actions = sorted(fixture["expected"]["proposal_actions"])
    all_proposed = all(proposal.state.value == "PROPOSED" for proposal in proposals)
    passed = (
        observed_finding_types == expected_findings
        and observed_actions == expected_actions
        and all_proposed is bool(fixture["expected"]["all_proposals_must_start_proposed"])
    )

    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-5001",
        requirement_id=requirement.requirement_delta_id,
        test_id="mission_replay_synthetic_v1",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest=canonical_digest(
            {"fixture_id": fixture["fixture_id"], "classification": fixture["classification"]}
        ),
        configuration_digest=canonical_digest({"replay_model": "deterministic_rules_v1"}),
        inputs=[{"event_count": len(events)}],
        outputs=[
            {
                "finding_types": observed_finding_types,
                "proposal_actions": observed_actions,
                "all_proposals_start_proposed": all_proposed,
                "graph_digest": canonical_digest(graph),
            }
        ],
        metrics=[
            {"name": "finding_set_match", "value": observed_finding_types == expected_findings},
            {"name": "proposal_set_match", "value": observed_actions == expected_actions},
            {"name": "all_proposals_proposed", "value": all_proposed},
        ],
        uncertainty=[
            {"name": "operational_generalization", "state": "NOT_EVALUATED"},
            {"name": "causal_validity", "state": "NOT_EVALUATED"},
        ],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=(
            "Synthetic mission replay produced the frozen findings and kept all follow-on actions behind a human approval gate"
            if passed
            else "Synthetic mission replay diverged from one or more frozen expectations"
        ),
        negative_evidence=[] if passed else [
            {
                "expected_findings": expected_findings,
                "observed_findings": observed_finding_types,
                "expected_actions": expected_actions,
                "observed_actions": observed_actions,
            }
        ],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    bundle = compile_qualification_bundle(requirement, [evidence], graph)
    bundle.pop("bundle_digest", None)
    bundle["fixture_id"] = fixture["fixture_id"]
    bundle["prime_action_proposals"] = [proposal.model_dump(mode="json") for proposal in proposals]
    bundle["scope_note"] = (
        "Synthetic deterministic mission-debrief/replay evidence only; no operational CCA/UAS, causal-AI, or autonomous replanning claim. Follow-on actions remain proposals pending identified human authorization."
    )
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle
