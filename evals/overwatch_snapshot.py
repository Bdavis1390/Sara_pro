#!/usr/bin/env python3
"""Render a compact OVERWATCH snapshot from Worldshepherd AGI gate output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


def build_snapshot(gate: Dict[str, Any]) -> Dict[str, Any]:
    candidate = gate.get("candidate_gate", {})
    lanes = candidate.get("lanes", {}) if isinstance(candidate, dict) else {}
    if not isinstance(lanes, dict):
        raise ValueError("candidate_gate.lanes must be an object")

    lane_status = {}
    blockers: List[Dict[str, Any]] = []
    for lane_name, lane in lanes.items():
        if not isinstance(lane, dict):
            continue
        status = lane.get("status", "UNKNOWN")
        lane_status[lane_name] = status
        for metric in lane.get("metrics", []):
            if not isinstance(metric, dict):
                continue
            if metric.get("status") != "PASS":
                blockers.append({
                    "lane": lane_name,
                    "metric": metric.get("metric"),
                    "status": metric.get("status", "UNKNOWN"),
                    "actual": metric.get("actual"),
                    "target": metric.get("target"),
                })

    evidence = gate.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
    prime = gate.get("prime_policy", {})
    if not isinstance(prime, dict):
        prime = {}

    alerts = []
    if gate.get("intelligence_state") == "BELOW_AGI":
        alerts.append("INTELLIGENCE_GATE_NOT_CLEARED")
    if not evidence.get("valid", False):
        alerts.append("EVIDENCE_INVALID_OR_INCOMPLETE")
    if prime.get("deployment_state_changed"):
        alerts.append("DEPLOYMENT_STATE_CHANGE_DETECTED")
    if any(item.get("status") == "BLOCKED" for item in blockers):
        alerts.append("INVALIDATED_MEASUREMENT_PRESENT")
    if any(item.get("status") == "UNKNOWN" for item in blockers):
        alerts.append("REQUIRED_METRIC_UNKNOWN")

    return {
        "schema": "WS-OVERWATCH-AGI-SNAPSHOT-V1.0",
        "system_id": gate.get("system_id", "UNKNOWN"),
        "intelligence_state": gate.get("intelligence_state", "UNKNOWN"),
        "deployment_state": prime.get("deployment_state_output", prime.get("deployment_state_input", "UNKNOWN")),
        "candidate_gate_passed": bool(candidate.get("passed", False)) if isinstance(candidate, dict) else False,
        "lane_status": lane_status,
        "blockers": blockers,
        "evidence_valid": bool(evidence.get("valid", False)),
        "evidence_record_count": evidence.get("record_count", 0),
        "evidence_errors": evidence.get("errors", []),
        "alerts": alerts,
    }


def render_markdown(snapshot: Dict[str, Any]) -> str:
    lines = [
        f"# OVERWATCH AGI Snapshot — {snapshot['system_id']}",
        "",
        f"- Intelligence: `{snapshot['intelligence_state']}`",
        f"- Deployment: `{snapshot['deployment_state']}`",
        f"- Candidate gate passed: `{str(snapshot['candidate_gate_passed']).lower()}`",
        f"- Evidence valid: `{str(snapshot['evidence_valid']).lower()}`",
        "",
        "## Lanes",
    ]
    for lane, status in snapshot["lane_status"].items():
        lines.append(f"- `{lane}`: **{status}**")
    lines.extend(["", "## Blockers"])
    if snapshot["blockers"]:
        for item in snapshot["blockers"]:
            lines.append(
                f"- `{item['lane']}` / `{item['metric']}`: {item['status']} "
                f"(actual={item['actual']}, target={item['target']})"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Alerts"])
    if snapshot["alerts"]:
        for alert in snapshot["alerts"]:
            lines.append(f"- `{alert}`")
    else:
        lines.append("- None")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render OVERWATCH AGI gate snapshot")
    parser.add_argument("gate_output", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    try:
        snapshot = build_snapshot(load_json(args.gate_output))
        if args.format == "markdown":
            print(render_markdown(snapshot))
        else:
            print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"OVERWATCH snapshot error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
