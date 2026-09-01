# WS CI Partner-Screening Artifact Upload — 2026-09-01

## Purpose

This record documents the SARA Verified Local v1 Gate update that turns the generated PRE full-bloom qualification evidence into a CI-uploaded partner-screening evidence artifact.

The workflow now performs the following sequence:

```text
ws-pre-bloom
→ qualification_evidence_ci/
→ ws-partner-screening-batch
→ partner_screening_ci/
→ upload-artifact: partner-screening-batch-evidence
```

## Added CI checks

The workflow verifies the installed console scripts:

```text
ws-pre-bloom
ws-partner-screening
ws-partner-screening-batch
```

It then validates the batch output before upload:

- `partner_screening_ci/batch-manifest.json` exists and is non-empty.
- Manifest schema is `WS-PARTNER-SCREENING-BATCH-MANIFEST-V1`.
- Default partners are `BAE_SYSTEMS` and `GENERIC_PRIME`.
- Source bundle count is greater than zero.
- Package count equals source bundle count multiplied by partner count.
- Batch digest is present and SHA-256 shaped.
- Every export record has a package directory with `manifest.json`, `qualification-summary.json`, and `claims-boundary.md`.
- Prohibited false-readiness assertions remain absent from the generated package tree.

## Artifact

The new uploaded artifact is:

```text
partner-screening-batch-evidence
```

It contains the generated partner/lane screening package tree created from the same PRE full-bloom bundle set used in the gate.

## Claims boundary

This artifact is a CI-generated screening evidence package only. It does **not** establish partner interest, partner validation, BAE validation, supplier approval, CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, classified access, DOE validation, field performance, hardware performance, external reproduction, export-control clearance, or operational authority.

Current maturity remains:

```text
INTERNAL SOFTWARE EVIDENCE / CI-GENERATED SCREENING PACKAGE / REQUIRES EXTERNAL VALIDATION
```
