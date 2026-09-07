#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys

from worldshepherd_sara.host_acceptance import assess_actual_host_evidence


def _git_value(*args: str) -> str | None:
    try:
        value = subprocess.check_output(
            ["git", *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return value or None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify integrity and acceptance gates for an actual-host PVK evidence package. "
            "Unless explicitly overridden, branch and commit expectations are bound to the current checkout."
        )
    )
    parser.add_argument("evidence_dir")
    parser.add_argument("--expected-branch")
    parser.add_argument("--expected-commit")
    parser.add_argument(
        "--allow-unbound",
        action="store_true",
        help="Permit assessment without branch/commit binding when Git context is unavailable.",
    )
    args = parser.parse_args()

    expected_branch = args.expected_branch or _git_value("branch", "--show-current")
    expected_commit = args.expected_commit or _git_value("rev-parse", "HEAD")

    if not args.allow_unbound and (not expected_branch or not expected_commit):
        print(
            json.dumps(
                {
                    "accepted": False,
                    "blockers": ["ASSESSMENT_NOT_BOUND_TO_BRANCH_AND_COMMIT"],
                    "warnings": [],
                    "scientific_validation_claim": "NOT_ESTABLISHED_BY_HOST_ACCEPTANCE",
                },
                sort_keys=True,
                indent=2,
            )
        )
        return 2

    assessment = assess_actual_host_evidence(
        args.evidence_dir,
        expected_branch=expected_branch,
        expected_commit=expected_commit,
    )
    payload = assessment.as_dict()
    payload["expected_branch"] = expected_branch
    payload["expected_commit"] = expected_commit
    payload["assessment_binding"] = (
        "BOUND" if expected_branch and expected_commit else "UNBOUND_EXPLICITLY_ALLOWED"
    )
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0 if assessment.accepted else 1


if __name__ == "__main__":
    sys.exit(main())
