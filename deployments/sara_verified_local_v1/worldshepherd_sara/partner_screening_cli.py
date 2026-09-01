from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .geo_provenance import build_geo_prov_bundle
from .qualification import canonical_digest

REQUIRED_OUTPUTS = {
    "manifest.json",
    "qualification-summary.json",
    "partner-evidence-overlay.json",
    "claims-boundary.md",
    "interface-control-description.md",
    "threat-model.md",
    "compliance-gap-map.md",
    "data-rights-ip-markings.md",
    "external-validation-route.md",
    "replay-instructions.md",
}

PARTNER_PRESETS: dict[str, dict[str, Any]] = {
    "BAE_SYSTEMS": {
        "display_name": "BAE Systems",
        "business_lanes": [
            "C5ISR",
            "autonomy",
            "AI/edge AI",
            "electronic warfare/spectrum",
            "cyber",
            "assured PNT/DDIL",
            "digital engineering",
            "digital twins/CBM+",
            "resilient communications",
            "advanced manufacturing",
            "distributed sensing",
            "mission engineering",
            "secure software supply chain",
        ],
        "pathways": [
            "Mission Advantage",
            "FAST Labs Technology Scouting",
            "RIVETS",
            "Combat Mission Systems Virtual Proving Ground / plugfest",
            "ADAPT/ADAMS",
        ],
        "supplier_readiness_gates": [
            "SAM/CAGE and small-business status where applicable",
            "CUI/CDI boundary statement",
            "DFARS 252.204-7012 flowdown assessment",
            "CMMC 2.0 status",
            "NIST SP 800-171 assessment evidence",
            "SBOM/dependency provenance",
            "secure build/release evidence",
            "incident response",
            "secrets management",
            "data-rights/IP markings",
            "export-control screening",
            "quality program",
            "supplier onboarding",
            "facility/personnel clearance if required",
        ],
    },
    "GENERIC_PRIME": {
        "display_name": "Generic prime/integration partner",
        "business_lanes": [
            "mission engineering",
            "secure software supply chain",
            "digital engineering",
            "autonomy support",
            "distributed sensing",
            "resilient operations",
        ],
        "pathways": [
            "technology scouting",
            "partner screening",
            "integration lab",
            "synthetic demonstration",
        ],
        "supplier_readiness_gates": [
            "business registration status",
            "cybersecurity boundary statement",
            "SBOM/dependency provenance",
            "secure build/release evidence",
            "data-rights/IP markings",
            "export-control screening",
            "quality/readiness evidence",
        ],
    },
}

PROHIBITED_ASSERTIONS = (
    "BAE_VALIDATED",
    "BAE_CERTIFIED",
    "BAE_APPROVED",
    "BAE_ADOPTED",
    "PARTNER_VALIDATED",
    "PARTNER_APPROVED",
    "PARTNER_ADOPTED",
    "SUPPLIER_APPROVED",
    "CMMC_CERTIFIED",
    "NIST_800_171_CONFORMANT",
    "DFARS_SATISFIED",
    "CLASSIFIED_ACCESS_GRANTED",
    "DOE_VALIDATED",
    "FIELD_VALIDATED",
)

