# WS Partner-Screening Manifest Verifier — 2026-09-01

## Purpose

Add a read-only verifier for partner-screening package artifacts generated from PRE full-bloom evidence.

The verifier is intended to support the BAE Systems and generic-prime screening workflow by ensuring that a generated package has not been altered before review or archival.

## New CLI

```bash
ws-partner-screening-verify --package <partner-package-dir>
ws-partner-screening-verify --batch <partner-screening-batch-dir>
```

## Verification scope

For a single partner-screening package, the verifier checks:

- `manifest.json` exists;
- manifest schema is `WS-PARTNER-SCREENING-MANIFEST-V1`;
- every declared output file exists;
- every declared output file digest matches;
- the manifest bootstrap self-digest matches;
- required package files are present;
- prohibited false-readiness assertions are absent.

For a batch export, the verifier checks:

- `batch-manifest.json` exists;
- batch schema is `WS-PARTNER-SCREENING-BATCH-MANIFEST-V1`;
- `source_bundle_count`, `package_count`, lanes and partners are internally consistent;
- `batch_digest` matches the manifest bootstrap form;
- every export record resolves to a package directory;
- every package manifest and file digest verifies;
- every package manifest digest matches the batch export record.

## CI integration

The SARA Verified Local v1 Gate now checks:

```bash
command -v ws-partner-screening-verify
ws-partner-screening-verify --help >/dev/null
ws-partner-screening-verify --batch partner_screening_ci >/dev/null
```

This means the uploaded `partner-screening-batch-evidence` artifact is generated and verified before upload.

## Claims boundary

This verifier confirms package integrity only.

It does not establish partner interest, partner validation, BAE validation, supplier approval, CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, classified access, DOE validation, field performance, hardware performance, external reproduction, export-control clearance, or operational authority.

Current maturity remains:

`INTERNAL SOFTWARE EVIDENCE / CI-GENERATED AND DIGEST-VERIFIED SCREENING PACKAGE / REQUIRES EXTERNAL VALIDATION`

## BAE readiness effect

This is a partner-readiness improvement because it gives Worldshepherd a reproducible way to prove that a BAE-style screening package still matches its generated manifests and file digests before external review.

It is not a BAE endorsement or acceptance signal.
