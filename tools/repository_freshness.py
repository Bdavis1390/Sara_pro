#!/usr/bin/env python3
"""Fail-closed checks for Worldshepherd repository source-of-truth freshness."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "runtime/README.md",
    "runtime/manifest.json",
    "scripts/sara.sh",
    "docs/CLAIMS_AND_EVIDENCE_POLICY.md",
    "docs/WORLDSHEPHERD_CAPABILITY_MAP.md",
    "docs/operations/ACTIVE_TASKS.md",
    "docs/operations/FRESHNESS_POLICY.md",
    "docs/operations/FRESHNESS_AUDIT_2026-09-15.md",
    ".github/pull_request_template.md",
)

REQUIRED_POLICY_STATES = (
    "CURRENT_CANONICAL",
    "ACTIVE",
    "DATED_EVIDENCE",
    "RECONCILE_REQUIRED",
    "SUPERSEDED",
    "ARCHIVE",
    "SAFE_DELETE_AFTER_VERIFY",
)

FORBIDDEN_CURRENT_PHRASES = (
    "runtime packaging remains fragmented",
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        require(errors, (ROOT / relative).is_file(), f"missing required source-of-truth file: {relative}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    root_readme = read("README.md")
    capability_map = read("docs/WORLDSHEPHERD_CAPABILITY_MAP.md")
    active_tasks = read("docs/operations/ACTIVE_TASKS.md")
    freshness_policy = read("docs/operations/FRESHNESS_POLICY.md")
    pr_template = read(".github/pull_request_template.md")
    runtime_readme = read("runtime/README.md")

    require(errors, "deployments/sara_verified_local_v1/" in root_readme, "root README must identify the canonical SARA implementation")
    require(errors, "runtime/README.md" in root_readme, "root README must link the canonical runtime entry point")
    require(errors, "recorded_local_only" in root_readme, "root README must preserve the local-relay claims boundary")
    require(errors, "FRESHNESS_POLICY.md" in root_readme, "root README must link the freshness policy")
    require(errors, "ACTIVE_TASKS.md" in root_readme, "root README must link the active-task source of truth")

    require(errors, "deployments/sara_verified_local_v1/" in capability_map, "capability map must identify the canonical SARA runtime")
    for phrase in FORBIDDEN_CURRENT_PHRASES:
        require(errors, phrase not in capability_map, f"capability map contains known stale phrase: {phrase!r}")

    for issue in ("#281", "#282", "#283"):
        require(errors, issue in active_tasks, f"active-task map is missing umbrella {issue}")

    for state in REQUIRED_POLICY_STATES:
        require(errors, state in freshness_policy, f"freshness policy is missing lifecycle state {state}")

    require(errors, "Freshness / supersession" in pr_template, "PR template must require freshness/supersession review")
    require(errors, "deployments/sara_verified_local_v1/" in runtime_readme, "runtime README must point to the canonical package")

    canonical_files = (
        "README.md",
        "runtime/README.md",
        "docs/README.md",
        "docs/WORLDSHEPHERD_CAPABILITY_MAP.md",
        "docs/operations/ACTIVE_TASKS.md",
        "docs/operations/FRESHNESS_POLICY.md",
    )
    for relative in canonical_files:
        text = read(relative)
        require(errors, "<<<<<<< " not in text and ">>>>>>> " not in text, f"merge-conflict marker found in {relative}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("repository_freshness_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
