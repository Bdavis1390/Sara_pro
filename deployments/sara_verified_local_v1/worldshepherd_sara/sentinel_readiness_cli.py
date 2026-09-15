from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .infrastructure_assurance import canonical_digest
from .sentinel_readiness import READINESS_CLAIMS_BOUNDARY, build_readiness_report


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def build_readiness_bundle(
    *,
    out: Path,
    software_commit: str,
    executed_utc: str,
    operator: str,
    scale_package_count: int = 2000,
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    report = build_readiness_report(scale_package_count=scale_package_count)
    report["software_commit"] = software_commit
    report["executed_utc"] = executed_utc
    report["operator"] = operator

    external = report["external_gate_matrix"]
    scale = report["scale_campaign"]
    integrity = report["integrity_adversarial_campaign"]
    boundary = {
        "schema": "WS-SENTINEL-DATA-BOUNDARY-REPORT-V1",
        "results": report["data_boundary"],
        "claims_boundary": READINESS_CLAIMS_BOUNDARY,
    }

    files: dict[str, dict[str, Any]] = {
        "readiness-report.json": report,
        "external-gate-matrix.json": external,
        "scale-campaign.json": scale,
        "integrity-adversarial-campaign.json": integrity,
        "data-boundary-report.json": boundary,
    }
    for name, payload in files.items():
        _write_json(out / name, payload)

    index = {
        "schema": "WS-SENTINEL-READINESS-EVIDENCE-INDEX-V1",
        "evidence_status": "INTERNAL_SYNTHETIC_SOFTWARE_EVIDENCE",
        "software_commit": software_commit,
        "executed_utc": executed_utc,
        "operator": operator,
        "internal_preparation_gate_pass": report["internal_preparation_gate_pass"],
        "external_operational_gate_pass": report["external_operational_gate_pass"],
        "artifacts": {
            name: canonical_digest(payload)
            for name, payload in sorted(files.items())
        },
        "claims_boundary": READINESS_CLAIMS_BOUNDARY,
    }
    index["index_digest"] = canonical_digest(index)
    _write_json(out / "readiness-evidence-index.json", index)
    (out / "claims-boundary.md").write_text(
        "# WS-SENTINEL Readiness Claims Boundary\n\n"
        + READINESS_CLAIMS_BOUNDARY
        + "\n\n"
        "Internal preparation and external operational readiness are intentionally separate gates.\n",
        encoding="utf-8",
    )
    return index


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed synthetic Sentinel readiness evidence bundle."
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--software-commit", default="UNSPECIFIED")
    parser.add_argument("--executed-utc", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--scale-package-count", type=int, default=2000)
    args = parser.parse_args()

    index = build_readiness_bundle(
        out=args.out,
        software_commit=args.software_commit,
        executed_utc=args.executed_utc,
        operator=args.operator,
        scale_package_count=args.scale_package_count,
    )
    print(json.dumps(index, sort_keys=True))
    if not index["internal_preparation_gate_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
