# WS Intake Minimum Standard Adoption — 2026-09-01

## Adoption posture

The intake minimum standard is now the baseline intake-control surface for new Worldshepherd/SARA signals. The immediate implementation is intentionally bounded:

- It provides a CLI and library validator.
- It provides a checked fixture representing the current CRE1AWS directive.
- It adds regression tests that fail if required custody, routing, review, or claims-boundary fields are missing.
- It does not change release-index inputs yet, so the existing post-merge evidence workflow remains stable.

## Required next integration

After this standard lands, the next increment should wire `ws-intake-minimum-ledger` into the SARA Verified Local v1 workflow as an uploaded artifact and then add release-index custody for that artifact.

Recommended sequence:

1. Build `intake_minimum_ci` from `fixtures/intake_minimum_standard.json`.
2. Assert both `intake-minimum-ledger.json` and `intake-minimum-summary.json` exist.
3. Upload the artifact as `intake-minimum-standard-evidence`.
4. Add optional or required intake-minimum fields to `ws-release-index`.
5. Extend release-index tests to verify intake custody without weakening the existing SBOM, vulnerability, human-triage, PRE, partner-screening, recovery, and operational snapshot checks.

## Claims boundary

This adoption record does not establish implementation completion across every future intake. It establishes the first enforced validator and fixture for minimum intake governance. Workflow-level artifact custody and release-index linkage remain the next integration step.
