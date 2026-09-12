#!/usr/bin/env python3
"""Convert protected, independently adjudicated trials into experience records.

Positive planner exemplars are created only from trials that passed independent
final-state adjudication and have no major/severe integrity issue. Failed trials
are retained as negative experience so the learning loop preserves mistakes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


def load_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON must be an object")
    return value


def canonical_hash(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _required(record: Mapping[str, Any], names: Iterable[str], prefix: str) -> None:
    missing = [name for name in names if record.get(name) in (None, "")]
    if missing:
        raise ValueError(f"{prefix} missing required fields: {', '.join(missing)}")


def ingest(source: Dict[str, Any]) -> Dict[str, Any]:
    _required(source, ["system_id", "system_version", "task_profiles", "trials"], "source")
    profiles = source["task_profiles"]
    trials = source["trials"]
    if not isinstance(profiles, dict):
        raise ValueError("task_profiles must be an object keyed by trial_id")
    if not isinstance(trials, list) or not trials:
        raise ValueError("trials must be a non-empty array")

    records: List[Dict[str, Any]] = []
    seen = set()
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict):
            raise ValueError(f"trials[{index}] must be an object")
        _required(
            trial,
            [
                "trial_id",
                "planner_identity",
                "final_state_evaluator_identity",
                "controller_status",
                "independent_final_state_pass",
                "integrity_severity",
                "steps",
            ],
            f"trials[{index}]",
        )
        trial_id = str(trial["trial_id"])
        if trial_id in seen:
            raise ValueError(f"duplicate trial_id: {trial_id}")
        seen.add(trial_id)
        if trial["planner_identity"] == trial["final_state_evaluator_identity"]:
            raise ValueError(f"trial {trial_id}: evaluator is not independent of planner")
        if not isinstance(trial["independent_final_state_pass"], bool):
            raise ValueError(f"trial {trial_id}: independent_final_state_pass must be boolean")
        severity = trial["integrity_severity"]
        if severity not in ("none", "minor", "major", "severe"):
            raise ValueError(f"trial {trial_id}: invalid integrity_severity")

        profile = profiles.get(trial_id)
        if not isinstance(profile, dict):
            raise ValueError(f"trial {trial_id}: missing task profile")
        _required(profile, ["task_family", "tags", "strategy_summary"], f"profile {trial_id}")
        tags = profile["tags"]
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
            raise ValueError(f"profile {trial_id}: tags must be non-empty strings")

        passed = bool(trial["independent_final_state_pass"])
        integrity_clean = severity in ("none", "minor")
        positive = passed and integrity_clean
        failure_summary = ""
        if not positive:
            feedback = trial.get("independent_feedback") or "independent final-state or integrity check did not qualify"
            failure_summary = str(feedback)

        evidence_material = {
            "system_id": source["system_id"],
            "system_version": source["system_version"],
            "trial": trial,
            "profile": profile,
        }
        records.append(
            {
                "experience_id": f"{source['system_id']}:{source['system_version']}:{trial_id}",
                "task_family": profile["task_family"],
                "tags": sorted(set(tags)),
                "strategy_summary": profile["strategy_summary"],
                "independently_passed": passed,
                "integrity_clean": integrity_clean,
                "positive_exemplar": positive,
                "final_evaluator_identity": trial["final_state_evaluator_identity"],
                "evidence_hash": canonical_hash(evidence_material),
                "failure_summary": failure_summary,
            }
        )

    positive_count = sum(1 for record in records if record["positive_exemplar"])
    return {
        "schema": "WS-VERIFIED-EXPERIENCE-INGEST-V1.0",
        "system_id": source["system_id"],
        "system_version": source["system_version"],
        "record_count": len(records),
        "positive_exemplar_count": positive_count,
        "negative_or_integrity_blocked_count": len(records) - positive_count,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build verified experience records from protected trials")
    parser.add_argument("source", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = ingest(load_json(args.source))
        print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Experience ingest error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
