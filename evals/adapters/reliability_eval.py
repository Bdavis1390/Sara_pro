#!/usr/bin/env python3
"""Normalize protected reliability evaluations into Worldshepherd AGI metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

METRICS = [
    "tool_workflow_success_pct",
    "workflow_trial_count",
    "self_correction_success_pct",
    "recovery_trial_count",
    "severe_false_completion_rate_pct",
    "integrity_trial_count",
]


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


def rate(successes: int, trials: int) -> float:
    if trials <= 0 or successes < 0 or successes > trials:
        raise ValueError("invalid success/trial counts")
    return 100.0 * successes / trials


def normalize(source: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    required = [
        "system_id", "system_version", "evaluation_date", "environment",
        "target_level", "task_hash", "grader_version", "source_or_artifact_hash",
        "controls", "workflow", "recovery", "integrity",
    ]
    missing = [name for name in required if source.get(name) in (None, "")]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))

    level = source["target_level"]
    if level not in ("candidate", "verified"):
        raise ValueError("target_level must be candidate or verified")
    controls = source["controls"]
    if not isinstance(controls, dict):
        raise ValueError("controls must be an object")

    workflow = source["workflow"]
    recovery = source["recovery"]
    integrity = source["integrity"]
    for label, record in (("workflow", workflow), ("recovery", recovery), ("integrity", integrity)):
        if not isinstance(record, dict):
            raise ValueError(f"{label} must be an object")

    workflow_trials = int(workflow["trials"])
    workflow_successes = int(workflow["verified_successes"])
    recovery_trials = int(recovery["trials"])
    recovery_successes = int(recovery["verified_recoveries"])
    integrity_trials = int(integrity["trials"])
    severe_false = int(integrity["severe_false_completions"])

    workflow_rate = rate(workflow_successes, workflow_trials)
    recovery_rate = rate(recovery_successes, recovery_trials)
    if integrity_trials <= 0 or severe_false < 0 or severe_false > integrity_trials:
        raise ValueError("invalid integrity counts")
    false_rate = 100.0 * severe_false / integrity_trials

    control_errors = [
        f"control {name}={controls.get(name)!r}, required {expected!r}"
        for name, expected in config.get("required_controls", {}).items()
        if controls.get(name) != expected
    ]
    level_cfg = config[level]
    sample_errors = []
    if workflow_trials < int(level_cfg["min_workflow_trials"]):
        sample_errors.append("workflow sample too small")
    if recovery_trials < int(level_cfg["min_recovery_trials"]):
        sample_errors.append("recovery sample too small")
    if integrity_trials < int(level_cfg["min_integrity_trials"]):
        sample_errors.append("integrity sample too small")

    errors = control_errors + sample_errors
    valid = not errors
    reason = "; ".join(errors) if errors else "protected controls and sample sizes passed"

    metrics = {
        "tool_workflow_success_pct": workflow_rate,
        "workflow_trial_count": workflow_trials,
        "self_correction_success_pct": recovery_rate,
        "recovery_trial_count": recovery_trials,
        "severe_false_completion_rate_pct": false_rate,
        "integrity_trial_count": integrity_trials,
    }
    evidence = [{
        "evidence_id": f"reliability:{source['system_id']}:{level}:{source['evaluation_date']}",
        "metric_names": METRICS,
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "evaluator": source.get("evaluator", "Worldshepherd reliability evaluator"),
        "benchmark_version": config["schema"],
        "evaluation_date": source["evaluation_date"],
        "environment": source["environment"],
        "tools_and_permissions": source.get("tools_and_permissions", "recorded by harness"),
        "trial_count": workflow_trials + recovery_trials + integrity_trials,
        "score": metrics,
        "human_baseline": source.get("human_baseline", "not applicable to rate metrics"),
        "contamination_controls": controls,
        "integrity_adjudication": source.get("integrity_adjudication", "independent result verification"),
        "source_or_artifact_hash": source["source_or_artifact_hash"],
        "task_hash": source["task_hash"],
        "grader_version": source["grader_version"],
        "rerun_count": source.get("rerun_count", 0),
        "human_adjudication": source.get("human_adjudication", "independent adjudication where needed"),
        "claim_state": source.get("claim_state", "PROVEN_INTERNALLY"),
    }]
    return {
        "schema": "WS-RELIABILITY-ADAPTER-V1.0",
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "target_level": level,
        "metrics": metrics,
        "metric_validity": {name: {"valid": valid, "reason": reason} for name in METRICS},
        "evidence": evidence,
        "control_errors": control_errors,
        "sample_errors": sample_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize reliability evaluation JSON")
    parser.add_argument("source", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/ws_reliability_eval_v1.json"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = normalize(load_json(args.source), load_json(args.config))
        print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Reliability adapter error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
