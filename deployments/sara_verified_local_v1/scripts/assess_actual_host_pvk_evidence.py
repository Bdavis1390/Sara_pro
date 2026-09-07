#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from worldshepherd_sara.host_acceptance import assess_actual_host_evidence


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify integrity and acceptance gates for an actual-host PVK evidence package."
    )
    parser.add_argument("evidence_dir")
    parser.add_argument("--expected-branch")
    parser.add_argument("--expected-commit")
    args = parser.parse_args()

    assessment = assess_actual_host_evidence(
        args.evidence_dir,
        expected_branch=args.expected_branch,
        expected_commit=args.expected_commit,
    )
    print(json.dumps(assessment.as_dict(), sort_keys=True, indent=2))
    return 0 if assessment.accepted else 1


if __name__ == "__main__":
    sys.exit(main())
