# WS Partner Screening Exporter — 2026-09-01

## Purpose

`ws-partner-screening` generalizes the BAE GEO screening export path into a reusable partner-readiness package exporter for PRE qualification bundles.

The exporter is meant to convert internal Worldshepherd evidence into a non-confidential screening artifact while preserving negative evidence, maturity limits, validation gaps, and claims boundaries.

## Scope

Initial presets:

- `BAE_SYSTEMS`
- `GENERIC_PRIME`

The BAE preset keeps the already established readiness themes: Mission Advantage, FAST Labs Technology Scouting, RIVETS, Virtual Proving Ground / plugfest, ADAPT/ADAMS, C5ISR, autonomy, AI/edge AI, EW/spectrum, cyber, APNT/DDIL, digital engineering, CBM+/digital twins, advanced manufacturing, distributed sensing, mission engineering, and secure software supply chain.

## Required outputs

- `manifest.json`
- `qualification-summary.json`
- `partner-evidence-overlay.json`
- `claims-boundary.md`
- `interface-control-description.md`
- `threat-model.md`
- `compliance-gap-map.md`
- `data-rights-ip-markings.md`
- `external-validation-route.md`
- `replay-instructions.md`

## Example

```bash
ws-pre-bloom --out build/pre-bloom
ws-partner-screening \
  --partner BAE_SYSTEMS \
  --bundle build/pre-bloom/geo_prov_qualification_bundle.json \
  --out build/partner-screening/bae-geo
```

If `--bundle` is omitted, the CLI generates the existing GEO fixture bundle for local demonstration only.

## Claims boundary

This exporter does **not** claim partner interest, endorsement, adoption, validation, certification, supplier approval, classified access, CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, CUI/CDI handling authorization, DOE validation, field performance, hardware performance, export-control clearance, or operational authority.

The exporter rejects packages that lack a source claims boundary and scans generated package text for prohibited assertion labels.

## Relationship to the specialized BAE GEO CLI

The existing `ws-bae-geo-screening` CLI remains available as a specialized GEO/BAE path. `ws-partner-screening` is the broader framework intended to support future APNT, DDIL, RF, CBM+, manufacturing lineage, and other PRE qualification bundles.

## Maturity

`INTERNAL SOFTWARE EVIDENCE / SCREENING PACKAGE EXPORT / REQUIRES EXTERNAL VALIDATION`
