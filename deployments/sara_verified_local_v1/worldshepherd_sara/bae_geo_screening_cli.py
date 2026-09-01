from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .geo_provenance import build_geo_prov_bundle
from .qualification import canonical_digest

REQUIRED_OUTPUTS = {
    "manifest.json",
    "qualification-summary.json",
    "bae-evidence-overlay.json",
    "claims-boundary.md",
    "interface-control-description.md",
    "threat-model.md",
    "nist-cmmc-dfars-gap-map.md",
    "data-rights-ip-markings.md",
    "external-validation-route.md",
    "replay-instructions.md",
}

PROHIBITED_ASSERTIONS = (
    "BAE_VALIDATED",
    "BAE_CERTIFIED",
    "BAE_APPROVED",
    "BAE_ADOPTED",
    "CMMC_CERTIFIED",
    "NIST_800_171_CONFORMANT",
    "SUPPLIER_APPROVED",
    "CLASSIFIED_ACCESS_GRANTED",
)


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(_json_text(value), encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def _file_digest(path: Path) -> str:
    return canonical_digest({"path": path.name, "content": path.read_text(encoding="utf-8")})


def _assert_sanitized_text(text: str) -> None:
    upper = text.upper()
    for assertion in PROHIBITED_ASSERTIONS:
        if assertion in upper:
            raise ValueError(f"screening package contains prohibited assertion: {assertion}")


def _assert_bundle_claims_boundary(bundle: dict[str, Any]) -> None:
    boundary = "\n".join(str(item) for item in bundle.get("claims_boundary", []))
    required_fragments = [
        "No BAE interest",
        "No supplier cybersecurity conformity",
    ]
    for fragment in required_fragments:
        if fragment not in boundary:
            raise ValueError(f"missing required claims-boundary fragment: {fragment}")


def build_screening_package(bundle: dict[str, Any]) -> dict[str, str | dict[str, Any]]:
    """Create non-confidential BAE screening package artifacts from a GEO bundle.

    The output is intentionally a screening package, not a proposal, certification,
    endorsement record, operational validation, or evidence of BAE interest.
    """
    _assert_bundle_claims_boundary(bundle)
    overlay = bundle.get("bae_evidence_overlay")
    if not isinstance(overlay, dict):
        raise ValueError("geo qualification bundle missing bae_evidence_overlay")
    evidence = bundle.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("geo qualification bundle missing evidence records")

    source_digest = bundle.get("bundle_digest") or canonical_digest(bundle)
    summary = {
        "schema": "WS-BAE-GEO-SCREENING-SUMMARY-V1",
        "source_bundle_digest": source_digest,
        "requirement_delta_id": bundle["requirement"]["requirement_delta_id"],
        "test_id": evidence[0]["test_id"],
        "evidence_scope": evidence[0]["evidence_scope"],
        "capability_status": evidence[0]["capability_status"],
        "current_maturity": "INTERNAL SOFTWARE EVIDENCE / SIMULATED REPLAY / REQUIRES EXTERNAL VALIDATION",
        "negative_evidence_retained": evidence[0].get("negative_evidence", []),
        "bae_lane": overlay.get("bae_lane", []),
        "worldshepherd_asset": overlay.get("worldshepherd_asset", []),
        "missing_validation": overlay.get("missing_validation", []),
        "strongest_bae_pathway": overlay.get("strongest_bae_pathway", []),
        "claim_boundary": bundle.get("claims_boundary", []),
    }
    artifacts: dict[str, str | dict[str, Any]] = {
        "qualification-summary.json": summary,
        "bae-evidence-overlay.json": {
            "schema": "WS-BAE-GEO-EVIDENCE-OVERLAY-V1",
            "source_bundle_digest": source_digest,
            "overlay": overlay,
            "claim_boundary": [
                "The overlay is a screening/readiness artifact only.",
                "It does not evidence BAE interest, endorsement, adoption, validation, certification, classified access, supplier approval, or cybersecurity conformity.",
            ],
        },
        "claims-boundary.md": """
# WS-BAE-GEO Screening Claims Boundary

This package is a non-confidential screening/readiness artifact derived from the `WS-GEO-PROV-001A` simulated qualification bundle.

It may support discussion of a mission-context provenance pattern for heterogeneous environmental/geospatial evidence, degraded data, source disagreement, null controls, and human-reviewed decisions.

It does not establish:

- BAE Systems interest, endorsement, adoption, partnership, certification, approval, supplier approval, or classified access;
- DOE validation, national-lab validation, independent reproduction, or external acceptance;
- land-restoration performance, emergency-response authority, field-calibrated sensor performance, or hardware/platform performance;
- CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, CUI/CDI handling authorization, or export-control clearance.

Current maturity remains: `INTERNAL SOFTWARE EVIDENCE / SIMULATED REPLAY / REQUIRES EXTERNAL VALIDATION`.
""",
        "interface-control-description.md": """
# Interface Control Description — WS-BAE-GEO-SCREENING-ICD-001

## Inputs

- `geospatial_dataset`: raster, vector, or time-series evidence with provider, dataset version, timestamp, spatial resolution, license/use terms, and retrieval hash.
- `local_sensor_or_ground_truth`: optional evidence with collector, time, location, collection method, confidence, and chain-of-custody note.

## Outputs

- `baseline_record`
- `change_event`
- `uncertainty_record`
- `null_control_record`
- `human_review_record`
- `audit_event`
- `bae_evidence_overlay`

## Timing assumptions

Batch replay only. Near-real-time operation is not claimed.

## Security assumptions

No classified data and no CUI/CDI are used in this package. Access control is a design/readiness topic only unless supported by later documentary evidence.
""",
        "threat-model.md": """
# Threat Model — WS-BAE-GEO-SCREENING-THREAT-001

## Primary abuse/failure modes

- treating simulated evidence as field validation;
- overclaiming BAE/DOE acceptance from thematic fit;
- ingesting stale, altered, or unlicensed datasets;
- suppressing null-control failures or negative evidence;
- omitting uncertainty when source data conflicts;
- leaking protected IP or sensitive partner data into a screening package;
- handling CUI/CDI without an authorized boundary;
- publishing a map layer without source, timestamp, confidence, or review state.

## Controls required before external partner screening

- claims-boundary review;
- SBOM/build-provenance attachment;
- source and output digests;
- role-based access review;
- data-rights/IP marking review;
- CUI/CDI exclusion statement;
- external-validation route.
""",
        "nist-cmmc-dfars-gap-map.md": """
# NIST / CMMC / DFARS Gap Map — Screening Only

This package does not claim CMMC certification, NIST SP 800-171 conformity, DFARS 252.204-7012 satisfaction, or authorized CUI/CDI handling.

## Current internal evidence

- CI and test evidence for software behavior;
- audit/provenance pattern evidence;
- simulated bundle generation and ECHO custody verification.

## Missing supplier-readiness evidence

- defined CUI/CDI boundary;
- system security plan and control implementation evidence;
- SPRS/NIST assessment evidence where applicable;
- incident-response procedure and test record;
- secrets-management evidence;
- SBOM/dependency provenance and secure release artifacts;
- DFARS flowdown review;
- data-rights and IP-marking review;
- export-control screening;
- quality-system evidence;
- facility/personnel clearance determination if a future opportunity requires it.
""",
        "data-rights-ip-markings.md": """
# Data Rights and IP Markings — Screening Package

This package should contain only non-confidential, non-enabling, public/synthetic demonstration content.

## Required markings

- `WORLD-SHEPHERD-INTERNAL-SIMULATED-EVIDENCE`
- `NON-CONFIDENTIAL-SCREENING-VERSION`
- `NO-CUI-NO-CLASSIFIED-DATA`
- `NO-EXTERNAL-VALIDATION-CLAIM`

Any future partner package must be reviewed before transmission for protected IP, export-control sensitivity, proprietary source data, CUI/CDI, and third-party license restrictions.
""",
        "external-validation-route.md": """
# External Validation Route

## Minimum credible next validation

1. Independent replay of the generated package by a technically competent reviewer using only the manifest and public/synthetic inputs.
2. Review of uncertainty, null-control, negative-evidence, and claims-boundary handling.
3. Signed or otherwise attributable reproduction report.
4. Separate security-control review before any supplier-readiness assertion.
5. Field data, sensor data, or hardware evidence only after a bounded partner-approved test plan exists.

External replay can upgrade reproducibility evidence only for the tested software/artifact scope. It does not validate BAE adoption, supplier approval, field performance, or CMMC/NIST conformity.
""",
        "replay-instructions.md": """
# Replay Instructions — WS-BAE-GEO-SCREENING-BUNDLE-001

## Source

Start from a generated `geo_prov_qualification_bundle.json` emitted by `ws-pre-bloom` or from a freshly generated internal synthetic GEO bundle.

## Expected checks

- requirement delta is `PRE-RD-2026-0020`;
- test is `WS-GEO-PROV-001A`;
- evidence scope is `SIMULATION`;
- capability status is `SIMULATED_ONLY`;
- null control is preserved;
- BAE validation remains negative evidence;
- claims boundary states no BAE interest or supplier cybersecurity conformity.

## Output

The package exports markdown and JSON artifacts for partner-screening discussion only.
""",
    }
    return artifacts


def export_screening_package(bundle: dict[str, Any], out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    artifacts = build_screening_package(bundle)
    for filename, value in artifacts.items():
        target = out / filename
        if isinstance(value, dict):
            _write_json(target, value)
        else:
            _assert_sanitized_text(value)
            _write_text(target, value)

    artifact_digests = {filename: _file_digest(out / filename) for filename in sorted(artifacts)}
    manifest = {
        "schema": "WS-BAE-GEO-SCREENING-MANIFEST-V1",
        "package_id": "WS-BAE-GEO-SCREENING-BUNDLE-001",
        "source_bundle_digest": bundle.get("bundle_digest") or canonical_digest(bundle),
        "output_files": sorted(REQUIRED_OUTPUTS - {"manifest.json"}),
        "artifact_digests": artifact_digests,
        "claim_boundary": [
            "Screening package only.",
            "No partner validation, supplier approval, external reproduction, field performance, or cybersecurity conformity is claimed.",
        ],
    }
    _write_json(out / "manifest.json", manifest)
    manifest["artifact_digests"]["manifest.json"] = _file_digest(out / "manifest.json")
    _write_json(out / "manifest.json", manifest)
    return manifest


def _load_bundle(path: Path | None, *, software_commit: str, executed_utc: str, operator: str) -> dict[str, Any]:
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    return build_geo_prov_bundle(
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a sanitized BAE GEO screening package")
    parser.add_argument("--bundle", type=Path, default=None, help="Optional geo_prov_qualification_bundle.json input")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--software-commit", default=os.getenv("GITHUB_SHA", "UNKNOWN"))
    parser.add_argument("--executed-utc", required=True)
    parser.add_argument("--operator", default="worldshepherd-bae-geo-screening-cli")
    args = parser.parse_args()
    bundle = _load_bundle(
        args.bundle,
        software_commit=args.software_commit,
        executed_utc=args.executed_utc,
        operator=args.operator,
    )
    manifest = export_screening_package(bundle, args.out)
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
