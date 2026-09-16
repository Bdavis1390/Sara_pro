"""CLI for bounded BAROS synthetic evidence generation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .pipeline import run_synthetic_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NON-CLINICAL BAROS synthetic verification pipeline")
    parser.add_argument("--output", type=Path, help="Optional JSON evidence output path")
    parser.add_argument("--commit-sha", default=os.getenv("GITHUB_SHA", "UNPINNED"))
    args = parser.parse_args()

    evidence = run_synthetic_pipeline(commit_sha=args.commit_sha)
    payload = json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if evidence["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
