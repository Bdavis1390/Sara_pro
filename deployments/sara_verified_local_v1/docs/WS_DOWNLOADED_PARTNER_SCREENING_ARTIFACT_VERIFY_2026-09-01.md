# WS Downloaded Partner-Screening Artifact Verification

Date: 2026-09-01  
Status: CI-integrated verifier support  
Scope: Worldshepherd/SARA partner-screening evidence custody

## Purpose

This record adds a local verification path for downloaded GitHub Actions artifacts, especially:

```text
partner-screening-batch-evidence
```

The goal is to let a reviewer or operator download a GitHub Actions artifact ZIP, compare the downloaded ZIP against the GitHub-displayed artifact digest, extract it safely into a temporary directory, and run the existing partner-screening manifest verifier against the extracted package tree.

## Added script

```bash
scripts/verify_partner_screening_artifact.sh <artifact.zip|extracted-dir> [expected-artifact-sha256]
```

Accepted inputs:

- GitHub Actions artifact ZIP;
- extracted batch directory containing `batch-manifest.json`;
- extracted single package directory containing `manifest.json`.

The optional digest argument accepts either:

```text
<hex>
sha256:<hex>
```

## Verification sequence

For a downloaded ZIP:

```text
ZIP exists
→ optional ZIP SHA-256 matches supplied expected digest
→ ZIP is extracted into a temporary directory
→ artifact root is resolved
→ batch-manifest.json or manifest.json is identified
→ ws-partner-screening-verify validates manifests and file digests
→ JSON PASS/FAIL report is emitted
```

For an extracted directory:

```text
directory exists
→ artifact root is resolved
→ batch-manifest.json or manifest.json is identified
→ ws-partner-screening-verify validates manifests and file digests
→ JSON PASS/FAIL report is emitted
```

## Example use

```bash
cd deployments/sara_verified_local_v1
bash scripts/verify_partner_screening_artifact.sh \
  ~/Downloads/partner-screening-batch-evidence.zip \
  sha256:<digest-shown-by-github-actions>
```

Or, after manual extraction:

```bash
cd deployments/sara_verified_local_v1
bash scripts/verify_partner_screening_artifact.sh /path/to/extracted/partner_screening_ci
```

## CI integration

The SARA Verified Local v1 Gate now checks:

```bash
bash scripts/verify_partner_screening_artifact.sh --help
```

and, after generating the CI partner-screening batch package:

```bash
bash scripts/verify_partner_screening_artifact.sh partner_screening_ci
```

That proves the reviewer-facing script path works on the same generated evidence tree uploaded by CI.

## Test coverage

The test suite verifies:

- extracted batch verification succeeds;
- artifact ZIP verification succeeds when the expected digest matches;
- artifact ZIP verification fails when the expected digest is wrong.

## Claims boundary

This verification path checks integrity and manifest consistency only.

It does **not** establish:

- BAE interest;
- partner validation;
- supplier approval;
- CMMC conformity;
- NIST SP 800-171 implementation;
- DFARS satisfaction;
- classified access;
- DOE validation;
- field performance;
- hardware performance;
- external reproduction;
- export-control clearance;
- operational authority.

Current maturity remains:

```text
INTERNAL SOFTWARE EVIDENCE / CI-GENERATED AND LOCALLY VERIFIABLE SCREENING PACKAGE / REQUIRES EXTERNAL VALIDATION
```

## BAE readiness effect

This closes the downloaded-artifact custody gap for the BAE screening package path. The chain now supports:

```text
PRE full-bloom generation
→ partner-screening batch export
→ CI manifest verification
→ Actions artifact upload
→ downloaded ZIP digest comparison
→ local manifest/file-digest verification
```

That improves review discipline without changing Worldshepherd's technical validation status.
