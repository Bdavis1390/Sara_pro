# WS-BAE-GEO Screening CLI — 2026-09-01

## Purpose

`ws-bae-geo-screening` exports a non-confidential BAE screening package from the `WS-GEO-PROV-001A` geospatial provenance qualification bundle.

The package is meant to help translate the generated PRE evidence into a partner-screening discussion artifact. It is not a proposal, certification, validation, supplier approval, operational authority, or evidence of BAE interest.

## Inputs

The CLI can either:

1. read a generated `geo_prov_qualification_bundle.json`; or
2. build the internal synthetic GEO bundle directly from `worldshepherd_sara.geo_provenance.build_geo_prov_bundle()`.

## Command

```bash
ws-bae-geo-screening \
  --bundle path/to/geo_prov_qualification_bundle.json \
  --out out/ws-bae-geo-screening \
  --executed-utc 2026-09-01T16:00:00Z \
  --operator SSPADAWANZZ
```

If `--bundle` is omitted, the CLI generates the internal synthetic bundle first.

## Output files

- `manifest.json`
- `qualification-summary.json`
- `bae-evidence-overlay.json`
- `claims-boundary.md`
- `interface-control-description.md`
- `threat-model.md`
- `nist-cmmc-dfars-gap-map.md`
- `data-rights-ip-markings.md`
- `external-validation-route.md`
- `replay-instructions.md`

## Controls

The exporter requires the source bundle claims boundary to retain the no-BAE-interest and no-supplier-cybersecurity-conformity statements before package generation.

The exporter also writes a manifest with file digests so the package can be reviewed and compared after transfer.

## Current maturity

`INTERNAL SOFTWARE EVIDENCE / SIMULATED REPLAY / REQUIRES EXTERNAL VALIDATION`

## Claims boundary

This package does not claim:

- BAE Systems interest, endorsement, adoption, validation, certification, approval, classified access, supplier approval, or partnership;
- DOE validation, national-lab validation, independent reproduction, or external acceptance;
- land-restoration performance, emergency-response authority, field-calibrated sensor performance, or hardware/platform performance;
- CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, CUI/CDI handling authorization, or export-control clearance.

## BAE readiness value

The value proposition remains narrow and evidence-governed:

> Worldshepherd can package a simulated, replayable mission-context provenance workflow for heterogeneous environmental/geospatial evidence, degraded data, source disagreement, null controls, and human-reviewed decisions.

This can support BAE-oriented screening against RIVETS, ADAPT/ADAMS, Virtual Proving Ground-style interoperability, and Mission Advantage framing, but it does not imply BAE acceptance.
