#!/usr/bin/env python3
"""Rank AGI capability lanes that most need evidence or bounded improvement.

This selector is advisory. It never changes permissions, deployment state, models,
repository contents, or acceptance thresholds. BLOCKED/UNKNOWN evidence is prioritized
before ordinary metric failures so the program does not optimize against missing data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping


STATUS_PRIORITY = {"BLOCKED": 4, "UNKNOWN": 3, "FAIL": 2, "PASS": 0}
INTERVENTION_FAMILIES = {
    "novel_generalization": "generalization_and_novel_environment_reasoning",
    "long_horizon_autonomy": "planning_memory_checkpointing_and_recovery",
    "economic_breadth": "domain_tooling_and_professional_work_coverage",
    "cross_domain_transfer": "verified_experience_abstraction_and_transfer",
    "tool_workflow_reliability": "ensemble_planning_tool_contracts_and_verification",
    "self_correction": "error_diagnosis_repair_and_calibration",
    "evidence_integrity": "independent_adjudication_provenance_and_false_completion_control",
}


def load_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("evaluation must be a JSON object")
    return value


def _metric_gap(metric: Mapping[str, Any]) -> float:
    if metric.get("status") != "FAIL":
        return 0.0
    actual = metric.get("actual")
    target = metric.get("target")
    if isinstance(actual, bool) or isinstance(target, bool):
        return 0.0
    if not isinstance(actual, (int, float)) or not isinstance(target, (int, float)):
        return 0.0
    scale = max(abs(float(target)), 1.0)
    return abs(float(actual) - float(target)) / scale


def rank_lanes(evaluation: Dict[str, Any], level: str = "candidate") -> Dict[str, Any]:
    if level not in ("candidate", "verified"):
        raise ValueError("level must be candidate or verified")
    gate = evaluation.get(f"{level}_gate")
    if not isinstance(gate, dict):
        raise ValueError(f"evaluation missing {level}_gate")
    lanes = gate.get("lanes")
    if not isinstance(lanes, dict) or not lanes:
        raise ValueError("evaluation gate is missing lane summaries")

    ranked: List[Dict[str, Any]] = []
    for lane_name, lane in lanes.items():
        if not isinstance(lane, dict):
            continue
        status = lane.get("status", "UNKNOWN")
        metrics = lane.get("metrics", [])
        if not isinstance(metrics, list):
            metrics = []
        gap = max((_metric_gap(metric) for metric in metrics if isinstance(metric, dict)), default=0.0)
        priority = STATUS_PRIORITY.get(status, 5)
        ranked.append(
            {
                "lane": lane_name,
                "status": status,
                "priority_class": priority,
                "normalized_failed_metric_gap": round(gap, 6),
                "intervention_family": INTERVENTION_FAMILIES.get(lane_name, "measurement_and_bounded_architecture_review"),
                "reason": (
                    "measurement is blocked and must be made valid before optimization"
                    if status == "BLOCKED"
                    else "required evidence is unknown; measure before claiming improvement"
                    if status == "UNKNOWN"
                    else "measured capability is below the configured threshold"
                    if status == "FAIL"
                    else "lane currently passes this gate level"
                ),
            }
        )

    ranked.sort(
        key=lambda row: (
            row["priority_class"],
            row["normalized_failed_metric_gap"],
            row["lane"],
        ),
        reverse=True,
    )
    actionable = [row for row in ranked if row["status"] != "PASS"]
    return {
        "schema": "WS-AGI-WEAKEST-LANE-V1.0",
        "system_id": evaluation.get("system_id", "UNKNOWN"),
        "target_level": level,
        "intelligence_state": evaluation.get("intelligence_state", "UNKNOWN"),
        "top_priority": actionable[0] if actionable else None,
        "ranked_nonpassing_lanes": actionable,
        "policy": "advisory_only_no_automatic_model_or_deployment_changes",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank nonpassing Worldshepherd AGI lanes")
    parser.add_argument("evaluation", type=Path)
    parser.add_argument("--level", choices=["candidate", "verified"], default="candidate")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = rank_lanes(load_json(args.evaluation), args.level)
        print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Weakest lane error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
