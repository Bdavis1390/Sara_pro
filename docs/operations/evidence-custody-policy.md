# SARA Commit Closure Evidence Custody Policy

Status: INTERNAL ENGINEERING CUSTODY PRECURSOR

## Objective

Bind the critical internal engineering evidence for one exact SARA commit into a single machine-verifiable manifest and cryptographically attest that manifest after successful main-branch execution.

## Required evidence classes

A closure manifest must fail closed unless its trusted main-branch collector supplies a successful workflow run and an unexpired SHA-256-addressed artifact for the same target commit from each of these classes:

- SARA release evidence index
- rollback drill evidence
- replacement-environment restore evidence
- TLS/private-backend architecture evidence
- operational-resilience incident/recovery evidence

The manifest records workflow identity, run ID/attempt, event, branch, exact head SHA, conclusion, workflow URL, artifact name/ID, provider-reported digest, size, creation time, expiration time, and expiration state.

## Trust separation

The manifest builder is deliberately offline: it receives a local snapshot and never receives a GitHub token or performs network requests. GitHub workflow/artifact discovery occurs only in the trusted main-branch `workflow_run` path after the SARA main gate succeeds. That collector uses the bounded GitHub CLI API client and passes only resulting metadata into the offline validator.

## Signing

For a successful `main` push, the closure manifest is attested through GitHub Actions OIDC using Sigstore-backed artifact attestation. The custody receipt records the target commit, manifest digest, attestation bundle digest, attestation identifier, attestation URL, and signing mechanism.

## Pull-request qualification

Pull requests receive no Actions-read credential for closure discovery. Instead, the PR job uses a synthetic five-class snapshot to compile and exercise the offline schema, validation, exact-SHA binding, digest validation, manifest generation, and fail-closed contract. Live workflow/artifact discovery and signing are reserved for trusted `main` execution.

## Claims boundary

This policy establishes a stronger same-provider cryptographic custody chain than separate unsigned CI artifacts. It is not off-provider or independent archival custody. It does not establish legal-record retention, WORM storage, customer/government acceptance, an external audit, certification, ATO, or independent third-party reproduction. A later external-custody implementation must export and verify the signed closure package in a separately administered failure and trust domain before the external ledger gate can be closed.