_NON_CLAIM_MARKERS = (
    "does not",
    "do not",
    "not",
    "no",
    "without",
    "unless",
    "never",
)


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(_json_text(value), encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def _file_digest(path: Path) -> str:
    return canonical_digest({"path": path.name, "content": path.read_text(encoding="utf-8")})


def _normalized_words(text: str) -> str:
    return " " + " ".join(text.lower().replace("-", " ").replace("/", " ").split()) + " "


def _has_explicit_non_claim_language(text: str) -> bool:
    words = _normalized_words(text)
    return any(f" {marker} " in words for marker in _NON_CLAIM_MARKERS)


def _assert_sanitized_text(text: str) -> None:
    upper = text.upper()
    for assertion in PROHIBITED_ASSERTIONS:
        if assertion in upper:
            raise ValueError(f"partner screening package contains prohibited assertion: {assertion}")


def _first_evidence(bundle: dict[str, Any]) -> dict[str, Any]:
    evidence = bundle.get("evidence", [])
    if not evidence or not isinstance(evidence[0], dict):
        raise ValueError("qualification bundle must include at least one evidence record")
    return evidence[0]


def _require_claim_boundary(bundle: dict[str, Any]) -> list[str]:
    boundary = bundle.get("claims_boundary")
    if not isinstance(boundary, list) or not boundary:
        raise ValueError("qualification bundle missing claims_boundary")
    text = "\n".join(str(item) for item in boundary)
    if not _has_explicit_non_claim_language(text):
        raise ValueError("claims_boundary must include explicit non-claim language")
    return [str(item) for item in boundary]


def _partner_preset(partner: str) -> tuple[str, dict[str, Any]]:
    key = partner.strip().upper().replace(" ", "_").replace("-", "_")
    if key in {"BAE", "BAE_SYSTEMS", "BAE_SYSTEMS_INC"}:
        key = "BAE_SYSTEMS"
    if key not in PARTNER_PRESETS:
        key = "GENERIC_PRIME"
    return key, PARTNER_PRESETS[key]


def _derive_partner_overlay(bundle: dict[str, Any], partner_id: str, preset: dict[str, Any]) -> dict[str, Any]:
    bae_overlay = bundle.get("bae_evidence_overlay")
    evidence = _first_evidence(bundle)
    if partner_id == "BAE_SYSTEMS" and isinstance(bae_overlay, dict):
        lane = bae_overlay.get("bae_lane", preset["business_lanes"])
        assets = bae_overlay.get("worldshepherd_asset", [])
        missing_validation = bae_overlay.get("missing_validation", [])
        proposed_demo = bae_overlay.get("proposed_demo", "Use this qualification bundle as a screened partner demonstration candidate.")
        likely_value = bae_overlay.get("likely_bae_value", "Partner-screening evidence package with retained claim boundaries.")
        pathways = bae_overlay.get("strongest_bae_pathway", preset["pathways"])
        supplier_gates = bae_overlay.get("supplier_readiness_dependency", preset["supplier_readiness_gates"])
        maturity = bae_overlay.get("maturity_label", "INTERNAL SOFTWARE EVIDENCE / REQUIRES EXTERNAL VALIDATION")
        boundary = bae_overlay.get("claim_boundary", [])
    else:
        lane = preset["business_lanes"]
        assets = bundle.get("requirement", {}).get("affected_lanes", [])
        missing_validation = bundle.get("requirement", {}).get("missing_capability", [])
        proposed_demo = "Use the generated qualification bundle as a non-confidential integration-screening artifact."
        likely_value = "Supports partner technical screening by preserving evidence scope, negative evidence, and claim boundaries."
        pathways = preset["pathways"]
        supplier_gates = preset["supplier_readiness_gates"]
        maturity = "INTERNAL SOFTWARE EVIDENCE / REQUIRES EXTERNAL VALIDATION"
        boundary = []
    return {
        "schema": "WS-PARTNER-EVIDENCE-OVERLAY-V1",
        "partner_id": partner_id,
        "partner_display_name": preset["display_name"],
        "requirement_delta_id": bundle.get("requirement", {}).get("requirement_delta_id"),
        "test_id": evidence.get("test_id"),
        "business_lanes": lane,
        "worldshepherd_assets_or_lanes": assets,
        "maturity_label": maturity,
        "missing_validation": missing_validation,
        "proposed_demonstration": proposed_demo,
        "likely_partner_value": likely_value,
        "screening_pathways": pathways,
        "supplier_readiness_gates": supplier_gates,
        "negative_evidence_retained": evidence.get("negative_evidence", []),
        "claim_boundary": boundary,
        "claim_boundary_note": (
            "The overlay is a screening map only. It does not establish partner interest, endorsement, "
            "adoption, validation, certification, supplier approval, classified access, or compliance conformity."
        ),
    }


def build_partner_screening_package(bundle: dict[str, Any], *, partner: str) -> dict[str, str | dict[str, Any]]:
    """Create a sanitized partner-screening package from a PRE qualification bundle.

    The package is intentionally not a proposal, certification, endorsement record,
    supplier approval, operational validation, or evidence of partner interest.
    """
    claims_boundary = _require_claim_boundary(bundle)
    evidence = _first_evidence(bundle)
    partner_id, preset = _partner_preset(partner)
    overlay = _derive_partner_overlay(bundle, partner_id, preset)
    requirement = bundle.get("requirement", {})

    summary = {
        "schema": "WS-PARTNER-QUALIFICATION-SUMMARY-V1",
        "partner_id": partner_id,
        "partner_display_name": preset["display_name"],
        "requirement_delta_id": requirement.get("requirement_delta_id"),
        "test_id": evidence.get("test_id"),
        "evidence_scope": evidence.get("evidence_scope"),
        "capability_status": evidence.get("capability_status"),
        "result": evidence.get("result"),
        "software_commit": evidence.get("software_commit"),
        "executed_utc": evidence.get("executed_utc"),
        "physical_validation_performed": evidence.get("physical_validation_performed", False),
        "negative_evidence_retained": evidence.get("negative_evidence", []),
        "screening_pathways": overlay["screening_pathways"],
        "claim_boundary": claims_boundary,
    }

    claims_md = f"""
# Claims Boundary

This partner-screening package is a non-confidential readiness artifact for {preset['display_name']} or a comparable integration-screening path.

Current maturity remains: **{summary.get('capability_status')} / {summary.get('evidence_scope')}**.

This package does not establish partner interest, endorsement, adoption, validation, certification, supplier approval, classified access, CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, CUI/CDI handling authorization, DOE validation, field performance, hardware performance, or operational authority.

Source bundle claim boundaries:

""" + "\n".join(f"- {item}" for item in claims_boundary)

    icd_md = f"""
# Interface Control Description

## Purpose

Describe how a generated Worldshepherd qualification bundle can be reviewed as a partner-screening artifact without exposing protected IP or overstating maturity.

## Inputs

- Qualification bundle JSON
- Requirement Delta Record
- Qualification evidence record
- Evidence graph where available
- Domain-specific overlay where available

## Outputs

- Qualification summary
- Partner evidence overlay
- Claims boundary
- Threat model
- Compliance gap map
- Data-rights/IP markings
- External validation route
- Replay instructions

## Timing assumptions

- Default mode: batch/replay
- Real-time authority: not claimed
- Partner-specific latency: scenario-defined

## Security assumptions

- CUI/CDI handling is not claimed unless a later record documents authorization and boundary controls.
- Classified data is not used.
- Partner validation is not inferred from export.
"""

    threat_md = f"""
# Threat Model

## Primary misuse risks

- Treating simulation as field validation
- Treating partner relevance as partner endorsement
- Treating internal software evidence as CMMC/NIST/DFARS compliance
- Leaking protected IP through excessive technical detail
- Reusing a screening package after the source bundle changes
- Omitting negative evidence or failed/null cases

## Required controls

- Preserve `evidence_scope`
- Preserve `capability_status`
- Preserve negative evidence
- Preserve source `bundle_digest`
- Preserve claims boundary
- Require CRE1AWS approval before external disclosure
- Require counsel/export-control review before sensitive sharing
"""

    compliance_md = f"""
# Compliance Gap Map

This map identifies review gates. It does not claim satisfaction.

| Gate | Current state |
|---|---|
| Partner validation | Not established |
| Supplier approval | Not established |
| CMMC 2.0 | Not claimed |
| NIST SP 800-171 | Not claimed |
| DFARS 252.204-7012 | Gap-map only |
| CUI/CDI boundary | Must be separately documented before handling |
| SBOM/dependency provenance | Required for partner package |
| Secure build/release | Required for partner package |
| Incident response | Required before controlled-data handling |
| Secrets management | Required before controlled integrations |
| Data rights/IP markings | Required before external sharing |
| Export-control screening | Required before sensitive sharing |
| Quality program | Required if supplier onboarding proceeds |
"""

    rights_md = f"""
# Data Rights and IP Markings

Default marking: **non-confidential screening artifact**.

Do not include protected/enabling IP, trade secrets, export-controlled details, customer data, CUI, CDI, classified material, or third-party restricted data unless a later approved package explicitly authorizes it.

Every technical assertion should retain:

- source bundle digest;
- requirement ID;
- evidence record ID/test ID;
- capability status;
- evidence scope;
- validation gap;
- disclosure approval state.
"""

    validation_md = f"""
# External Validation Route

External validation requires evidence not present in this screening export.

Minimum next steps:

1. Independent replay from the manifest and source bundle.
2. Signed evidence bundle or attestation.
3. Scenario-specific success/failure criteria.
4. Measurement uncertainty record.
5. Partner/lab reviewer identity and scope.
6. Explicit statement of what was and was not reproduced.

Until those records exist, status remains **internal / simulated / not externally reproduced**.
"""

    replay_md = f"""
# Replay Instructions

1. Generate or obtain the source PRE qualification bundle.
2. Verify the source bundle digest.
3. Export this screening package with `ws-partner-screening`.
4. Confirm all files in `manifest.json` are present.
5. Verify each artifact digest.
6. Confirm claims-boundary and negative-evidence sections are intact.
7. Do not present the package externally without CRE1AWS approval and required legal/export-control review.

Example:

```bash
ws-pre-bloom --out build/pre-bloom
ws-partner-screening --partner BAE_SYSTEMS --bundle build/pre-bloom/geo_prov_qualification_bundle.json --out build/partner-screening/bae-geo
```
"""

    package: dict[str, str | dict[str, Any]] = {
        "qualification-summary.json": summary,
        "partner-evidence-overlay.json": overlay,
        "claims-boundary.md": claims_md,
        "interface-control-description.md": icd_md,
        "threat-model.md": threat_md,
        "compliance-gap-map.md": compliance_md,
        "data-rights-ip-markings.md": rights_md,
        "external-validation-route.md": validation_md,
        "replay-instructions.md": replay_md,
    }

    combined_text = "\n".join(_json_text(v) if isinstance(v, dict) else v for v in package.values())
    _assert_sanitized_text(combined_text)
    return package


def export_partner_screening_package(bundle: dict[str, Any], out_dir: Path, *, partner: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    package = build_partner_screening_package(bundle, partner=partner)
    for filename, value in package.items():
        path = out_dir / filename
        if isinstance(value, dict):
            _write_json(path, value)
        else:
            _write_text(path, value)

    artifact_digests = {filename: _file_digest(out_dir / filename) for filename in sorted(package)}
    partner_id, preset = _partner_preset(partner)
    manifest = {
        "schema": "WS-PARTNER-SCREENING-MANIFEST-V1",
        "package_id": f"WS-PARTNER-SCREENING-{partner_id}-001",
        "partner_id": partner_id,
        "partner_display_name": preset["display_name"],
        "source_bundle_digest": bundle.get("bundle_digest"),
        "output_files": sorted(package),
        "artifact_digests": artifact_digests,
        "claims_boundary": (
            "Screening export only; no partner interest, validation, supplier approval, certification, "
            "classified access, or compliance conformity is claimed."
        ),
    }
    _write_json(out_dir / "manifest.json", manifest)
    manifest["artifact_digests"]["manifest.json"] = _file_digest(out_dir / "manifest.json")
    _write_json(out_dir / "manifest.json", manifest)
    return manifest


def _load_bundle(path: Path | None) -> dict[str, Any]:
    if path is None:
        return build_geo_prov_bundle(
            software_commit="local-partner-screening-fixture",
            executed_utc="2026-09-01T16:05:00Z",
            operator="ws-partner-screening",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export sanitized partner-screening package from a PRE qualification bundle.")
    parser.add_argument("--bundle", type=Path, default=None, help="Path to source qualification bundle JSON. Defaults to GEO fixture bundle.")
    parser.add_argument("--partner", default="BAE_SYSTEMS", help="Partner preset, e.g. BAE_SYSTEMS or GENERIC_PRIME.")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for screening package files.")
    args = parser.parse_args(argv)
    bundle = _load_bundle(args.bundle)
    manifest = export_partner_screening_package(bundle, args.out, partner=args.partner)
    print(_json_text(manifest), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
