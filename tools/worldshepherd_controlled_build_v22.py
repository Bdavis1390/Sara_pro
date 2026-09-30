#!/usr/bin/env python3
"""Worldshepherd V22 controlled-build evidence generator.

This tool is intentionally conservative. It converts a pip resolver report into
candidate reproducibility evidence only when the repository's exact runtime
constraints fully cover the resolved dependency graph and every remote artifact
carries a SHA-256 from the package index. It never marks production readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import tomllib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONSTRAINT_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)(?:\[[A-Za-z0-9_,.-]+\])?==(?P<version>[A-Za-z0-9][A-Za-z0-9._+!-]*)$"
)
NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
LOCAL_PROJECT = "worldshepherd-sara"
SCHEMA = "WS-CONTROLLED-BUILD-EVIDENCE-V22"


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_constraints(path: Path) -> dict[str, dict[str, str]]:
    pins: dict[str, dict[str, str]] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ";" in line or " @ " in line:
            raise ValueError(f"{path}:{lineno}: markers/URLs are not allowed in the V22 runtime constraint set")
        m = CONSTRAINT_RE.fullmatch(line)
        if not m:
            raise ValueError(f"{path}:{lineno}: dependency must be an exact == pin: {line}")
        name = canonical_name(m.group("name"))
        if name in pins:
            raise ValueError(f"{path}:{lineno}: duplicate dependency pin: {name}")
        pins[name] = {"name": m.group("name"), "version": m.group("version"), "line": line}
    if not pins:
        raise ValueError("runtime constraints are empty")
    return pins


def _dependency_name(spec: str) -> str:
    m = NAME_RE.match(spec)
    if not m:
        raise ValueError(f"cannot parse dependency name: {spec}")
    return canonical_name(m.group(1))


def audit_pyproject(pyproject: Path, pins: dict[str, dict[str, str]]) -> dict[str, Any]:
    doc = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = doc.get("project", {})
    deps = project.get("dependencies", [])
    if not isinstance(deps, list):
        raise ValueError("project.dependencies must be a list")
    direct = sorted({_dependency_name(str(x)) for x in deps})
    missing = sorted(set(direct) - set(pins))
    if missing:
        raise ValueError(f"exact constraints do not cover direct runtime dependencies: {missing}")
    build_requires = doc.get("build-system", {}).get("requires", [])
    for requirement in build_requires:
        req = str(requirement).strip()
        if "==" not in req or any(op in req for op in (">=", "<=", "~=", "!=", "<", ">")):
            raise ValueError(f"build-system requirement is not exact: {req}")
    return {
        "project_name": canonical_name(str(project.get("name", ""))),
        "project_version": str(project.get("version", "")),
        "direct_runtime_dependencies": direct,
        "build_system_requires": [str(x) for x in build_requires],
    }


def _sha256_from_download_info(item: dict[str, Any]) -> str | None:
    info = item.get("download_info") or {}
    archive = info.get("archive_info") or {}
    hashes = archive.get("hashes") or {}
    value = hashes.get("sha256")
    if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value):
        return value.lower()
    legacy = archive.get("hash")
    if isinstance(legacy, str) and legacy.startswith("sha256="):
        candidate = legacy.split("=", 1)[1]
        if re.fullmatch(r"[0-9a-fA-F]{64}", candidate):
            return candidate.lower()
    return None


def verify_resolver_report(report: dict[str, Any], pins: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    installs = report.get("install")
    if not isinstance(installs, list) or not installs:
        raise ValueError("pip resolver report has no install records")
    resolved: dict[str, dict[str, str]] = {}
    for item in installs:
        if not isinstance(item, dict):
            raise ValueError("invalid install record")
        metadata = item.get("metadata") or {}
        name = canonical_name(str(metadata.get("name", "")))
        version = str(metadata.get("version", ""))
        if not name or not version:
            raise ValueError("resolver item is missing package name/version")
        info = item.get("download_info") or {}
        url = str(info.get("url", ""))
        is_local = url.startswith("file:") and name == LOCAL_PROJECT
        if is_local:
            continue
        if name not in pins:
            raise ValueError(f"resolver produced package not present in exact constraints: {name}=={version}")
        expected = pins[name]["version"]
        if version != expected:
            raise ValueError(f"resolver version mismatch for {name}: {version} != {expected}")
        digest = _sha256_from_download_info(item)
        if not digest:
            raise ValueError(f"resolver item lacks SHA-256 artifact hash: {name}=={version}")
        prior = resolved.get(name)
        current = {"name": name, "version": version, "sha256": digest}
        if prior and prior != current:
            raise ValueError(f"conflicting resolver records for {name}")
        resolved[name] = current
    missing = sorted(set(pins) - set(resolved))
    if missing:
        raise ValueError(f"exact constraints contain packages absent from the resolved graph: {missing}")
    return [resolved[name] for name in sorted(resolved)]


def write_hash_lock(path: Path, resolved: list[dict[str, str]]) -> None:
    lines = [
        "# Worldshepherd V22 candidate runtime hash lock",
        "# Generated from a pip 26.2.1 resolver report; production credit requires independent verification.",
    ]
    for item in resolved:
        lines.append(f"{item['name']}=={item['version']} --hash=sha256:{item['sha256']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_cyclonedx(project: dict[str, Any], resolved: list[dict[str, str]]) -> dict[str, Any]:
    components = []
    for item in resolved:
        components.append({
            "type": "library",
            "name": item["name"],
            "version": item["version"],
            "hashes": [{"alg": "SHA-256", "content": item["sha256"]}],
            "purl": f"pkg:pypi/{item['name']}@{item['version']}",
        })
    canonical = json.dumps(components, sort_keys=True, separators=(",", ":")).encode()
    serial = uuid.uuid5(uuid.NAMESPACE_URL, hashlib.sha256(canonical).hexdigest())
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": project["project_name"] or LOCAL_PROJECT,
                "version": project["project_version"] or "UNKNOWN",
            },
            "properties": [
                {"name": "worldshepherd:evidence-status", "value": "CONTROLLED_BUILD_CANDIDATE"},
                {"name": "worldshepherd:production-credit", "value": "false"},
            ],
        },
        "components": components,
    }


def run_build(root: Path, report_path: Path, output_dir: Path, source_commit: str) -> dict[str, Any]:
    constraints = root / "deployments/sara_verified_local_v1/constraints-runtime.txt"
    pyproject = root / "deployments/sara_verified_local_v1/pyproject.toml"
    pins = parse_constraints(constraints)
    project = audit_pyproject(pyproject, pins)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    resolved = verify_resolver_report(report, pins)

    output_dir.mkdir(parents=True, exist_ok=True)
    lock = output_dir / "requirements-runtime-hashed.txt"
    sbom = output_dir / "worldshepherd-sara-runtime.cdx.json"
    manifest = output_dir / "controlled-build-manifest.json"
    write_hash_lock(lock, resolved)
    sbom.write_text(json.dumps(build_cyclonedx(project, resolved), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    generated_at = os.environ.get("WS_EVIDENCE_TIMESTAMP") or datetime.now(timezone.utc).isoformat()
    evidence = {
        "schema": SCHEMA,
        "evidence_status": "CONTROLLED_BUILD_CANDIDATE",
        "production_credit": False,
        "source_commit": source_commit,
        "generated_at": generated_at,
        "builder": {
            "github_repository": os.environ.get("GITHUB_REPOSITORY"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
            "python": platform.python_version(),
            "pip": os.environ.get("WS_PIP_VERSION", "UNKNOWN"),
        },
        "inputs": {
            "constraints": str(constraints.relative_to(root)),
            "constraints_sha256": sha256_file(constraints),
            "pyproject": str(pyproject.relative_to(root)),
            "pyproject_sha256": sha256_file(pyproject),
            "resolver_report_sha256": sha256_file(report_path),
        },
        "resolved_component_count": len(resolved),
        "outputs": {
            "hash_lock": lock.name,
            "hash_lock_sha256": sha256_file(lock),
            "cyclonedx_sbom": sbom.name,
            "cyclonedx_sbom_sha256": sha256_file(sbom),
        },
        "claims_boundary": (
            "Candidate controlled-build evidence only. This record does not establish production readiness, "
            "independent validation, non-exportable signer custody, trusted time, external rollback anchors, "
            "host attestation, or an independent adversarial assessment."
        ),
    }
    manifest.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("--root", default=".")
    p.add_argument("--report", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--source-commit", required=True)
    ns = ap.parse_args()
    if ns.cmd == "build":
        evidence = run_build(Path(ns.root).resolve(), Path(ns.report).resolve(), Path(ns.output_dir).resolve(), ns.source_commit)
        print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
