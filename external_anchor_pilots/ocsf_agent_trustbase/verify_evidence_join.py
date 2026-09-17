#!/usr/bin/env python3
"""
Provisional evidence-grade join checker for OCSF #1724.

This is NOT an OCSF schema validator. It checks a stronger implementation
property discussed in the issue thread: a trust-base closure event and its
correlated activity event carry the same metadata.correlation_uid, and both
records are independently protected with record_integrity-style attestations.

OCSF's attestation object states that the canonical serialization covers the
entire event except the attestation's own fingerprint and signatures. Therefore,
when metadata.correlation_uid is present in an attested event, the correlation
key is inside the integrity-protected bytes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _first_attestation(event: Dict[str, Any]) -> Dict[str, Any] | None:
    value = event.get("attestation_list")
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return None


def _integrity_protected(event: Dict[str, Any]) -> bool:
    att = _first_attestation(event)
    if not att:
        return False
    fp = att.get("fingerprint")
    return isinstance(fp, dict) and bool(fp.get("value"))


def validate_case(case: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    closure = case.get("trust_base_closure")
    activity = case.get("activity_event")

    if not isinstance(closure, dict):
        return ["case: trust_base_closure object is required"]
    if not isinstance(activity, dict):
        return ["case: activity_event object is required"]

    if closure.get("phase") != "closure":
        errors.append("trust_base_closure.phase must be 'closure'")

    instance_uid = ((closure.get("ai_agent") or {}).get("instance_uid"))
    if not instance_uid:
        errors.append("trust_base_closure.ai_agent.instance_uid is required")

    closure_meta = closure.get("metadata") or {}
    activity_meta = activity.get("metadata") or {}
    closure_corr = closure_meta.get("correlation_uid")
    activity_corr = activity_meta.get("correlation_uid")

    if not closure_corr:
        errors.append("trust_base_closure.metadata.correlation_uid is required")
    if not activity_corr:
        errors.append("activity_event.metadata.correlation_uid is required")
    if closure_corr and activity_corr and closure_corr != activity_corr:
        errors.append(
            f"correlation mismatch: closure='{closure_corr}' activity='{activity_corr}'"
        )

    if not _integrity_protected(closure):
        errors.append(
            "trust_base_closure requires attestation_list[0].fingerprint.value "
            "for an evidence-grade join"
        )
    if not _integrity_protected(activity):
        errors.append(
            "activity_event requires attestation_list[0].fingerprint.value "
            "for an evidence-grade join"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()

    data = json.loads(args.fixture.read_text())
    cases = data.get("cases", [])
    if not cases:
        raise SystemExit("fixture must contain non-empty 'cases' list")

    mismatches = 0
    for case in cases:
        name = case.get("name", "<unnamed>")
        expected = case.get("expected", "pass")
        errors = validate_case(case)
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
