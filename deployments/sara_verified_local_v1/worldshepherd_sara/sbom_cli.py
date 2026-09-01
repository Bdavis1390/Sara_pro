from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .qualification import canonical_digest

SBOM_EVIDENCE_SCHEMA = "WS-SOFTWARE-SUPPLY-CHAIN-EVIDENCE-V1"
BOM_FORMAT = "CycloneDX"
BOM_SPEC_VERSION = "1.5"
EVIDENCE_STATUS = "INTERNAL_CI_GENERATED_UNSIGNED"

CLAIMS_BOUNDARY = (
    "Software SBOM evidence is generated from CI dependency-freeze and repository input files only. "
    "It supports internal supply-chain visibility and release custody, but it does not establish a complete "
    "or hermetic software bill of materials, vulnerability remediation, license legal review, SLSA compliance, "
    "CMMC/NIST/DFARS conformity, certification, accreditation, external reproduction, supplier approval, "
    "partner validation, field performance, hardware performance, classified access, or operational authority."
)

NOT_CLAIMED = [
    "complete_or_hermetic_sbom",
    "vulnerability_scan_pass",
    "vulnerability_remediation_complete",
    "license_legal_review",
    "slsa_compliance",
    "cmmc_conformity",
    "nist_800_171_implementation",
    "dfars_satisfaction",
    "fedramp_authorization",
    "iso_certification",
    "soc2_attestation",
    "partner_validation",
    "supplier_approval",
    "external_reproduction",
    "field_or_hardware_performance",
]

