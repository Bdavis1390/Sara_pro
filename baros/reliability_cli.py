"""CLI for BAROS bounded reliability evidence generation.

NON-CLINICAL. This command estimates only bounded synthetic research-software
reliability under the predeclared distribution in `baros.reliability`.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .reliability import report_as_dict, run_reliability_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BAROS bounded 98.7% reliability gate")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit-sha", default=os.getenv("GITHUB_SHA", "UNPINNED"))
    parser.add_argument("--cases", type=int, default=1000)
    parser.add_argument("--confidence", type=float, default=0.999)
    parser.add_argument("--target-probability", type=float, default=0.987)
    args = parser.parse_args()

    report = run_reliability_gate(
        cases=args.cases,
        confidence=args.confidence,
        target_probability=args.target_probability,
        commit_sha=args.commit_sha,
    )
    payload = report_as_dict(report)
    payload["commit_sha"] = args.commit_sha
    payload["claim_scope"] = (
        "bounded synthetic BAROS research-software acceptance probability under "
        "the predeclared synthetic reliability distribution"
    )
    payload["clinical_probability_claimed"] = False
    payload["limitations"] = [
        "synthetic population only",
        "not an estimate of physical-dose correctness",
        "not an estimate of clinical safety or effectiveness",
        "not an estimate of treatment success or patient outcome",
        "not regulatory authorization",
        "external TPS, dosimetric, retrospective, prospective, and peer-review evidence remain separate gates",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0 if report.gate_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
