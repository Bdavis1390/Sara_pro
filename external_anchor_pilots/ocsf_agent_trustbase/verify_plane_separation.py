#!/usr/bin/env python3
"""Provisional non-duplication checker for the OCSF #1724 trust-base pilot.

This checker enforces only a harness-level architectural boundary: behavior and
outcome telemetry should not be copied into the provisional `trust_base` object.
It does not define OCSF field names or a normative correlation mechanism.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, List, Tuple

# Keys that belong to behavior/outcome telemetry under current adjacent OCSF
# discussions (#1754 AI Agent Activity, #1704 ai_status), not to the #1724
# trust-base configuration/evidence payload.
FORBIDDEN_TRUST_BASE_ACTIVITY_KEYS = {
    "activity_id",
    "activity_name",
    "ai_tool_input",
    "ai_tool_response",
    "tool_input",
    "tool_response",
    "tool_result",
    "stop_reason",
    "stop_reason_id",
    "permission_result_id",
    "compaction_reason_id",
    "subagent_stop_reason_id",
}


def walk(obj: Any, path: str = "$") -> Iterable[Tuple[str, str]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{path}.{key}"
            yield child, str(key)
            yield from walk(value, child)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from walk(value, f"{path}[{index}]")


def validate_event(event: Any) -> List[str]:
    if not isinstance(event, dict):
        return ["event must be an object"]

    trust_base = event.get("trust_base")
    if not isinstance(trust_base, dict):
        return ["event.trust_base must be an object"]

    errors: List[str] = []
    for path, key in walk(trust_base, "$.trust_base"):
        if key in FORBIDDEN_TRUST_BASE_ACTIVITY_KEYS:
            errors.append(
                f"behavior/outcome key '{key}' is not permitted inside trust_base at {path}; "
                "keep the activity/outcome in its OCSF activity/ai_status representation and correlate instead"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()

    data = json.loads(args.fixture.read_text())
    cases = data.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise SystemExit("fixture must contain a non-empty 'cases' list")

    mismatches = 0
    for case in cases:
        name = case.get("name", "<unnamed>")
        expected = case.get("expected", "pass")
        errors = validate_event(case.get("event"))
        actual = "pass" if not errors else "fail"
        ok = actual == expected
        print(f"[{'PASS' if ok else 'MISMATCH'}] {name}: expected={expected} actual={actual}")
        for error in errors:
            print(f"  - {error}")
        if not ok:
            mismatches += 1

    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
