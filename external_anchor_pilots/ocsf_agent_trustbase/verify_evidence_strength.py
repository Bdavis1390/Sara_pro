#!/usr/bin/env python3
"""
Provisional evidence-strength checker for the OCSF #1724 trust-base pilot.

This is intentionally non-normative. It implements only discussion-level
consistency rules that can be checked without inventing final OCSF field names.

verification_id meanings tracked from the #1724 issue discussion:
  0 Unknown
  1 Locally computed
  2 Provider asserted
  3 Third-party attested
  4 Not observable
  99 Other

The checker does NOT decide whether an evidence strength is sufficient for a
security control. Sufficiency remains relying-party policy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED = {0, 1, 2, 3, 4, 99}


def has_fingerprint(element):
    fp = element.get("fingerprint")
    return isinstance(fp, dict) and bool(fp.get("value"))


def has_hosted_tuple(element):
    model = element.get("ai_model")
    return (
        isinstance(model, dict)
        and all(bool(model.get(k)) for k in ("ai_provider", "name", "version"))
    )


def validate_element(element, path):
    errors = []
    verification_id = element.get("verification_id")

    if verification_id not in ALLOWED:
        return [f"{path}: verification_id must be one of {sorted(ALLOWED)}"]

    if verification_id == 1 and not has_fingerprint(element):
        errors.append(
            f"{path}: verification_id=1 (Locally computed) requires fingerprint.value"
        )

    if verification_id == 4 and has_fingerprint(element):
        errors.append(
            f"{path}: verification_id=4 (Not observable) cannot simultaneously "
            "claim a local content fingerprint"
        )

    if element.get("kind") in {"hosted_model", "remote_model"} and verification_id in {2, 4}:
        if not has_hosted_tuple(element):
            errors.append(
                f"{path}: hosted/remote model with verification_id={verification_id} "
                "requires ai_model.ai_provider/name/version so the reference remains identifiable"
            )

    return errors


def validate_case(case):
    elements = case.get("elements")
    if not isinstance(elements, list) or not elements:
        return ["case: non-empty elements list is required"]

    errors = []
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            errors.append(f"elements[{index}]: must be an object")
        else:
            errors.extend(validate_element(element, f"elements[{index}]"))
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()

    cases = json.loads(args.fixture.read_text()).get("cases", [])
    if not cases:
        raise SystemExit("fixture must contain non-empty 'cases' list")

    mismatches = 0
    for case in cases:
        errors = validate_case(case)
        actual = "pass" if not errors else "fail"
        expected = case.get("expected", "pass")
        ok = actual == expected
        print(
            f"[{'PASS' if ok else 'MISMATCH'}] {case.get('name', '<unnamed>')}: "
            f"expected={expected} actual={actual}"
        )
        for error in errors:
            print(f"  - {error}")
        if not ok:
            mismatches += 1

    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