PEP508_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(@|==|===|~=|!=|<=|>=|<|>)")


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(value), encoding="utf-8")


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"required file missing for digest: {path}")
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _optional_file_digest(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        raise ValueError(f"optional input was supplied but does not exist: {path}")
    return {
        "path": str(path),
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _normalize_name(value: str) -> str:
    cleaned = value.strip().replace("_", "-")
    return cleaned.lower()


def _parse_freeze_line(line: str, index: int) -> dict[str, Any] | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    source = "pip_freeze"
    version: str | None = None
    name: str
    purl: str | None = None

    if raw.startswith("-e "):
        source = "editable"
        editable = raw[3:].strip()
        if "#egg=" in editable:
            name = editable.rsplit("#egg=", 1)[1].strip()
        else:
            name = Path(editable).name or f"editable-{index}"
        version = None
    elif "===" in raw:
        name, version = raw.split("===", 1)
    elif "==" in raw:
        name, version = raw.split("==", 1)
    elif " @ " in raw:
        name, _url = raw.split(" @ ", 1)
        version = None
        source = "direct_reference"
    else:
        match = PEP508_NAME_RE.match(raw)
        if match:
            name = match.group(1)
        else:
            name = raw.split()[0] if raw.split() else f"unparsed-{index}"
            source = "unparsed_freeze_entry"

    name = _normalize_name(name)
    if version:
        version = version.strip()
        purl = f"pkg:pypi/{name}@{version}"

    component: dict[str, Any] = {
        "type": "library",
        "name": name,
        "bom-ref": f"pkg:pypi/{name}@{version}" if version else f"pkg:pypi/{name}",
        "properties": [
            {"name": "worldshepherd:source_line_index", "value": str(index)},
            {"name": "worldshepherd:source", "value": source},
            {"name": "worldshepherd:raw_freeze_line_sha256", "value": hashlib.sha256(raw.encode("utf-8")).hexdigest()},
        ],
    }
    if version:
        component["version"] = version
    if purl:
        component["purl"] = purl
    return component


def parse_dependency_freeze(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"dependency freeze file is required: {path}")
    components: list[dict[str, Any]] = []
    seen_refs: set[str] = set()
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        component = _parse_freeze_line(line, index)
        if component is None:
            continue
        ref = component["bom-ref"]
        if ref in seen_refs:
            continue
        seen_refs.add(ref)
        components.append(component)
    if not components:
        raise ValueError("dependency freeze did not produce any SBOM components")
    return sorted(components, key=lambda item: (item["name"], item.get("version", "")))


def build_sbom_evidence(
    *,
    dependency_freeze: Path,
    pyproject: Path | None,
    runtime_constraints: Path | None,
    ci_constraints: Path | None,
    repository: str,
    commit_sha: str,
    operator: str,
    executed_utc: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not commit_sha:
        raise ValueError("commit_sha is required")

    generated_at = executed_utc or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    components = parse_dependency_freeze(dependency_freeze)
    input_files = {
        "dependency_freeze": _optional_file_digest(dependency_freeze),
        "pyproject": _optional_file_digest(pyproject),
        "runtime_constraints": _optional_file_digest(runtime_constraints),
        "ci_constraints": _optional_file_digest(ci_constraints),
    }

    sbom: dict[str, Any] = {
        "bomFormat": BOM_FORMAT,
        "specVersion": BOM_SPEC_VERSION,
        "version": 1,
        "metadata": {
            "timestamp": generated_at,
            "component": {
                "type": "application",
                "name": "worldshepherd-sara",
                "version": "0.1.0",
                "bom-ref": "pkg:pypi/worldshepherd-sara@0.1.0",
            },
            "tools": [
                {
                    "vendor": "Worldshepherd / SARA",
                    "name": "ws-sbom-evidence",
                    "version": "1",
                }
            ],
            "properties": [
                {"name": "worldshepherd:repository", "value": repository},
                {"name": "worldshepherd:commit_sha", "value": commit_sha},
                {"name": "worldshepherd:evidence_status", "value": EVIDENCE_STATUS},
            ],
        },
        "components": components,
        "properties": [
            {"name": "worldshepherd:schema", "value": SBOM_EVIDENCE_SCHEMA},
            {"name": "worldshepherd:claims_boundary", "value": CLAIMS_BOUNDARY},
            {"name": "worldshepherd:not_claimed", "value": ",".join(NOT_CLAIMED)},
        ],
    }

    summary: dict[str, Any] = {
        "schema": SBOM_EVIDENCE_SCHEMA,
        "generated_utc": generated_at,
        "repository": repository,
        "commit_sha": commit_sha,
        "operator": operator,
        "bom_format": BOM_FORMAT,
        "bom_spec_version": BOM_SPEC_VERSION,
        "evidence_status": EVIDENCE_STATUS,
        "component_count": len(components),
        "component_names": [component["name"] for component in components],
        "input_files": input_files,
        "claims_boundary": CLAIMS_BOUNDARY,
        "not_claimed": NOT_CLAIMED,
    }
    summary["summary_digest"] = canonical_digest(summary)
    return sbom, summary


def write_sbom_evidence(
    *,
    out_dir: Path,
    dependency_freeze: Path,
    pyproject: Path | None,
    runtime_constraints: Path | None,
    ci_constraints: Path | None,
    repository: str,
    commit_sha: str,
    operator: str,
    executed_utc: str | None = None,
) -> dict[str, Any]:
    sbom, summary = build_sbom_evidence(
        dependency_freeze=dependency_freeze,
        pyproject=pyproject,
        runtime_constraints=runtime_constraints,
        ci_constraints=ci_constraints,
        repository=repository,
        commit_sha=commit_sha,
        operator=operator,
        executed_utc=executed_utc,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    sbom_path = out_dir / "software-sbom.json"
    summary_path = out_dir / "sbom-evidence-summary.json"
    _write_json(sbom_path, sbom)

    summary["software_sbom_path"] = str(sbom_path)
    summary["software_sbom_sha256"] = _sha256_file(sbom_path)
    summary["summary_digest"] = canonical_digest(summary)
    _write_json(summary_path, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate internal SARA software SBOM evidence from CI dependency freeze.")
    parser.add_argument("--dependency-freeze", type=Path, required=True, help="Path to pip freeze output.")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for SBOM evidence files.")
    parser.add_argument("--pyproject", type=Path, default=None, help="Optional pyproject.toml path to digest into evidence.")
    parser.add_argument("--runtime-constraints", type=Path, default=None, help="Optional runtime constraints file to digest.")
    parser.add_argument("--ci-constraints", type=Path, default=None, help="Optional CI constraints file to digest.")
    parser.add_argument("--repository", default="", help="Repository full name.")
    parser.add_argument("--commit-sha", required=True, help="Commit SHA for the CI run.")
    parser.add_argument("--operator", default="github-actions", help="Evidence operator.")
    parser.add_argument("--executed-utc", default=None, help="Optional fixed execution timestamp.")
    args = parser.parse_args(argv)

    summary = write_sbom_evidence(
        out_dir=args.out,
        dependency_freeze=args.dependency_freeze,
        pyproject=args.pyproject,
        runtime_constraints=args.runtime_constraints,
        ci_constraints=args.ci_constraints,
        repository=args.repository,
        commit_sha=args.commit_sha,
        operator=args.operator,
        executed_utc=args.executed_utc,
    )
    print(_json_text(summary), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
