#!/usr/bin/env python3
"""Lightweight security sink inventory for PR #62.

This is a diagnostic supplement to CodeQL, not a replacement for CodeQL.
It inventories obvious CLI-derived filesystem sinks and selected dangerous APIs
so the eight CodeQL medium alerts can be triaged systematically.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

SCAN_ROOTS = [
    "boeing_spirit",
    "marketplace",
    "evidence",
    "pre",
    "readiness",
    "resonance",
    "stegriage",
    "ion_ep",
    "deployments",
]
EXCLUDE_PARTS = {".git", "__pycache__", ".venv", "venv", "node_modules"}


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


def is_arg_attr(node: ast.AST, arg_names: set[str]) -> bool:
    return isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in arg_names


def literal_string(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def audit_file(path: Path) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [{
            "file": str(path),
            "line": exc.lineno or 0,
            "kind": "syntax_error",
            "severity": "diagnostic",
            "detail": str(exc),
        }]

    arg_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if dotted(node.value.func).endswith("parse_args"):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        arg_names.add(target.id)

    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = dotted(node.func)
        first = node.args[0] if node.args else None

        # Direct CLI-derived filesystem path sinks.
        if fn in {"Path", "pathlib.Path", "open", "io.open"} and first is not None and is_arg_attr(first, arg_names):
            findings.append({
                "file": str(path),
                "line": getattr(node, "lineno", 0),
                "kind": "cli_derived_filesystem_sink",
                "severity": "review",
                "sink": fn,
                "source": dotted(first),
            })

        # Direct CLI-derived network target.
        if fn.endswith("urlopen") and first is not None and is_arg_attr(first, arg_names):
            findings.append({
                "file": str(path),
                "line": getattr(node, "lineno", 0),
                "kind": "cli_derived_network_sink",
                "severity": "review",
                "sink": fn,
                "source": dotted(first),
            })

        # Selected dangerous execution/deserialization APIs.
        if fn in {"eval", "exec", "os.system", "pickle.load", "pickle.loads", "yaml.load"}:
            findings.append({
                "file": str(path),
                "line": getattr(node, "lineno", 0),
                "kind": "dangerous_api",
                "severity": "high_review",
                "sink": fn,
            })

        if fn.startswith("subprocess."):
            shell_true = any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords)
            if shell_true:
                findings.append({
                    "file": str(path),
                    "line": getattr(node, "lineno", 0),
                    "kind": "subprocess_shell_true",
                    "severity": "high_review",
                    "sink": fn,
                })

        # Dynamic network calls are retained as diagnostics even when the URL is not CLI-derived.
        if fn.endswith("urlopen") and first is not None and not literal_string(first):
            findings.append({
                "file": str(path),
                "line": getattr(node, "lineno", 0),
                "kind": "dynamic_network_call",
                "severity": "diagnostic",
                "sink": fn,
                "expression": ast.unparse(first) if hasattr(ast, "unparse") else "dynamic",
            })

    # Stable de-duplication.
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in findings:
        key = (item.get("file"), item.get("line"), item.get("kind"), item.get("sink"), item.get("source"))
        unique[key] = item
    return sorted(unique.values(), key=lambda x: (x["file"], x["line"], x["kind"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="security/evidence/changed-python-sink-audit.json")
    ns = ap.parse_args()

    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = Path(root_name)
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if any(part in EXCLUDE_PARTS for part in p.parts):
                continue
            files.append(p)
    files = sorted(set(files))

    findings: list[dict[str, Any]] = []
    for p in files:
        findings.extend(audit_file(p))

    high_review = [f for f in findings if f["severity"] == "high_review"]
    cli_fs = [f for f in findings if f["kind"] == "cli_derived_filesystem_sink"]
    cli_net = [f for f in findings if f["kind"] == "cli_derived_network_sink"]
    dynamic_net = [f for f in findings if f["kind"] == "dynamic_network_call"]

    normalized = json.dumps(findings, sort_keys=True, separators=(",", ":")).encode("utf-8")
    report = {
        "schema": "WS-PR62-STATIC-SECURITY-SINK-AUDIT-V1",
        "scope": "diagnostic supplement to CodeQL; scans selected PR #62 Python roots",
        "scanned_python_file_count": len(files),
        "finding_count": len(findings),
        "high_review_count": len(high_review),
        "cli_derived_filesystem_sink_count": len(cli_fs),
        "cli_derived_network_sink_count": len(cli_net),
        "dynamic_network_call_count": len(dynamic_net),
        "findings_sha256": hashlib.sha256(normalized).hexdigest(),
        "findings": findings,
        "merge_gate_effect": "NONE_DIAGNOSTIC_ONLY",
        "claims_boundary": "This heuristic inventory is not CodeQL and cannot identify, dismiss, or prove remediation of the eight CodeQL medium alerts by itself. It exists to prioritize manual/dataflow triage."
    }
    out = Path(ns.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in [
        "scanned_python_file_count", "finding_count", "high_review_count",
        "cli_derived_filesystem_sink_count", "cli_derived_network_sink_count",
        "dynamic_network_call_count", "findings_sha256", "merge_gate_effect"
    ]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
