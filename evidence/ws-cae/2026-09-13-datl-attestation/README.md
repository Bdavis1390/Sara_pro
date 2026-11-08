# WS-CAE DATL attestation proof — 2026-09-13

Claims state: operational transparency attestation proven; SCITT transparency-service receipt not yet proven.

Exact PR head used for the observable attestation run:

`98c29e3dd0f0a34b3836a5c5dc058864b433f526`

GitHub Actions run: `34787026593`
Job: `103804238648`
Artifact ID: `10326991807`
Artifact ZIP digest:

`sha256:ff8d0a6e7f2d24757b0b79330a2067e6182eff4afc2349711ee07be095ca85d4`

## Exact evidence bindings

DATL statement SHA-256:

`7048c7726e1edf9809b1d562d18d00711bf07328c80dd5cd69719613257fbbef`

Source WS-CAE patch SHA-256:

`9237fbaadb0f4ad294985d9f89c496639eb97fa8fda3b1b9f59c24c585273c2b`

Subject:

`urn:ws-cae:blockchain:ethereum`

Predicate type:

`urn:ws-cae:predicate:datl:v0.1`

The Sigstore bundle is media type `application/vnd.dev.sigstore.bundle.v0.3+json` and contains one transparency-log entry at log index `2822787224`, with both an inclusion promise and inclusion proof.

The DSSE envelope is `application/vnd.in-toto+json`. Its in-toto subject SHA-256 exactly matches the DATL statement SHA-256 above.

The workflow successfully executed:

1. deterministic DATL statement generation;
2. custom in-toto predicate generation;
3. keyless Cosign attestation using GitHub Actions OIDC;
4. identity-bound `verify-blob-attestation` verification;
5. proof-bundle artifact preservation.

## Important boundary

This proves that a specific digital-asset authority/migration statement was content-bound, identity-bound, entered Sigstore transparency infrastructure, and independently re-verifiable from the resulting bundle.

It does **not** prove the substantive Ethereum claims are true merely because they were attested, does not establish a SCITT transparency-service receipt, does not imply Ethereum endorsement, and does not establish DATL as a standard or adopted industry infrastructure.
