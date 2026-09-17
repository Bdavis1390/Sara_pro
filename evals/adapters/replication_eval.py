#!/usr/bin/env python3
"""Normalize independent replication records into Worldshepherd AGI gate metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

METRICS = ["independent_replications", "unresolved_evidence_integrity_failures"]


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


def normalize(source: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    required = [
        "system_id", "system_version", "evaluation_date", "environment",
        "target_level", "task_hash", "grader_version", "source_or_artifact_hash",
        "replications",
    ]
    missing = [name for name in required if source.get(name) in (None, "")]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))

    level = source["target_level"]
    if level not in ("candidate", "verified"):
        raise ValueError("target_level must be candidate or verified")
    if not isinstance(source["replications"], list):
        raise ValueError("replications must be an array")

    level_cfg = config[level]
    accepted_states = set(level_cfg["accepted_states"])
    required_controls = config.get("required_controls", {})
    distinctness_fields = list(config.get("distinctness_fields", []))

    admitted: List[Dict[str, Any]] = []
    errors: List[str] = []
    seen: set[Tuple[Any, ...]] = set()
    unresolved = 0

    for index, record in enumerate(source["replications"]):
        if not isinstance(record, dict):
            errors.append(f"replications[{index}] must be an object")
            continue
        req = [
            "replication_id", "evaluator_org", "infrastructure_id", "result_state",
            "controls", "unresolved_integrity_failures", "artifact_hash",
        ]
        missing_record = [name for name in req if record.get(name) in (None, "")]
        if missing_record:
            errors.append(f"replications[{index}] missing: {', '.join(missing_record)}")
            continue
        controls = record["controls"]
        if not isinstance(controls, dict):
            errors.append(f"replications[{index}].controls must be an object")
            continue
        control_errors = [
            name for name, expected in required_controls.items()
            if controls.get(name) != expected
        ]
        if control_errors:
            errors.append(
                f"replications[{index}] failed controls: {', '.join(control_errors)}"
            )
            continue
        if record["result_state"] not in accepted_states:
            continue
        key = tuple(record.get(field) for field in distinctness_fields)
        if key in seen:
            errors.append(f"replications[{index}] duplicate independence key: {key}")
            continue
        seen.add(key)
        failures = int(record["unresolved_integrity_failures"])
        if failures < 0:
            errors.append(f"replications[{index}] negative integrity failure count")
            continue
        unresolved += failures
        admitted.append(record)

    count = len(admitted)
    metrics = {
        "independent_replications": count,
        "unresolved_evidence_integrity_failures": unresolved,
    }
    validity_reason = "; ".join(errors) if errors else "replication records structurally valid"
    validity = {name: {"valid": not errors, "reason": validity_reason} for name in METRICS}

    evidence = [{
        "evidence_id": f"replication-summary:{source['system_id']}:{level}:{source['evaluation_date']}",
        "metric_names": METRICS,
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "evaluator": source.get("evaluator", "Worldshepherd replication aggregator"),
        "benchmark_version": config["schema"],
        "evaluation_date": source["evaluation_date"],
        "environment": source["environment"],
        "tools_and_permissions": source.get("tools_and_permissions", "replication evidence ingestion only"),
        "trial_count": count,
        "score": metrics,
        "human_baseline": source.get("human_baseline", "not applicable to replication count"),
        "contamination_controls": required_controls,
        "integrity_adjudication": {
            "unresolved_failures": unresolved,
            "record_errors": errors,
        },
        "source_or_artifact_hash": source["source_or_artifact_hash"],
        "task_hash": source["task_hash"],
        "grader_version": source["grader_version"],
        "rerun_count": source.get("rerun_count", 0),
        "human_adjudication": source.get("human_adjudication", "replication records reviewed before admission"),
        "claim_state": source.get("claim_state", "PROVEN_INTERNALLY"),
    }]

    return {
        "schema": "WS-REPLICATION-ADAPTER-V1.0",
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "target_level": level,
        "metrics": metrics,
        "metric_validity": validity,
        "evidence": evidence,
        "admitted_replication_ids": [record["replication_id"] for record in admitted],
        "record_errors": errors,
        "required_replications_for_level": int(level_cfg["min_independent_replications"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize independent replication records")
    parser.add_argument("source", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/ws_replication_eval_v1.json"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = normalize(load_json(args.source), load_json(args.config))
        print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Replication adapter error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
