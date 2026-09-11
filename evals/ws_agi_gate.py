#!/usr/bin/env python3
"""Worldshepherd AGI gate evaluator.

Evaluates a JSON result bundle against config/ws_agi_gate_v1.json.
This tool does not measure intelligence itself; it enforces the configured
acceptance thresholds and reports missing/failed evidence explicitly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


OPS = {
    ">=": lambda actual, target: actual >= target,
    "<=": lambda actual, target: actual <= target,
    ">": lambda actual, target: actual > target,
    "<": lambda actual, target: actual < target,
    "==": lambda actual, target: actual == target,
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return data


def validate_evidence(bundle: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    records = bundle.get("evidence", [])
    if not isinstance(records, list):
        return {
            "valid": False,
            "record_count": 0,
            "errors": ["evidence must be an array"],
        }

    errors: List[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"evidence[{index}] must be an object")
            continue
        missing = [field for field in required_fields if record.get(field) in (None, "")]
        if missing:
            errors.append(f"evidence[{index}] missing: {', '.join(missing)}")

    return {
        "valid": len(errors) == 0 and len(records) > 0,
        "record_count": len(records),
        "errors": errors,
    }


def evaluate_level(
    metrics: Dict[str, Any], required_metrics: Dict[str, Any], level: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    checks: List[Dict[str, Any]] = []
    passed_all = True

    for name, level_rules in required_metrics.items():
        rule = level_rules[level]
        operator = rule["operator"]
        target = rule["value"]
        actual = metrics.get(name)

        if actual is None:
            checks.append(
                {
                    "metric": name,
                    "status": "UNKNOWN",
                    "actual": None,
                    "operator": operator,
                    "target": target,
                }
            )
            passed_all = False
            continue

        if operator not in OPS:
            raise ValueError(f"Unsupported operator {operator!r} for {name}")

        try:
            passed = bool(OPS[operator](actual, target))
        except TypeError as exc:
            raise ValueError(
                f"Metric {name!r} value {actual!r} is not comparable with {target!r}"
            ) from exc

        checks.append(
            {
                "metric": name,
                "status": "PASS" if passed else "FAIL",
                "actual": actual,
                "operator": operator,
                "target": target,
            }
        )
        passed_all = passed_all and passed

    return passed_all, checks


def determine_state(
    candidate_pass: bool,
    verified_pass: bool,
    evidence_valid: bool,
) -> str:
    if verified_pass and evidence_valid:
        return "AGI_VERIFIED"
    if candidate_pass and evidence_valid:
        return "AGI_CANDIDATE"
    return "BELOW_AGI"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a Worldshepherd AGI result bundle")
    parser.add_argument("results", type=Path, help="JSON result bundle containing metrics and evidence")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/ws_agi_gate_v1.json"),
        help="AGI gate configuration JSON",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON",
    )
    args = parser.parse_args()

    try:
        config = load_json(args.config)
        bundle = load_json(args.results)
        metrics = bundle.get("metrics", {})
        if not isinstance(metrics, dict):
            raise ValueError("results.metrics must be an object")

        evidence = validate_evidence(bundle, config.get("evidence_required_fields", []))
        candidate_pass, candidate_checks = evaluate_level(
            metrics, config["required_metrics"], "candidate"
        )
        verified_pass, verified_checks = evaluate_level(
            metrics, config["required_metrics"], "verified"
        )

        state = determine_state(candidate_pass, verified_pass, evidence["valid"])
        output = {
            "schema": "WS-AGI-GATE-EVALUATION-V1.0",
            "gate_config_schema": config.get("schema"),
            "system_id": bundle.get("system_id", "UNKNOWN"),
            "intelligence_state": state,
            "candidate_gate": {
                "passed": candidate_pass and evidence["valid"],
                "metric_thresholds_passed": candidate_pass,
                "checks": candidate_checks,
            },
            "verified_gate": {
                "passed": verified_pass and evidence["valid"],
                "metric_thresholds_passed": verified_pass,
                "checks": verified_checks,
            },
            "evidence": evidence,
            "deployment_state_changed": False,
            "claims_boundary": config.get("claims_boundary"),
        }

        indent = 2 if args.pretty else None
        print(json.dumps(output, indent=indent, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"AGI gate evaluation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
