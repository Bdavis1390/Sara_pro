#!/usr/bin/env python3
"""Normalize held-out cross-domain transfer evaluations for the Worldshepherd AGI gate.

The adapter measures transfer from in-domain reference performance to held-out task
families. It does not train or modify the evaluated system. Promotion use is blocked
when protected-holdout controls are incomplete or the requested sample size is not met.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

METRICS = ["heldout_transfer_ratio_pct", "transfer_pair_count"]


def _load(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return data


def _required(record: Dict[str, Any], names: Iterable[str], prefix: str) -> None:
    missing = [name for name in names if record.get(name) in (None, "")]
    if missing:
        raise ValueError(f"{prefix} missing required fields: {', '.join(missing)}")


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
            "pairs",
        ],
        "transfer source",
    )
    level = source["target_level"]
    if level not in ("candidate", "verified"):
        raise ValueError("target_level must be candidate or verified")
    if not isinstance(source["pairs"], list) or not source["pairs"]:
        raise ValueError("pairs must be a non-empty array")
    controls = source["controls"]
    if not isinstance(controls, dict):
        raise ValueError("controls must be an object")

    required_controls = config.get("required_controls", {})
    control_errors = [
        f"control {name}={controls.get(name)!r}, required {expected!r}"
        for name, expected in required_controls.items()
        if controls.get(name) != expected
    ]

    pair_errors: List[str] = []
    seen_ids = set()
    admitted: List[Dict[str, Any]] = []
    for index, pair in enumerate(source["pairs"]):
        if not isinstance(pair, dict):
            pair_errors.append(f"pairs[{index}] must be an object")
            continue
        try:
            _required(
                pair,
                ["pair_id", "in_domain_score", "heldout_score", "verified"],
                f"pairs[{index}]",
            )
        except ValueError as exc:
            pair_errors.append(str(exc))
            continue
        pair_id = str(pair["pair_id"])
        if pair_id in seen_ids:
            pair_errors.append(f"duplicate pair_id: {pair_id}")
            continue
        seen_ids.add(pair_id)
        if pair["verified"] is not True:
            continue
        try:
            in_domain = float(pair["in_domain_score"])
            heldout = float(pair["heldout_score"])
        except (TypeError, ValueError):
            pair_errors.append(f"{pair_id}: scores must be numeric")
            continue
        if not (0.0 < in_domain <= 100.0):
            pair_errors.append(f"{pair_id}: in_domain_score must be in (0, 100]")
            continue
        if not (0.0 <= heldout <= 100.0):
            pair_errors.append(f"{pair_id}: heldout_score must be in [0, 100]")
            continue
        admitted.append({"pair_id": pair_id, "in_domain": in_domain, "heldout": heldout})

    pair_count = len(admitted)
    min_pairs = int(config[level]["min_transfer_pairs"])
    total_in = sum(item["in_domain"] for item in admitted)
    total_out = sum(item["heldout"] for item in admitted)
    raw_ratio = (100.0 * total_out / total_in) if total_in > 0 else None
    ratio = (
        min(float(config.get("ratio_cap_pct", 120.0)), max(0.0, raw_ratio))
        if raw_ratio is not None
        else None
    )

    validity_reasons = list(control_errors) + list(pair_errors)
    if pair_count < min_pairs:
        validity_reasons.append(f"verified transfer pairs {pair_count} < required {min_pairs}")
    valid = not validity_reasons and ratio is not None
    reason = "; ".join(validity_reasons) if validity_reasons else "protected transfer controls passed"

    evidence = [{
        "evidence_id": f"transfer:{source['system_id']}:{level}:{source['evaluation_date']}",
        "metric_names": METRICS,
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "evaluator": source.get("evaluator", "Worldshepherd held-out transfer evaluator"),
        "benchmark_version": config["schema"],
        "evaluation_date": source["evaluation_date"],
        "environment": source["environment"],
        "tools_and_permissions": source.get("tools_and_permissions", "recorded by harness"),
        "trial_count": pair_count,
        "score": {"heldout_transfer_ratio_pct": ratio, "transfer_pair_count": pair_count},
        "human_baseline": source.get("human_baseline", "not applicable; ratio uses system in-domain reference"),
        "contamination_controls": controls,
        "integrity_adjudication": source.get("integrity_adjudication", "independent held-out result verification"),
        "source_or_artifact_hash": source["source_or_artifact_hash"],
        "task_hash": source["task_hash"],
        "grader_version": source["grader_version"],
        "rerun_count": source.get("rerun_count", 0),
        "human_adjudication": source.get("human_adjudication", "required for disputed final-state grading"),
        "claim_state": source.get("claim_state", "PROVEN_INTERNALLY"),
    }]

    return {
        "schema": "WS-TRANSFER-ADAPTER-V1.0",
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "target_level": level,
        "metrics": {
            "heldout_transfer_ratio_pct": ratio,
            "transfer_pair_count": pair_count,
        },
        "metric_validity": {
            "heldout_transfer_ratio_pct": {"valid": valid, "reason": reason},
            "transfer_pair_count": {"valid": not pair_errors, "reason": "; ".join(pair_errors) if pair_errors else "verified pair count structurally valid"},
        },
        "evidence": evidence,
        "control_errors": control_errors,
        "pair_errors": pair_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize Worldshepherd held-out transfer evaluation JSON")
    parser.add_argument("source", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/ws_transfer_eval_v1.json"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        output = normalize(_load(args.source), _load(args.config))
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Transfer adapter error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
