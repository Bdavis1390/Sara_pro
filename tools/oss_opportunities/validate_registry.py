#!/usr/bin/env python3
"""Validate the Worldshepherd OSS opportunity registry.

The registry is deliberately dependency-free so it can run in a minimal CI runner.
It is a claims-control gate, not a scoring engine: scores remain analyst judgments,
but contradictory status/evidence/ownership combinations are rejected.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
from typing import Any

TASKS = {"A", "B", "C"}
PRIORITIES = {"P0", "P1", "WATCH", "CLOSED"}
UPSTREAM_STATES = {"OPEN", "CLOSED"}
COLLISIONS = {
    "CLEAR",
    "ACTIVE_PR",
    "CONTRIBUTOR_OWNED",
    "ASSIGNED",
    "CLOSED_UPSTREAM",
    "WATCH_ONLY",
}
MATURITIES = {
    "SCREENED",
    "SOURCE_REVIEWED",
    "REPRODUCTION_REQUIRED",
    "PATCH_DRAFT",
    "LAB_VALIDATION",
    "THIRD_PARTY_PATCH",
}
CLAIMS_STATES = {
    "PROVEN INTERNALLY",
    "IMPLEMENTED IN SOFTWARE",
    "SUPPORTED BY LITERATURE",
    "SIMULATED ONLY",
    "HYPOTHESIS",
    "SPECULATIVE EXTENSION",
    "REQUIRES LAB VALIDATION",
    "REQUIRES PARTNER VALIDATION",
    "REQUIRES LEGAL REVIEW",
    "NOT CURRENTLY CLAIMED",
}

ISSUE_URL = re.compile(r"^https://github\.com/[^/]+/[^/]+/(issues|pull)/\d+$")
REPO = re.compile(r"^[^/\s]+/[^/\s]+$")

REQUIRED = {
    "repo",
    "number",
    "url",
    "title",
    "task",
    "priority",
    "score",
    "upstream_state",
    "collision",
    "duplicate_checked",
    "evidence_maturity",
    "claims_state",
    "next_gate",
    "last_checked",
}


def _error(errors: list[str], ident: str, message: str) -> None:
    errors.append(f"{ident}: {message}")


def validate_entry(entry: dict[str, Any], *, today: dt.date | None = None) -> list[str]:
    errors: list[str] = []
    ident = f"{entry.get('repo', '<missing-repo>')}#{entry.get('number', '<missing-number>')}"

    missing = sorted(REQUIRED - entry.keys())
    if missing:
        _error(errors, ident, f"missing required fields: {', '.join(missing)}")
        return errors

    if not isinstance(entry["repo"], str) or not REPO.match(entry["repo"]):
        _error(errors, ident, "repo must be 'owner/name'")

    if not isinstance(entry["number"], int) or entry["number"] <= 0:
        _error(errors, ident, "number must be a positive integer")

    if not isinstance(entry["url"], str) or not ISSUE_URL.match(entry["url"]):
        _error(errors, ident, "url must be a canonical GitHub issue or pull URL")

    if not isinstance(entry["title"], str) or not entry["title"].strip():
        _error(errors, ident, "title must be non-empty")

    if entry["task"] not in TASKS:
        _error(errors, ident, f"task must be one of {sorted(TASKS)}")

    if entry["priority"] not in PRIORITIES:
        _error(errors, ident, f"priority must be one of {sorted(PRIORITIES)}")

    if not isinstance(entry["score"], int) or not 0 <= entry["score"] <= 100:
        _error(errors, ident, "score must be an integer in [0, 100]")

    if entry["upstream_state"] not in UPSTREAM_STATES:
        _error(errors, ident, f"upstream_state must be one of {sorted(UPSTREAM_STATES)}")

    if entry["collision"] not in COLLISIONS:
        _error(errors, ident, f"collision must be one of {sorted(COLLISIONS)}")

    if entry["evidence_maturity"] not in MATURITIES:
        _error(errors, ident, f"evidence_maturity must be one of {sorted(MATURITIES)}")

    if entry["claims_state"] not in CLAIMS_STATES:
        _error(errors, ident, "claims_state is not a Worldshepherd claims-control label")

    if entry["duplicate_checked"] is not True:
        _error(errors, ident, "duplicate_checked must be true before registry admission")

    if not isinstance(entry["next_gate"], str) or not entry["next_gate"].strip():
        _error(errors, ident, "next_gate must be non-empty")

    try:
        checked = dt.date.fromisoformat(entry["last_checked"])
    except (TypeError, ValueError):
        _error(errors, ident, "last_checked must be ISO YYYY-MM-DD")
        checked = None

    if checked and today and checked > today:
        _error(errors, ident, "last_checked cannot be in the future")

    # Claims-control invariants.
    if entry["priority"] in {"P0", "P1"}:
        if entry["upstream_state"] != "OPEN":
            _error(errors, ident, "P0/P1 candidates must still be upstream OPEN")
        if entry["collision"] != "CLEAR":
            _error(errors, ident, "P0/P1 candidates must have collision=CLEAR")

    if entry["priority"] == "WATCH" and entry["collision"] == "CLEAR":
        _error(errors, ident, "WATCH requires an ownership/PR/watch collision reason")

    if entry["priority"] == "CLOSED":
        if entry["upstream_state"] != "CLOSED":
            _error(errors, ident, "CLOSED priority requires upstream_state=CLOSED")
        if entry["collision"] != "CLOSED_UPSTREAM":
            _error(errors, ident, "CLOSED priority requires collision=CLOSED_UPSTREAM")

    if entry["collision"] == "CLOSED_UPSTREAM" and entry["upstream_state"] != "CLOSED":
        _error(errors, ident, "CLOSED_UPSTREAM collision requires upstream_state=CLOSED")

    if entry["collision"] in {"ACTIVE_PR", "CONTRIBUTOR_OWNED", "ASSIGNED"} and entry["priority"] not in {"WATCH"}:
        _error(errors, ident, "occupied upstream work must be WATCH, not an ownership candidate")

    if entry["evidence_maturity"] == "LAB_VALIDATION" and entry["claims_state"] != "REQUIRES LAB VALIDATION":
        _error(errors, ident, "LAB_VALIDATION maturity requires REQUIRES LAB VALIDATION claims state")

    if entry["evidence_maturity"] == "PATCH_DRAFT" and entry["claims_state"] == "PROVEN INTERNALLY":
        _error(errors, ident, "a patch draft cannot be labeled PROVEN INTERNALLY")

    return errors


def validate_registry(doc: dict[str, Any], *, today: dt.date | None = None) -> list[str]:
    errors: list[str] = []

    if doc.get("schema_version") != 1:
        errors.append("registry: schema_version must be 1")

    entries = doc.get("opportunities")
    if not isinstance(entries, list) or not entries:
        errors.append("registry: opportunities must be a non-empty list")
        return errors

    seen: set[tuple[str, int]] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"registry[{index}]: entry must be an object")
            continue
        errors.extend(validate_entry(entry, today=today))
        repo = entry.get("repo")
        number = entry.get("number")
        if isinstance(repo, str) and isinstance(number, int):
            key = (repo.lower(), number)
            if key in seen:
                errors.append(f"{repo}#{number}: duplicate registry entry")
            seen.add(key)

    return errors


def load(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("registry root must be a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("registry", type=pathlib.Path)
    args = parser.parse_args(argv)

    try:
        doc = load(args.registry)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"registry load failed: {exc}", file=sys.stderr)
        return 2

    errors = validate_registry(doc, today=dt.date.today())
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print(f"registry invalid: {len(errors)} error(s)", file=sys.stderr)
        return 1

    print(f"registry valid: {len(doc['opportunities'])} opportunities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
