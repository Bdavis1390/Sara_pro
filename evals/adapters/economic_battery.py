#!/usr/bin/env python3
"""Normalize protected professional-work evaluations into Worldshepherd AGI metrics.

This adapter compares system task scores with pre-established skilled-human baselines.
It fails closed when required domains or evaluation controls are missing. It does not
create tasks, obtain hidden answers, or alter the evaluated system.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

METRICS = [
    "economic_battery_pct_of_skilled_human",
    "economic_domain_count",
    "critical_domain_floor_pct_of_skilled_human",
]


def _load(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return data


def _required(record: Dict[str, Any], names: Iterable[str], prefix: str) -> None:
    missing = [name for name in names if record.get(name) in (None, "")]
    if missing:
        raise ValueError(f"{prefix} missing required fields: {', '.join(missing)}")


def _ratio(domain: Dict[str, Any], cap: float) -> float:
    system_score = float(domain["system_score"])
    human_score = float(domain["human_baseline_score"])
    direction = domain.get("score_direction", "higher_is_better")
    if direction == "higher_is_better":
        if human_score <= 0:
            raise ValueError("human_baseline_score must be positive for higher_is_better")
        raw = 100.0 * system_score / human_score
    elif direction == "lower_is_better":
        if system_score <= 0 or human_score < 0:
            raise ValueError("scores must be valid and system_score positive for lower_is_better")
        raw = 100.0 * human_score / system_score
    else:
        raise ValueError(f"unsupported score_direction: {direction}")
    return max(0.0, min(float(cap), raw))


def normalize(source: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    _required(
        source,
        [
            "system_id",
            "system_version",
            "evaluation_date",
            "environment",
            "target_level",
            "task_hash",
            "grader_version",
            "source_or_artifact_hash",
            "controls",
            "domains",
        ],
        "economic source",
    )
    level = source["target_level"]
    if level not in ("candidate", "verified"):
        raise ValueError("target_level must be candidate or verified")
    level_cfg = config[level]
    required_domains = list(level_cfg["required_domains"])
    critical_domains = set(config.get("critical_domains", []))
    required_controls = config.get("required_controls", {})
    controls = source["controls"]
    if not isinstance(controls, dict):
        raise ValueError("controls must be an object")
    if not isinstance(source["domains"], list) or not source["domains"]:
        raise ValueError("domains must be a non-empty array")

    control_errors = [
        f"control {name}={controls.get(name)!r}, required {expected!r}"
        for name, expected in required_controls.items()
        if controls.get(name) != expected
    ]

    by_domain: Dict[str, Dict[str, Any]] = {}
    structural_errors: List[str] = []
    for index, domain in enumerate(source["domains"]):
        if not isinstance(domain, dict):
            structural_errors.append(f"domains[{index}] must be an object")
            continue
        try:
            _required(
                domain,
                [
                    "domain_id",
                    "system_score",
                    "human_baseline_score",
                    "task_count",
                    "human_baseline_n",
                ],
                f"domains[{index}]",
            )
        except ValueError as exc:
            structural_errors.append(str(exc))
            continue
        domain_id = str(domain["domain_id"])
        if domain_id in by_domain:
            structural_errors.append(f"duplicate domain_id: {domain_id}")
            continue
        by_domain[domain_id] = domain

    missing_domains = [domain_id for domain_id in required_domains if domain_id not in by_domain]
    domain_results: Dict[str, Dict[str, Any]] = {}
    domain_errors: List[str] = []
    ratios: List[float] = []
    critical_ratios: List[float] = []

    for domain_id in required_domains:
        domain = by_domain.get(domain_id)
        if domain is None:
            continue
        reasons = []
        if int(domain["task_count"]) < int(level_cfg["min_tasks_per_domain"]):
            reasons.append(
                f"task_count {domain['task_count']} < {level_cfg['min_tasks_per_domain']}"
            )
        if int(domain["human_baseline_n"]) < int(level_cfg["min_human_baseline_n"]):
            reasons.append(
                "human_baseline_n "
                f"{domain['human_baseline_n']} < {level_cfg['min_human_baseline_n']}"
            )
        try:
            ratio = _ratio(domain, float(config.get("ratio_cap_pct", 120.0)))
        except (TypeError, ValueError) as exc:
            reasons.append(str(exc))
            ratio = None

        valid = not reasons
        if reasons:
            domain_errors.extend(f"{domain_id}: {reason}" for reason in reasons)
        domain_results[domain_id] = {
            "valid": valid,
            "ratio_pct_of_skilled_human": ratio,
            "task_count": domain.get("task_count"),
            "human_baseline_n": domain.get("human_baseline_n"),
            "critical": domain_id in critical_domains,
            "reasons": reasons,
        }
        if valid and ratio is not None:
            ratios.append(ratio)
            if domain_id in critical_domains:
                critical_ratios.append(ratio)

    full_battery_valid = not (
        control_errors or structural_errors or missing_domains or domain_errors
    )
    tested_required_count = sum(
        1 for domain_id in required_domains if domain_results.get(domain_id, {}).get("valid")
    )

    battery_score = statistics.fmean(ratios) if ratios else None
    critical_floor = min(critical_ratios) if critical_ratios else None
    metrics = {
        "economic_battery_pct_of_skilled_human": battery_score,
        "economic_domain_count": tested_required_count,
        "critical_domain_floor_pct_of_skilled_human": critical_floor,
    }

    common_reasons = control_errors + structural_errors
    if missing_domains:
        common_reasons.append("missing required domains: " + ", ".join(missing_domains))
    common_reasons.extend(domain_errors)
    reason_text = "; ".join(common_reasons) if common_reasons else "all protected battery controls passed"

    metric_validity = {
        "economic_battery_pct_of_skilled_human": {
            "valid": full_battery_valid and battery_score is not None,
            "reason": reason_text,
        },
        "economic_domain_count": {
            "valid": not structural_errors,
            "reason": "; ".join(structural_errors) if structural_errors else "domain records structurally valid",
        },
        "critical_domain_floor_pct_of_skilled_human": {
            "valid": full_battery_valid and critical_floor is not None,
            "reason": reason_text,
        },
    }

    evidence = [
        {
            "evidence_id": f"economic-battery:{source['system_id']}:{level}:{source['evaluation_date']}",
            "metric_names": METRICS,
            "system_id": source["system_id"],
            "system_version": source["system_version"],
            "evaluator": source.get("evaluator", "Worldshepherd protected economic battery"),
            "benchmark_version": config["schema"],
            "evaluation_date": source["evaluation_date"],
            "environment": source["environment"],
            "tools_and_permissions": source.get("tools_and_permissions", "recorded by harness"),
            "trial_count": sum(
                int(domain.get("task_count", 0)) for domain in by_domain.values()
            ),
            "score": {
                "battery_pct_of_skilled_human": battery_score,
                "valid_required_domains": tested_required_count,
                "critical_floor_pct": critical_floor,
            },
            "human_baseline": source.get(
                "human_baseline", "domain-specific skilled-human reference panels"
            ),
            "contamination_controls": controls,
            "integrity_adjudication": source.get(
                "integrity_adjudication", "protected holdout and independent final-state grading"
            ),
            "source_or_artifact_hash": source["source_or_artifact_hash"],
            "task_hash": source["task_hash"],
            "grader_version": source["grader_version"],
            "rerun_count": source.get("rerun_count", 0),
            "human_adjudication": source.get(
                "human_adjudication", "independent final-state grading required"
            ),
            "claim_state": source.get("claim_state", "PROVEN_INTERNALLY"),
        }
    ]

    return {
        "schema": "WS-ECONOMIC-BATTERY-ADAPTER-V1.0",
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "target_level": level,
        "metrics": metrics,
        "metric_validity": metric_validity,
        "evidence": evidence,
        "domain_results": domain_results,
        "missing_required_domains": missing_domains,
        "control_errors": control_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize protected economic-work battery JSON")
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--config", type=Path, default=Path("config/ws_economic_battery_v1.json")
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        output = normalize(_load(args.source), _load(args.config))
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Economic battery adapter error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
