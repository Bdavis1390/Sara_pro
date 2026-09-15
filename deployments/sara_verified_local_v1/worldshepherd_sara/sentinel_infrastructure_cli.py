from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .infrastructure_assurance import (
    CLAIMS_BOUNDARY,
    EVIDENCE_STATUS,
    build_synthetic_packages,
    canonical_digest,
    run_gate,
)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def build_evidence_bundle(
    *,
    out: Path,
    campaign_id: str,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    report = run_gate(campaign_id=campaign_id)

    packages = build_synthetic_packages(24)
    scenario = {
        "schema": "WS-SENTINEL-SYNTHETIC-SCENARIO-V1",
        "campaign_id": campaign_id,
        "evidence_status": EVIDENCE_STATUS,
        "corridor_name": "DEMO-CORRIDOR-ALPHA",
        "synthetic_only": True,
        "segment_count": 12,
        "work_package_count": len(packages),
        "subcontractor_count": 4,
        "failure_classes": [item.failure_id for item in report.failure_results],
        "packages": [item.model_dump(mode="json") for item in packages],
        "claims_boundary": CLAIMS_BOUNDARY,
    }
    gate_payload = report.model_dump(mode="json", by_alias=True)
    failure_payload = {
        "schema": "WS-SENTINEL-FAILURE-RESULTS-V1",
        "campaign_id": campaign_id,
        "results": [item.model_dump(mode="json") for item in report.failure_results],
        "claims_boundary": CLAIMS_BOUNDARY,
    }
    provenance = {
        "schema": "WS-SENTINEL-DEMO-PROVENANCE-V1",
        "campaign_id": campaign_id,
        "software_commit": software_commit,
        "executed_utc": executed_utc,
        "operator": operator,
        "evidence_status": EVIDENCE_STATUS,
        "claims_boundary": CLAIMS_BOUNDARY,
    }

    files = {
        "scenario-manifest.json": scenario,
        "gate-report.json": gate_payload,
        "failure-results.json": failure_payload,
        "software-provenance.json": provenance,
    }
    for name, payload in files.items():
        _write_json(out / name, payload)

    index = {
        "schema": "WS-SENTINEL-DEMO-EVIDENCE-INDEX-V1",
        "campaign_id": campaign_id,
        "evidence_status": EVIDENCE_STATUS,
        "pass_gate": report.pass_gate,
        "artifacts": {
            name: canonical_digest(payload)
            for name, payload in sorted(files.items())
        },
        "claims_boundary": CLAIMS_BOUNDARY,
    }
    index["index_digest"] = canonical_digest(index)
    _write_json(out / "evidence-index.json", index)
    (out / "claims-boundary.md").write_text(
        "# WS-SENTINEL-DEMO-G1 Claims Boundary\n\n"
        + CLAIMS_BOUNDARY
        + "\n\n"
        "The demonstration uses synthetic data only and is not a government or prime acceptance test.\n",
        encoding="utf-8",
    )
    return index


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the claims-controlled synthetic Sentinel infrastructure assurance G1 evidence bundle."
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--campaign-id", default="WS-SENTINEL-DEMO-G1")
    parser.add_argument("--software-commit", default="UNSPECIFIED")
    parser.add_argument("--executed-utc", required=True)
    parser.add_argument("--operator", required=True)
    args = parser.parse_args()

    index = build_evidence_bundle(
        out=args.out,
        campaign_id=args.campaign_id,
        software_commit=args.software_commit,
        executed_utc=args.executed_utc,
        operator=args.operator,
    )
    print(json.dumps(index, sort_keys=True))
    if not index["pass_gate"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
