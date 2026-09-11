#!/usr/bin/env python3
"""Worldshepherd AGI gate evaluator.

Evaluates a JSON result bundle against config/ws_agi_gate_v1.json.
This tool does not measure intelligence itself; it enforces configured
acceptance thresholds, metric validity, and metric-to-evidence provenance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple


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


def validate_evidence(
    bundle: Dict[str, Any],
    required_fields: List[str],
    required_metrics: Optional[List[str]] = None,
    allowed_claim_states: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Validate evidence records and metric-level provenance coverage."""

    records = bundle.get("evidence", [])
    if not isinstance(records, list):
        return {
            "valid": False,
            "record_count": 0,
            "errors": ["evidence must be an array"],
            "metric_coverage": {},
        }

    errors: List[str] = []
    seen_ids = set()
    required_metric_set = set(required_metrics or [])
    coverage: Dict[str, List[str]] = {name: [] for name in required_metric_set}

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"evidence[{index}] must be an object")
            continue

        missing = [field for field in required_fields if record.get(field) in (None, "")]
        if missing:
            errors.append(f"evidence[{index}] missing: {', '.join(missing)}")

        evidence_id = record.get("evidence_id")
        if evidence_id not in (None, ""):
            if evidence_id in seen_ids:
                errors.append(f"duplicate evidence_id: {evidence_id}")
            seen_ids.add(evidence_id)

        metric_names = record.get("metric_names")
        if metric_names is not None:
            if not isinstance(metric_names, list) or not metric_names:
                errors.append(f"evidence[{index}].metric_names must be a non-empty array")
            else:
                for metric_name in metric_names:
                    if not isinstance(metric_name, str) or not metric_name:
                        errors.append(f"evidence[{index}] contains invalid metric name")
                        continue
                    if required_metric_set and metric_name not in required_metric_set:
                        errors.append(
                            f"evidence[{index}] references unknown metric: {metric_name}"
                        )
                        continue
                    coverage.setdefault(metric_name, []).append(str(evidence_id))

        claim_state = record.get("claim_state")
        if (
            allowed_claim_states
            and claim_state not in (None, "")
            and claim_state not in allowed_claim_states
        ):
            errors.append(f"evidence[{index}] invalid claim_state: {claim_state}")

    if required_metric_set:
        missing_coverage = sorted(name for name in required_metric_set if not coverage.get(name))
        if missing_coverage:
            errors.append(
                "required metrics without evidence mapping: " + ", ".join(missing_coverage)
            )

    return {
        "valid": len(errors) == 0 and len(records) > 0,
        "record_count": len(records),
        "errors": errors,
        "metric_coverage": {name: coverage.get(name, []) for name in sorted(coverage)},
    }


def evaluate_level(
    metrics: Dict[str, Any],
    required_metrics: Dict[str, Any],
    level: str,
    metric_validity: Optional[Mapping[str, Any]] = None,
) -> Tuple[bool, List[Dict[str, Any]]]:
    checks: List[Dict[str, Any]] = []
    passed_all = True
    validity = metric_validity or {}

    for name, level_rules in required_metrics.items():
        rule = level_rules[level]
        operator = rule["operator"]
        target = rule["value"]
        actual = metrics.get(name)

        validity_record = validity.get(name)
        if isinstance(validity_record, dict) and validity_record.get("valid") is False:
            checks.append(
                {
                    "metric": name,
                    "status": "BLOCKED",
                    "actual": actual,
                    "operator": operator,
                    "target": target,
                    "validity_reason": validity_record.get("reason", "metric invalidated"),
                }
            )
            passed_all = False
            continue

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
    parser.add_argument("--pretty", action="store_true", help="Pretty-print output JSON")
    args = parser.parse_args()

    try:
        config = load_json(args.config)
        bundle = load_json(args.results)
        metrics = bundle.get("metrics", {})
        metric_validity = bundle.get("metric_validity", {})
        if not isinstance(metrics, dict):
            raise ValueError("results.metrics must be an object")
        if not isinstance(metric_validity, dict):
            raise ValueError("results.metric_validity must be an object when present")

        required_metrics = config["required_metrics"]
        evidence = validate_evidence(
            bundle,
            config.get("evidence_required_fields", []),
            required_metrics=list(required_metrics),
            allowed_claim_states=config.get("claim_states", []),
        )
        candidate_pass, candidate_checks = evaluate_level(
            metrics, required_metrics, "candidate", metric_validity
        )
        verified_pass, verified_checks = evaluate_level(
            metrics, required_metrics, "verified", metric_validity
        )

        state = determine_state(candidate_pass, verified_pass, evidence["valid"])
        output = {
            "schema": "WS-AGI-GATE-EVALUATION-V1.1",
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
            "metric_validity": metric_validity,
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
