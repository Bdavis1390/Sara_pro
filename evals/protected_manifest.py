#!/usr/bin/env python3
"""Validate metadata for protected AGI evaluation task sets.

The public repository should contain only hashes and control metadata, never raw
holdout tasks, answer keys, or hidden grader targets. Actual protected artifacts
remain outside the repository under evaluator-controlled access.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FORBIDDEN_INLINE_FIELDS = {
    "tasks",
    "task_content",
    "answer_key",
    "answers",
    "hidden_answers",
    "grader_targets",
    "solutions",
}


def _load(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest must be a JSON object")
    return value


def _required(record: Mapping[str, Any], fields: Iterable[str]) -> None:
    missing = [field for field in fields if record.get(field) in (None, "")]
    if missing:
        raise ValueError("manifest missing required fields: " + ", ".join(missing))


def validate_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    forbidden = sorted(FORBIDDEN_INLINE_FIELDS.intersection(manifest))
    if forbidden:
        raise ValueError("protected content must not be stored inline: " + ", ".join(forbidden))

    _required(
        manifest,
        [
            "schema",
            "suite_id",
            "suite_version",
            "target_lane",
            "task_count",
            "task_set_hash",
            "grader_hash",
            "controls",
            "artifact_access",
        ],
    )
    if manifest["schema"] != "WS-PROTECTED-TASK-MANIFEST-V1.0":
        raise ValueError("unsupported manifest schema")
    if manifest["target_lane"] not in (
        "economic_breadth",
        "cross_domain_transfer",
        "tool_workflow_reliability",
        "self_correction",
        "evidence_integrity",
        "long_horizon_autonomy",
        "novel_generalization",
    ):
        raise ValueError("unsupported target_lane")
    if isinstance(manifest["task_count"], bool) or int(manifest["task_count"]) <= 0:
        raise ValueError("task_count must be positive")
    for field in ("task_set_hash", "grader_hash"):
        value = manifest[field]
        if not isinstance(value, str) or not SHA256_RE.match(value):
            raise ValueError(f"{field} must be a canonical sha256:<64 hex> hash")

    controls = manifest["controls"]
    if not isinstance(controls, dict):
        raise ValueError("controls must be an object")
    required_controls = {
        "heldout": True,
        "task_set_fixed_before_run": True,
        "answer_key_separate": True,
        "contamination_review_passed": True,
        "failed_runs_retained": True,
    }
    errors: List[str] = []
    for name, required_value in required_controls.items():
        if controls.get(name) != required_value:
            errors.append(f"control {name} must equal {required_value!r}")

    access = manifest["artifact_access"]
    if not isinstance(access, dict):
        raise ValueError("artifact_access must be an object")
    if access.get("public_repo_contains_raw_tasks") is not False:
        errors.append("public_repo_contains_raw_tasks must be false")
    if access.get("evaluator_controlled") is not True:
        errors.append("evaluator_controlled must be true")
    if not isinstance(access.get("reference_id"), str) or not access.get("reference_id"):
        errors.append("artifact_access.reference_id is required")

    return {
        "valid": not errors,
        "errors": errors,
        "suite_id": manifest["suite_id"],
        "suite_version": manifest["suite_version"],
        "target_lane": manifest["target_lane"],
        "task_count": int(manifest["task_count"]),
        "task_set_hash": manifest["task_set_hash"],
        "grader_hash": manifest["grader_hash"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate protected evaluation manifest metadata")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        result = validate_manifest(_load(args.manifest))
        print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0 if result["valid"] else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Protected manifest error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
