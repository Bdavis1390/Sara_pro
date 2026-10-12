"""CLI for BAROS expert technical readout generation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .expert_readout import build_expert_readout, render_expert_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate NON-CLINICAL BAROS expert technical readouts")
    parser.add_argument("--json-output", type=Path, help="Optional JSON readout path")
    parser.add_argument("--markdown-output", type=Path, help="Optional Markdown readout path")
    parser.add_argument("--commit-sha", default=os.getenv("GITHUB_SHA", "UNPINNED"))
    args = parser.parse_args()

    report = build_expert_readout(commit_sha=args.commit_sha)
    json_payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    markdown = render_expert_markdown(report)

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json_payload, encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")

    print(json_payload, end="")
    return 0 if report["source_evidence"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
