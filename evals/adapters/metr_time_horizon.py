#!/usr/bin/env python3
"""Normalize METR-style time-horizon measurements for the Worldshepherd AGI gate.

The adapter preserves point estimates and confidence intervals while marking a metric
invalid for gate promotion when the supplied source says the estimate exceeds the
suite's reliable range or when the source explicitly flags the measurement as
unreliable/saturated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

HORIZON_FIELDS = {
    "horizon_80pct_hours": "metr_80pct_horizon_hours",
    "horizon_50pct_hours": "metr_50pct_horizon_hours",
}


def _load(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("METR source record must be a JSON object")
    return data


def _required(record: Dict[str, Any], names: Iterable[str], prefix: str = "record") -> None:
    missing = [name for name in names if record.get(name) in (None, "")]
    if missing:
        raise ValueError(f"{prefix} missing required fields: {', '.join(missing)}")


def _canonical_hash(data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def normalize(source: Dict[str, Any]) -> Dict[str, Any]:
    _required(
        source,
        [
            "system_id",
            "system_version",
            "evaluation_date",
            "benchmark_version",
            "environment",
            "source_url",
            "task_hash",
            "grader_version",
            "reliable_max_hours",
        ],
        "METR source",
    )

    reliable_max = float(source["reliable_max_hours"])
    if reliable_max <= 0:
        raise ValueError("reliable_max_hours must be positive")

    metrics: Dict[str, float] = {}
    metric_validity: Dict[str, Dict[str, Any]] = {}
    evidence = []
    source_saturated = bool(source.get("suite_saturation_warning", False))
    explicit_unreliable = set(source.get("unreliable_metrics", []))

    for source_field, metric_name in HORIZON_FIELDS.items():
        raw_value = source.get(source_field)
        if raw_value is None:
            continue
        value = float(raw_value)
        if value < 0:
            raise ValueError(f"{source_field} cannot be negative")
        metrics[metric_name] = value

        reasons = []
        valid = True
        if value > reliable_max:
            valid = False
            reasons.append(
                f"point estimate {value:g}h exceeds source reliable range {reliable_max:g}h"
            )
        if source_field in explicit_unreliable or metric_name in explicit_unreliable:
            valid = False
            reasons.append("source explicitly marks this metric unreliable")
        if source_saturated and source.get("invalidate_on_saturation", True):
            valid = False
            reasons.append("source suite saturation warning is active")

        metric_validity[metric_name] = {
            "valid": valid,
            "reason": "; ".join(reasons) if reasons else "within supplied reliable range",
            "reliable_max_hours": reliable_max,
        }

        ci = None
        ci_map = source.get("confidence_intervals_hours", {})
        if isinstance(ci_map, dict):
            ci = ci_map.get(source_field) or ci_map.get(metric_name)

        evidence.append(
            {
                "evidence_id": f"metr:{source['system_id']}:{metric_name}",
                "metric_names": [metric_name],
                "system_id": source["system_id"],
                "system_version": source["system_version"],
                "evaluator": source.get("evaluator", "METR time-horizon evaluation"),
                "benchmark_version": source["benchmark_version"],
                "evaluation_date": source["evaluation_date"],
                "environment": source["environment"],
                "tools_and_permissions": source.get(
                    "tools_and_permissions", "as specified by time-horizon evaluation"
                ),
                "trial_count": source.get("trial_count", 1),
                "score": value,
                "human_baseline": source.get(
                    "human_baseline", "human expert task-duration estimate"
                ),
                "contamination_controls": source.get(
                    "contamination_controls", "benchmark source controls"
                ),
                "integrity_adjudication": source.get(
                    "integrity_adjudication", "source methodology and adjudication"
                ),
                "source_or_artifact_hash": source.get("source_or_artifact_hash")
                or _canonical_hash(source),
                "task_hash": source["task_hash"],
                "grader_version": source["grader_version"],
                "rerun_count": source.get("rerun_count", 0),
                "human_adjudication": source.get(
                    "human_adjudication", "source evaluator adjudication"
                ),
                "claim_state": source.get("claim_state", "EXTERNALLY_REPLICATED"),
                "source_url": source["source_url"],
                "confidence_interval_hours": ci,
                "suite_domains": source.get("suite_domains", []),
                "reliable_max_hours": reliable_max,
                "suite_saturation_warning": source_saturated,
            }
        )

    return {
        "schema": "WS-METR-TIME-HORIZON-ADAPTER-V1.0",
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "metrics": metrics,
        "metric_validity": metric_validity,
        "evidence": evidence,
        "adapter_notes": [
            "Point estimates are retained even when blocked from gate promotion.",
            "Measurements beyond the source-declared reliable range fail closed.",
            "Suite saturation can invalidate gate use without deleting the measurement.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize METR-style horizon JSON")
    parser.add_argument("source", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        output = normalize(_load(args.source))
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"METR adapter error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
