from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tomllib
from collections import Counter
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


EVALUATOR_HANDOFF_SCHEMA = "ws-evaluator-handoff-1"

_EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}

_TEXT_SUFFIXES = {
    ".css",
    ".env",
    ".example",
    ".html",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


class ContractStatus(str, Enum):
    NO_CURRENT_CONTRACT_CLAIMED = "NO_CURRENT_CONTRACT_CLAIMED"
    CONTRACT_EXISTS_DISCLOSED = "CONTRACT_EXISTS_DISCLOSED"
    DISCLOSURE_RESTRICTED = "DISCLOSURE_RESTRICTED"
    UNKNOWN_REQUIRES_REVIEW = "UNKNOWN_REQUIRES_REVIEW"


class CodeInventory(BaseModel):
    inventory_root: str
    file_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    text_file_count: int = Field(ge=0)
    text_line_count: int = Field(ge=0)
    suffix_counts: dict[str, int]
    excluded_parts: list[str]


class ProjectRequirements(BaseModel):
    project_name: str
    project_version: str
    requires_python: str
    dependencies: list[str]
    test_dependencies: list[str]


class EvaluatorHandoffManifest(BaseModel):
    schema_version: str = EVALUATOR_HANDOFF_SCHEMA
    artifact_id: str = Field(min_length=1, max_length=160)
    generated_utc: str = Field(min_length=20, max_length=40)
    repository: str = Field(min_length=1, max_length=200)
    release_ref: str = Field(min_length=1, max_length=200)
    release_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    package_root: str = Field(min_length=1, max_length=300)
    code_inventory: CodeInventory
    project_requirements: ProjectRequirements
    hardware_requirements: list[str] = Field(min_length=1)
    delivery_method: str = Field(min_length=1, max_length=2000)
    install_run_instructions: list[str] = Field(min_length=1)
    fixture_refs: list[str] = Field(min_length=1)
    expected_results_ref: str = Field(min_length=1, max_length=500)
    claims_boundary_refs: list[str] = Field(min_length=1)
    evaluation_scope: str = Field(min_length=1, max_length=4000)
    evaluation_window: str = Field(min_length=1, max_length=500)
    contract_status: ContractStatus
    conflict_disclosure_notes: list[str] = Field(default_factory=list)
    non_claims: list[str] = Field(min_length=1)


def _should_skip(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return path.is_symlink() or any(part in _EXCLUDED_PARTS for part in relative.parts)


def inventory_package(root: str | Path) -> CodeInventory:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError(f"inventory root is not a directory: {root_path}")

    file_count = 0
    total_bytes = 0
    text_file_count = 0
    text_line_count = 0
    suffix_counts: Counter[str] = Counter()

    for path in sorted(root_path.rglob("*")):
        if not path.is_file() or _should_skip(path, root_path):
            continue
        file_count += 1
        total_bytes += path.stat().st_size
        suffix = path.suffix.lower() or "<none>"
        suffix_counts[suffix] += 1
        if suffix in _TEXT_SUFFIXES:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            text_file_count += 1
            text_line_count += len(text.splitlines())

    return CodeInventory(
        inventory_root=str(root_path),
        file_count=file_count,
        total_bytes=total_bytes,
        text_file_count=text_file_count,
        text_line_count=text_line_count,
        suffix_counts=dict(sorted(suffix_counts.items())),
        excluded_parts=sorted(_EXCLUDED_PARTS),
    )


def discover_project_requirements(root: str | Path) -> ProjectRequirements:
    root_path = Path(root).resolve()
    pyproject_path = root_path / "pyproject.toml"
    if not pyproject_path.is_file():
        raise ValueError(f"missing pyproject.toml: {pyproject_path}")

    with pyproject_path.open("rb") as handle:
        data = tomllib.load(handle)

    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml missing [project] table")

    optional = project.get("optional-dependencies", {})
    test_dependencies = optional.get("test", []) if isinstance(optional, dict) else []
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list) or not isinstance(test_dependencies, list):
        raise ValueError("project dependencies must be lists")

    return ProjectRequirements(
        project_name=str(project.get("name", "")),
        project_version=str(project.get("version", "")),
        requires_python=str(project.get("requires-python", "")),
        dependencies=[str(item) for item in dependencies],
        test_dependencies=[str(item) for item in test_dependencies],
    )


def resolve_git_commit(root: str | Path) -> str:
    root_path = Path(root).resolve()
    completed = subprocess.run(
        ["git", "-C", str(root_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    commit = completed.stdout.strip().lower()
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        raise ValueError(f"git returned an invalid commit SHA: {commit!r}")
    return commit


def build_evaluator_handoff(
    *,
    package_root: str | Path,
    artifact_id: str,
    repository: str,
    release_ref: str,
    hardware_requirements: list[str],
    delivery_method: str,
    fixture_refs: list[str],
    expected_results_ref: str,
    evaluation_scope: str,
    evaluation_window: str,
    contract_status: ContractStatus,
    conflict_disclosure_notes: list[str] | None = None,
    claims_boundary_refs: list[str] | None = None,
    install_run_instructions: list[str] | None = None,
    release_commit: str | None = None,
    generated_utc: str | None = None,
) -> EvaluatorHandoffManifest:
    root_path = Path(package_root).resolve()
    commit = (release_commit or resolve_git_commit(root_path)).lower()
    generated = generated_utc or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )

    return EvaluatorHandoffManifest(
        artifact_id=artifact_id,
        generated_utc=generated,
        repository=repository,
        release_ref=release_ref,
        release_commit=commit,
        package_root=str(root_path),
        code_inventory=inventory_package(root_path),
        project_requirements=discover_project_requirements(root_path),
        hardware_requirements=hardware_requirements,
        delivery_method=delivery_method,
        install_run_instructions=install_run_instructions
        or [
            "python -m venv .venv",
            "source .venv/bin/activate",
            "python -m pip install -e '.[test]'",
            "python -m pytest -q",
        ],
        fixture_refs=fixture_refs,
        expected_results_ref=expected_results_ref,
        claims_boundary_refs=claims_boundary_refs
        or [
            "docs/COMPLIANCE_BOUNDARY.md",
            "../../docs/CLAIMS_AND_EVIDENCE_POLICY.md",
        ],
        evaluation_scope=evaluation_scope,
        evaluation_window=evaluation_window,
        contract_status=contract_status,
        conflict_disclosure_notes=conflict_disclosure_notes or [],
        non_claims=[
            "This handoff manifest is not independent validation or evaluator acceptance.",
            "Repository/code inventory is not a runtime memory, latency, throughput, hardware-performance, or operational-effectiveness measurement.",
            "Internal tests and CI do not establish government/customer acceptance, CMMC/NIST/DFARS conformity, classified/CUI readiness, or physical capability.",
            "The evaluator must independently determine conflicts of interest and the scope of any resulting attestation.",
        ],
    )


def manifest_payload(manifest: EvaluatorHandoffManifest) -> dict[str, Any]:
    return manifest.model_dump(mode="json", exclude_none=True)


def manifest_digest(manifest: EvaluatorHandoffManifest) -> str:
    payload = json.dumps(
        manifest_payload(manifest),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a bounded evaluator-handoff manifest for Worldshepherd SARA."
    )
    parser.add_argument("--package-root", default=".")
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--repository", default="Bdavis1390/Sara_pro")
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--release-commit")
    parser.add_argument("--hardware-requirement", action="append", required=True)
    parser.add_argument("--delivery-method", required=True)
    parser.add_argument("--fixture", action="append", required=True)
    parser.add_argument("--expected-results-ref", required=True)
    parser.add_argument("--claims-boundary-ref", action="append")
    parser.add_argument("--run-instruction", action="append")
    parser.add_argument("--evaluation-scope", required=True)
    parser.add_argument("--evaluation-window", required=True)
    parser.add_argument(
        "--contract-status",
        choices=[item.value for item in ContractStatus],
        required=True,
    )
    parser.add_argument("--conflict-note", action="append")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    manifest = build_evaluator_handoff(
        package_root=args.package_root,
        artifact_id=args.artifact_id,
        repository=args.repository,
        release_ref=args.release_ref,
        release_commit=args.release_commit,
        hardware_requirements=args.hardware_requirement,
        delivery_method=args.delivery_method,
        fixture_refs=args.fixture,
        expected_results_ref=args.expected_results_ref,
        claims_boundary_refs=args.claims_boundary_ref,
        install_run_instructions=args.run_instruction,
        evaluation_scope=args.evaluation_scope,
        evaluation_window=args.evaluation_window,
        contract_status=ContractStatus(args.contract_status),
        conflict_disclosure_notes=args.conflict_note,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "manifest": manifest_payload(manifest),
        "manifest_sha256": manifest_digest(manifest),
    }
    output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
