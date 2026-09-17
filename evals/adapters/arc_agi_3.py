#!/usr/bin/env python3
"""Normalize ARC-AGI-3 verified result records into Worldshepherd AGI gate fields.

The adapter is intentionally offline and deterministic: it does not scrape the web or
trust model self-reports. A caller must provide a source record captured from a verified
evaluation source. Standard and Provider Adapter harnesses are always kept separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

HARNESS_TO_METRIC = {
    "standard": "arc_agi_3_standard_score_pct",
    "provider_adapter": "arc_agi_3_provider_adapter_score_pct",
}


def _load(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ARC source record must be a JSON object")
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
            "results",
        ],
        "ARC source",
    )
    if not isinstance(source["results"], list) or not source["results"]:
        raise ValueError("ARC source results must be a non-empty array")

    metrics: Dict[str, float] = {}
    metric_validity: Dict[str, Dict[str, Any]] = {}
    evidence = []

    for index, result in enumerate(source["results"]):
        if not isinstance(result, dict):
            raise ValueError(f"ARC result {index} must be an object")
        _required(result, ["harness", "score_pct", "verified"], f"ARC result {index}")
        harness = str(result["harness"]).strip().lower()
        if harness not in HARNESS_TO_METRIC:
            raise ValueError(f"Unsupported ARC-AGI-3 harness: {harness}")
        if result["verified"] is not True:
            continue

        score = float(result["score_pct"])
        if not 0.0 <= score <= 100.0:
            raise ValueError(f"ARC result {index} score_pct outside [0,100]")
        metric = HARNESS_TO_METRIC[harness]

        # Keep the best verified result for each harness while never mixing harnesses.
        if metric in metrics and score <= metrics[metric]:
            continue
        metrics[metric] = score
        metric_validity[metric] = {
            "valid": True,
            "reason": "verified result supplied to ARC-AGI-3 adapter",
            "harness": harness,
        }

        record_id = f"arc-agi-3:{source['system_id']}:{harness}:{index}"
        evidence.append(
            {
                "evidence_id": record_id,
                "metric_names": [metric],
                "system_id": source["system_id"],
                "system_version": source["system_version"],
                "evaluator": source.get("evaluator", "ARC Prize verified testing"),
                "benchmark_version": source["benchmark_version"],
                "evaluation_date": source["evaluation_date"],
                "environment": source["environment"],
                "tools_and_permissions": source.get(
                    "tools_and_permissions", "as specified by source harness"
                ),
                "trial_count": result.get("trial_count", source.get("trial_count", 1)),
                "score": score,
                "human_baseline": source.get(
                    "human_baseline", "ARC-AGI-3 human action-efficiency baseline reported separately"
                ),
                "contamination_controls": source.get(
                    "contamination_controls", "semi-private evaluation set"
                ),
                "integrity_adjudication": source.get(
                    "integrity_adjudication", "verified-testing source record"
                ),
                "source_or_artifact_hash": source.get("source_or_artifact_hash")
                or _canonical_hash(source),
                "task_hash": source["task_hash"],
                "grader_version": source["grader_version"],
                "rerun_count": result.get("rerun_count", 0),
                "human_adjudication": source.get(
                    "human_adjudication", "source evaluator adjudication"
                ),
                "claim_state": source.get("claim_state", "EXTERNALLY_REPLICATED"),
                "source_url": source["source_url"],
                "harness": harness,
                "reasoning_level": result.get("reasoning_level"),
                "cost_usd": result.get("cost_usd"),
            }
        )

    return {
        "schema": "WS-ARC-AGI-3-ADAPTER-V1.0",
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "metrics": metrics,
        "metric_validity": metric_validity,
        "evidence": evidence,
        "adapter_notes": [
            "Standard and Provider Adapter harness results remain separate.",
            "Provider Adapter results never substitute for Standard-harness results.",
            "Only source records explicitly marked verified=true are admitted.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize ARC-AGI-3 result JSON")
    parser.add_argument("source", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        output = normalize(_load(args.source))
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ARC-AGI-3 adapter error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
