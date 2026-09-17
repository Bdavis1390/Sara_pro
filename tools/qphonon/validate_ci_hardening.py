#!/usr/bin/env python3
"""Validate security-sensitive properties of the QPHONON GitHub Actions workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

CHECKOUT_SHA = "11d5960a326750d5838078e36cf38b85af677262"
SETUP_PYTHON_SHA = "a26af69be951a213d495a4c3e4e4022e16d87065"


def validate(text: str) -> list[str]:
    errors: list[str] = []

    if f"actions/checkout@{CHECKOUT_SHA}" not in text:
        errors.append("actions/checkout must be pinned to the approved immutable commit")
    if f"actions/setup-python@{SETUP_PYTHON_SHA}" not in text:
        errors.append("actions/setup-python must be pinned to the approved immutable commit")
    if "actions/checkout@v4" in text or "actions/setup-python@v5" in text:
        errors.append("mutable major-version action refs are prohibited")
    if "persist-credentials: false" not in text:
        errors.append("checkout must disable persisted credentials")
    if "permissions:\n  contents: read" not in text:
        errors.append("workflow must retain contents-read-only permissions")
    if "pull_request_target:" in text:
        errors.append("pull_request_target is prohibited for this security workflow")
    if "${{ secrets." in text:
        errors.append("QPHONON security CI must not consume repository secrets")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default=".github/workflows/ws-qphonon-l2-check.yml",
    )
    args = parser.parse_args()
    try:
        text = Path(args.path).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: unable to read workflow: {exc}")
        return 1
    errors = validate(text)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("WS-QPHONON CI hardening: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
