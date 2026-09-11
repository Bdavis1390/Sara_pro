#!/usr/bin/env python3
"""Load evaluator-controlled protected task artifacts with hash verification.

Raw holdout tasks stay outside the public repository. This module accepts a local
artifact path at evaluation time, verifies its exact SHA-256 against the public
manifest metadata, validates task structure, and converts records into
ProtectedTask objects for the existing bounded suite runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from runtime.protected_suite_runner import ProtectedTask


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _required(record: Mapping[str, Any], fields: Iterable[str], *, context: str) -> None:
    missing = [name for name in fields if record.get(name) in (None, "")]
    if missing:
        raise ValueError(f"{context} missing required fields: {', '.join(missing)}")


def load_protected_tasks(manifest: Mapping[str, Any], artifact_path: Path) -> List[ProtectedTask]:
    _required(manifest, ["task_count", "task_set_hash", "artifact_access"], context="manifest")
    access = manifest["artifact_access"]
    if not isinstance(access, Mapping) or access.get("evaluator_controlled") is not True:
        raise ValueError("protected artifact must be evaluator-controlled")
    if access.get("public_repo_contains_raw_tasks") is not False:
        raise ValueError("manifest must declare that raw tasks are absent from the public repository")

    raw = artifact_path.read_bytes()
    observed_hash = _sha256_bytes(raw)
    if observed_hash != manifest["task_set_hash"]:
        raise ValueError("protected task artifact hash does not match manifest")

    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("protected task artifact must be UTF-8 JSON") from exc

    records = decoded.get("tasks") if isinstance(decoded, dict) else decoded
    if not isinstance(records, list) or not records:
        raise ValueError("protected task artifact must contain a non-empty task list")
    if len(records) != int(manifest["task_count"]):
        raise ValueError("protected task count does not match manifest")

    tasks: List[ProtectedTask] = []
    seen_ids = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"task {index} must be an object")
        _required(
            record,
            ["task_id", "goal", "success_criteria", "allowed_tools"],
            context=f"task {index}",
        )
        task_id = record["task_id"]
        if not isinstance(task_id, str) or not task_id:
            raise ValueError(f"task {index} task_id must be a non-empty string")
        if task_id in seen_ids:
            raise ValueError(f"duplicate protected task_id: {task_id}")
        seen_ids.add(task_id)

        allowed = record["allowed_tools"]
        approvals = record.get("approval_required_tools", [])
        if not isinstance(allowed, list) or not allowed or not all(isinstance(x, str) and x for x in allowed):
            raise ValueError(f"task {task_id} allowed_tools must be a non-empty string list")
        if not isinstance(approvals, list) or not all(isinstance(x, str) and x for x in approvals):
            raise ValueError(f"task {task_id} approval_required_tools must be a string list")
        allowed_set = set(allowed)
        approval_set = set(approvals)
        if not approval_set.issubset(allowed_set):
            raise ValueError(f"task {task_id} approval_required_tools must be a subset of allowed_tools")

        max_steps = record.get("max_steps", 8)
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps <= 0:
            raise ValueError(f"task {task_id} max_steps must be a positive integer")
        goal = record["goal"]
        criteria = record["success_criteria"]
        if not isinstance(goal, str) or not goal or not isinstance(criteria, str) or not criteria:
            raise ValueError(f"task {task_id} goal and success_criteria must be non-empty strings")

        tasks.append(
            ProtectedTask(
                task_id=task_id,
                goal=goal,
                success_criteria=criteria,
                allowed_tools=allowed_set,
                approval_required_tools=approval_set,
                max_steps=max_steps,
            )
        )
    return tasks


def load_manifest(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an evaluator-controlled protected task artifact")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        tasks = load_protected_tasks(manifest, args.artifact)
        summary = {
            "valid": True,
            "suite_id": manifest.get("suite_id"),
            "suite_version": manifest.get("suite_version"),
            "task_count": len(tasks),
            "task_set_hash": manifest.get("task_set_hash"),
            "artifact_reference": manifest.get("artifact_access", {}).get("reference_id"),
        }
        print(json.dumps(summary, indent=2 if args.pretty else None, sort_keys=args.pretty))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Protected artifact validation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
