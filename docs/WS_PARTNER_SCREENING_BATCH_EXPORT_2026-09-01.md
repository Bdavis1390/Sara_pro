# WS Partner Screening Batch Export — 2026-09-01

## Purpose

Add a batch export path for partner-screening packages so a PRE full-bloom output directory can be converted into structured partner/lane screening folders with one command.

## Command

```bash
ws-pre-bloom --fixtures deployments/sara_verified_local_v1/fixtures --out build/pre-bloom
ws-partner-screening-batch --bundle-dir build/pre-bloom --out build/partner-screening
```

By default, the batch command exports each `*_qualification_bundle.json` for both:

- `BAE_SYSTEMS`
- `GENERIC_PRIME`

A caller may override the partner set by repeating `--partner`, for example:

```bash
ws-partner-screening-batch \
  --bundle-dir build/pre-bloom \
  --partner BAE_SYSTEMS \
  --out build/partner-screening/bae-only
```

## Output layout

```text
build/partner-screening/
├── batch-manifest.json
├── bae_systems/
│   ├── apnt/
│   ├── cbm/
│   ├── ddil/
│   ├── ddil_rejoin/
│   ├── edge/
│   ├── fusion/
│   ├── geo_prov/
│   ├── manufacturing/
│   ├── mission/
│   └── rf/
└── generic_prime/
    └── ...same lane layout...
```

Each lane/partner folder is generated through the existing single-bundle exporter and therefore retains the same controls:

- required claims boundary;
- prohibited-assertion rejection;
- evidence scope preservation;
- capability-status preservation;
- negative-evidence preservation;
- package-level artifact digests;
- partner-overlay claim boundary.

## Batch manifest

`batch-manifest.json` records:

- source bundle directory;
- output directory;
- partner IDs;
- exported lanes;
- source bundle count;
- package count;
- per-export source bundle digest;
- per-export package manifest digest;
- batch digest.

## Claims boundary

This batch export is a packaging/readiness mechanism only. It does not establish partner interest, partner validation, BAE validation, supplier approval, certification, classified access, CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, external reproduction, field performance, hardware performance, DOE validation, or operational authority.
