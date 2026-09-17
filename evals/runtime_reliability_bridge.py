#!/usr/bin/env python3
"""Convert independently adjudicated controller traces into reliability source counts.

This bridge does not grade its own work. Every admitted trial must include an
independent final-state adjudication identity distinct from the planner identity.
The resulting counts are designed to feed evals/adapters/reliability_eval.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


def _required(record: Dict[str, Any], fields: List[str], prefix: str) -> None:
    missing = [name for name in fields if record.get(name) in (None, "")]
    if missing:
        raise ValueError(f"{prefix} missing required fields: {', '.join(missing)}")


def _is_recovery_opportunity(steps: List[Dict[str, Any]]) -> bool:
    for step in steps[:-1] if len(steps) > 1 else steps:
        verification = step.get("verification")
        if isinstance(verification, dict):
            if verification.get("success") is False and verification.get("recoverable") is True:
                return True
    return False


def aggregate(source: Dict[str, Any]) -> Dict[str, Any]:
    _required(
        source,
        [
            "system_id",
            "system_version",
            "evaluation_date",
            "environment",
            "target_level",
            "grader_version",
            "source_or_artifact_hash",
            "controls",
            "trials",
        ],
        "runtime reliability source",
    )
    if source["target_level"] not in ("candidate", "verified"):
        raise ValueError("target_level must be candidate or verified")
    if not isinstance(source["controls"], dict):
        raise ValueError("controls must be an object")
    if not isinstance(source["trials"], list) or not source["trials"]:
        raise ValueError("trials must be a non-empty array")

    seen_ids = set()
    workflow_trials = 0
    workflow_successes = 0
    recovery_trials = 0
    recovery_successes = 0
    integrity_trials = 0
    severe_false_completions = 0
    admitted_ids: List[str] = []

    for index, trial in enumerate(source["trials"]):
        if not isinstance(trial, dict):
            raise ValueError(f"trials[{index}] must be an object")
        _required(
            trial,
            [
                "trial_id",
                "planner_identity",
                "final_state_evaluator_identity",
                "controller_status",
                "independent_final_state_pass",
                "integrity_severity",
                "steps",
            ],
            f"trials[{index}]",
        )
        trial_id = str(trial["trial_id"])
        if trial_id in seen_ids:
            raise ValueError(f"duplicate trial_id: {trial_id}")
        seen_ids.add(trial_id)

        if trial["planner_identity"] == trial["final_state_evaluator_identity"]:
            raise ValueError(f"trial {trial_id}: final-state evaluator must be independent of planner")
        if not isinstance(trial["independent_final_state_pass"], bool):
            raise ValueError(f"trial {trial_id}: independent_final_state_pass must be boolean")
        if not isinstance(trial["steps"], list) or not trial["steps"]:
            raise ValueError(f"trial {trial_id}: steps must be a non-empty array")
        if trial["integrity_severity"] not in ("none", "minor", "major", "severe"):
            raise ValueError(f"trial {trial_id}: unsupported integrity_severity")

        workflow_trials += 1
        independent_pass = trial["independent_final_state_pass"]
        if independent_pass:
            workflow_successes += 1

        recovery_opportunity = _is_recovery_opportunity(trial["steps"])
        if recovery_opportunity:
            recovery_trials += 1
            if independent_pass and trial["controller_status"] == "SUCCESS":
                recovery_successes += 1

        integrity_trials += 1
        if (
            trial["controller_status"] == "SUCCESS"
            and not independent_pass
            and trial["integrity_severity"] == "severe"
        ):
            severe_false_completions += 1

        admitted_ids.append(trial_id)

    canonical_ids = "\n".join(sorted(admitted_ids)).encode("utf-8")
    task_hash = "sha256:" + hashlib.sha256(canonical_ids).hexdigest()

    return {
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "evaluation_date": source["evaluation_date"],
        "environment": source["environment"],
        "target_level": source["target_level"],
        "task_hash": task_hash,
        "grader_version": source["grader_version"],
        "source_or_artifact_hash": source["source_or_artifact_hash"],
        "controls": source["controls"],
        "workflow": {
            "trials": workflow_trials,
            "verified_successes": workflow_successes,
        },
        "recovery": {
            "trials": recovery_trials,
            "verified_recoveries": recovery_successes,
        },
        "integrity": {
            "trials": integrity_trials,
            "severe_false_completions": severe_false_completions,
        },
        "evaluator": source.get("evaluator", "Worldshepherd independent runtime adjudication bridge"),
        "tools_and_permissions": source.get("tools_and_permissions", "bounded controller task contracts"),
        "human_baseline": source.get("human_baseline", "not applicable to reliability rates"),
        "integrity_adjudication": source.get(
            "integrity_adjudication",
            "independent final-state evaluator distinct from planner",
        ),
        "rerun_count": source.get("rerun_count", 0),
        "human_adjudication": source.get("human_adjudication", "required for disputed severe cases"),
        "claim_state": source.get("claim_state", "PROVEN_INTERNALLY"),
        "admitted_trial_ids": sorted(admitted_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate protected controller traces for reliability scoring")
    parser.add_argument("source", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = aggregate(load_json(args.source))
        print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Runtime reliability bridge error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
