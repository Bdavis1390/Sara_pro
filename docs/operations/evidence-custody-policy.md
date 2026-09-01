# SARA Commit Closure Evidence Custody Policy

Status: INTERNAL ENGINEERING CUSTODY PRECURSOR

## Objective

Bind the critical internal engineering evidence for one exact SARA commit into a single machine-verifiable manifest and cryptographically attest that manifest after successful main-branch execution.

## Required evidence classes

A closure manifest must fail closed unless it finds a successful workflow run and an unexpired SHA-256-addressed artifact for the same target commit from each of these classes:

- SARA release evidence index
- rollback drill evidence
- replacement-environment restore evidence
- TLS/private-backend architecture evidence
- operational-resilience incident/recovery evidence

The manifest records workflow identity, run ID/attempt, event, branch, exact head SHA, conclusion, workflow URL, artifact name/ID, provider-reported digest, size, creation time, expiration time, and expiration state.

## Signing

For a successful `main` push, the closure manifest is attested through GitHub Actions OIDC using Sigstore-backed artifact attestation. The custody receipt records the target commit, manifest digest, attestation bundle digest, attestation identifier, attestation URL, and signing mechanism.

## Pull-request qualification

Pull requests build the same exact-commit evidence inventory without making a production or external-custody claim. The PR gate therefore exercises workflow/artifact discovery and commit binding before merge.

## Claims boundary

This policy establishes a stronger same-provider cryptographic custody chain than separate unsigned CI artifacts. It is not off-provider or independent archival custody. It does not establish legal-record retention, WORM storage, customer/government acceptance, an external audit, certification, ATO, or independent third-party reproduction. A later external-custody implementation must export and verify the signed closure package in a separately administered failure and trust domain before the external ledger gate can be closed.
