#!/usr/bin/env python3
"""Worldshepherd V23 GitHub Action reference audit.

Purpose:
- Inventory external GitHub Actions references used by workflows.
- Classify immutable 40-hex commit pins vs floating refs.
- On pull requests, fail only when the head introduces new floating
  GitHub Action references or downgrades an exact pin to a floating ref.

Existing floating references remain backlog; V23 is a no-regression gate.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

WORKFLOW_ROOT = ".github/workflows"
WORKFLOW_SUFFIXES = (".yml", ".yaml")
USES_RE = re.compile(r"""^\s*(?:-\s*)?uses:\s*["']?([^"'#\s]+)""")
SHA40_RE = re.compile(r"^[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class ActionUse:
    workflow: str
    line: int
    target: str
    ref: str
    raw: str
    kind: str
    pinned: bool

    @property
    def exact_signature(self) -> str:
        return f"{self.workflow}|{self.target}|{self.ref}"

    @property
    def target_signature(self) -> str:
        return f"{self.workflow}|{self.target}"


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout


def _workflow_paths(ref: str) -> list[str]:
    out = _git("ls-tree", "-r", "--name-only", ref, "--", WORKFLOW_ROOT)
    return sorted(p for p in out.splitlines() if p.endswith(WORKFLOW_SUFFIXES))


def _read_at_ref(ref: str, path: str) -> str:
    return _git("show", f"{ref}:{path}")


def _parse_uses_value(value: str, workflow: str, line: int) -> ActionUse | None:
    if value.startswith("./"):
        return ActionUse(workflow, line, value, "", value, "local", True)

    if value.startswith("docker://"):
        image = value[len("docker://"):]
        pinned = "@sha256:" in image
        return ActionUse(workflow, line, image, "", value, "docker", pinned)

    if "@" not in value:
        return ActionUse(workflow, line, value, "", value, "malformed", False)

    target, ref = value.rsplit("@", 1)
    if not target or not ref:
        return ActionUse(workflow, line, target or value, ref, value, "malformed", False)

    return ActionUse(
        workflow=workflow,
        line=line,
        target=target,
        ref=ref,
        raw=value,
        kind="github_action",
        pinned=bool(SHA40_RE.fullmatch(ref)),
    )


def parse_workflow_text(text: str, workflow: str) -> list[ActionUse]:
    uses: list[ActionUse] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = USES_RE.match(line)
        if not match:
            continue
        parsed = _parse_uses_value(match.group(1), workflow, line_no)
        if parsed is not None:
            uses.append(parsed)
    return uses


def scan_ref(ref: str) -> list[ActionUse]:
    found: list[ActionUse] = []
    for path in _workflow_paths(ref):
        found.extend(parse_workflow_text(_read_at_ref(ref, path), path))
    return found


def summarize(ref: str, uses: Iterable[ActionUse]) -> dict:
    rows = list(uses)
    floating = [u for u in rows if not u.pinned and u.kind != "local"]
    pinned = [u for u in rows if u.pinned]
    return {
        "schema": "WS-GITHUB-ACTION-PIN-AUDIT-V23",
        "ref": ref,
        "counts": {
            "total_uses": len(rows),
            "pinned": len(pinned),
            "floating_or_malformed": len(floating),
        },
        "uses": [asdict(u) for u in rows],
        "floating": [asdict(u) for u in floating],
    }


def compare(base_ref: str, head_ref: str) -> dict:
    base = scan_ref(base_ref)
    head = scan_ref(head_ref)

    base_float = collections.Counter(
        u.exact_signature for u in base if not u.pinned and u.kind != "local"
    )
    head_float = collections.Counter(
        u.exact_signature for u in head if not u.pinned and u.kind != "local"
    )

    new_floating: list[str] = []
    for signature, count in (head_float - base_float).items():
        new_floating.extend([signature] * count)

    base_pinned_targets = {
        u.target_signature for u in base if u.pinned and u.kind == "github_action"
    }
    head_floating_targets = {
        u.target_signature for u in head if not u.pinned and u.kind == "github_action"
    }
    downgraded = sorted(base_pinned_targets & head_floating_targets)

    result = {
        "schema": "WS-GITHUB-ACTION-PIN-COMPARE-V23",
        "base": summarize(base_ref, base),
        "head": summarize(head_ref, head),
        "new_floating": sorted(new_floating),
        "pinned_to_floating": downgraded,
    }
    result["result"] = "PASS" if not new_floating and not downgraded else "FAIL"
    result["claims_boundary"] = (
        "No-regression policy only. PASS means this change did not add a new "
        "floating GitHub Action reference or replace an exact 40-hex action pin "
        "with a floating ref. PASS does not mean the pre-existing repository "
        "backlog is fully immutable or supply-chain certified."
    )
    return result


def _write_json(payload: dict, output: str | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan")
    scan_p.add_argument("--ref", default="HEAD")
    scan_p.add_argument("--output")

    cmp_p = sub.add_parser("compare")
    cmp_p.add_argument("--base", required=True)
    cmp_p.add_argument("--head", required=True)
    cmp_p.add_argument("--output")

    args = parser.parse_args(argv)

    if args.command == "scan":
        _write_json(summarize(args.ref, scan_ref(args.ref)), args.output)
        return 0

    result = compare(args.base, args.head)
    _write_json(result, args.output)
    if result["result"] != "PASS":
        print(
            "V23 no-regression gate failed: new floating or downgraded "
            "GitHub Action references detected.",
            file=sys.stderr,
        )
        return 23
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
