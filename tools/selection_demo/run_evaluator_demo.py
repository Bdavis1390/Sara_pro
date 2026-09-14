from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from worldshepherd_sara.autonomy_policy import (
    AutonomousActionCandidate,
    AutonomyPolicy,
    ExecutionDisposition,
    evaluate_candidate,
)
from worldshepherd_sara.ddil_reconcile import VersionedState, reconcile_key
from worldshepherd_sara.mission_replay import (
    MissionEvent,
    derive_findings,
    mission_replay_graph,
    propose_follow_on_actions,
    replay_events,
)
from worldshepherd_sara.prime import ActionState, decide_action, revoke_action
from worldshepherd_sara.sensor_fusion import Observation, fuse_observations, fusion_graph


FIXED_DECISION_UTC = "2026-09-13T21:00:00+00:00"
FIXED_REVOCATION_UTC = "2026-09-13T21:01:00+00:00"


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _model_or_dataclass(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {
        key: getattr(value, key)
        for key in value.__dataclass_fields__
    }


def _run_scenario(repo_root: Path) -> dict[str, Any]:
    fixtures = repo_root / "deployments" / "sara_verified_local_v1" / "fixtures"

    fusion_fixture = json.loads((fixtures / "sensor_fusion_synthetic_v1.json").read_text())
    observations = [Observation.model_validate(item) for item in fusion_fixture["observations"]]
    association = fusion_fixture["association"]
    tracks = fuse_observations(
        observations,
        max_spatial_distance=association["max_spatial_distance"],
        max_time_delta_seconds=association["max_time_delta_seconds"],
    )
    fusion_evidence = fusion_graph(
        graph_id="EVAL-FUSION-GRAPH",
        observations=observations,
        tracks=tracks,
    )

    mission_fixture = json.loads((fixtures / "mission_replay_synthetic_v1.json").read_text())
    events = [MissionEvent.model_validate(item) for item in mission_fixture["events"]]
    replayed = replay_events(events)
    findings = derive_findings(replayed)
    proposals = propose_follow_on_actions(findings)
    mission_evidence = mission_replay_graph(
        graph_id="EVAL-MISSION-GRAPH",
        events=replayed,
        findings=findings,
        proposals=proposals,
    )

    policy = AutonomyPolicy(
        policy_id="EVAL-POLICY-001",
        allowed_auto_action_types=["refresh_cache"],
        denied_action_types=["release_payload"],
        minimum_auto_confidence=0.99,
        maximum_auto_authority=1,
    )

    policy_reviews: list[dict[str, Any]] = []
    decided = []
    for index, proposal in enumerate(proposals):
        candidate = AutonomousActionCandidate(
            action_id=proposal.proposal_id,
            action_type=proposal.action,
            confidence=1.0,
            requested_authority=2,
            reversible=True,
        )
        disposition, reasons = evaluate_candidate(candidate, policy)
        policy_reviews.append(
            {
                "proposal_id": proposal.proposal_id,
                "disposition": disposition.value,
                "reasons": reasons,
            }
        )
        state = ActionState.APPROVED if index != 1 else ActionState.DENIED
        decision = decide_action(
            proposal,
            reviewer="identified-human-evaluator",
            state=state,
            reason="Synthetic evaluator decision after reviewing evidence lineage and policy disposition.",
        ).model_copy(update={"decision_utc": FIXED_DECISION_UTC})
        if index == 2 and decision.state is ActionState.APPROVED:
            decision = revoke_action(
                decision,
                reviewer="identified-human-evaluator",
                reason="Synthetic revocation demonstrates bounded human authority over previously approved action.",
            ).model_copy(update={"decision_utc": FIXED_REVOCATION_UTC})
        decided.append(decision)

    explicitly_denied = AutonomousActionCandidate(
        action_id="EVAL-DENIED-001",
        action_type="release_payload",
        confidence=1.0,
        requested_authority=0,
        reversible=True,
    )
    denied_disposition, denied_reasons = evaluate_candidate(explicitly_denied, policy)

    partition_left = VersionedState(
        key="mission_mode",
        value="search",
        logical_clock=9,
        authority=1,
        source_node="left",
    )
    partition_right = VersionedState(
        key="mission_mode",
        value="return",
        logical_clock=9,
        authority=1,
        source_node="right",
    )
    unresolved = reconcile_key([partition_left, partition_right])
    human_resolution = VersionedState(
        key="mission_mode",
        value="hold_for_review",
        logical_clock=10,
        authority=2,
        source_node="human-authority",
    )
    resolved = reconcile_key([partition_left, partition_right, human_resolution])

    source_ids = [item.observation_id for item in observations]
    event_ids = [f"event:{item.sequence}" for item in replayed]
    claims = [
        {
            "claim_id": "C1",
            "statement": "Synthetic fused tracks preserve observation lineage.",
            "evidence_refs": [f"obs:{item}" for item in source_ids],
        },
        {
            "claim_id": "C2",
            "statement": "Mission findings and proposed actions are traceable to replayed mission events.",
            "evidence_refs": event_ids,
        },
        {
            "claim_id": "C3",
            "statement": "High-authority follow-on actions remain behind identified-human review in this scenario.",
            "evidence_refs": [f"decision:{item.proposal_id}" for item in decided],
        },
        {
            "claim_id": "C4",
            "statement": "An explicitly denied action fails closed under the configured autonomy policy.",
            "evidence_refs": ["policy:EVAL-POLICY-001", "candidate:EVAL-DENIED-001"],
        },
        {
            "claim_id": "C5",
            "statement": "Equal-clock equal-authority DDIL divergence is surfaced as a conflict and is not silently resolved.",
            "evidence_refs": ["ddil:left", "ddil:right", "ddil:unresolved"],
        },
        {
            "claim_id": "C6",
            "statement": "A later higher-authority human resolution deterministically closes the synthetic DDIL conflict.",
            "evidence_refs": ["ddil:human-resolution", "ddil:resolved"],
        },
    ]

    package = {
        "scenario_id": "WS-EVALUATOR-DEMO-V1",
        "scope": "UNCLASSIFIED_SYNTHETIC_SOFTWARE_DEMONSTRATION",
        "sensor_fusion": {
            "observations": [item.model_dump(mode="json") for item in observations],
            "tracks": [_model_or_dataclass(item) for item in tracks],
            "evidence_graph": fusion_evidence.model_dump(mode="json"),
        },
        "mission_replay": {
            "events": [item.model_dump(mode="json") for item in replayed],
            "findings": [_model_or_dataclass(item) for item in findings],
            "proposals": [item.model_dump(mode="json") for item in proposals],
            "evidence_graph": mission_evidence.model_dump(mode="json"),
        },
        "policy_and_human_authorization": {
            "policy": policy.model_dump(mode="json"),
            "reviews": policy_reviews,
            "decisions": [item.model_dump(mode="json") for item in decided],
            "explicitly_denied_candidate": explicitly_denied.model_dump(mode="json"),
            "explicitly_denied_disposition": denied_disposition.value,
            "explicitly_denied_reasons": denied_reasons,
        },
        "ddil": {
            "left": partition_left.model_dump(mode="json"),
            "right": partition_right.model_dump(mode="json"),
            "unresolved": {
                "state": unresolved.state.value,
                "selected": None if unresolved.selected is None else unresolved.selected.model_dump(mode="json"),
                "reason": unresolved.reason,
            },
            "human_resolution": human_resolution.model_dump(mode="json"),
            "resolved": {
                "state": resolved.state.value,
                "selected": None if resolved.selected is None else resolved.selected.model_dump(mode="json"),
                "reason": resolved.reason,
            },
        },
        "claims": claims,
    }

    checks = {
        "all_claims_have_evidence_refs": all(bool(item["evidence_refs"]) for item in claims),
        "fusion_preserves_all_observation_ids": sorted(
            obs_id for track in tracks for obs_id in track.source_observation_ids
        ) == sorted(source_ids),
        "all_proposals_require_human_review": all(
            item["disposition"] == ExecutionDisposition.HUMAN_REVIEW_REQUIRED.value
            for item in policy_reviews
        ),
        "explicit_denial_fails_closed": denied_disposition is ExecutionDisposition.DENIED,
        "human_decisions_are_identified": all(item.reviewer == "identified-human-evaluator" for item in decided),
        "approval_denial_and_revocation_present": {
            item.state.value for item in decided
        }.issuperset({"APPROVED", "DENIED", "REVOKED"}),
        "ddil_conflict_not_silently_resolved": unresolved.state.value == "CONFLICT" and unresolved.selected is None,
        "higher_authority_resolution_selected": resolved.selected is not None and resolved.selected.source_node == "human-authority",
    }
    package["acceptance_checks"] = checks
    package["semantic_digest"] = _digest(package)
    return package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--software-commit", default=os.environ.get("GITHUB_SHA", "UNKNOWN"))
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    first = _run_scenario(repo_root)
    second = _run_scenario(repo_root)
    deterministic = first["semantic_digest"] == second["semantic_digest"]
    all_checks = all(first["acceptance_checks"].values())

    record = {
        "schema": "WS-EVALUATOR-DEMONSTRATION-EVIDENCE-V1",
        "result": "PASS" if deterministic and all_checks else "FAIL",
        "evidence_status": "INTERNAL_REPRODUCIBLE_SYNTHETIC_EVIDENCE",
        "software_commit": args.software_commit,
        "executed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "deterministic_rerun": deterministic,
        "scenario": first,
        "claims_boundary": [
            "Synthetic/public-style software evidence only.",
            "No operational sensor performance, CUI authorization, classified capability, flight validation, government acceptance, or external partner validation is established.",
            "Human decisions in this demonstration are synthetic evaluator actions, not real-world command authority.",
        ],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if record["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
