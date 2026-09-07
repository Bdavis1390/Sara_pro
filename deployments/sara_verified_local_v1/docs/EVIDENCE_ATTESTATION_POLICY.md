# SARA Release Evidence Attestation Policy

## Purpose

This policy defines the internal signing and retention boundary for SARA release-evidence indexes. It is an engineering-control document, not an external compliance certification.

## Authoritative internal subject

The attested subject is `release-index.json` emitted by a successful `SARA Verified Local v1 Gate` push run on `main`. The release index binds the triggering repository commit to the artifact IDs and SHA-256 digests produced by that gate.

A pull-request candidate, failed workflow, non-main branch run, or manually generated local file is not eligible for this automated release-index attestation.

## Privilege separation

The build/test job does not receive OIDC or attestation-write authority merely to produce evidence. A separate `workflow_run` job starts only after the main SARA gate reports success. That job receives the minimum signing-related permissions required by GitHub artifact attestations, downloads the release-index artifact from the exact triggering run, and verifies its recorded commit, workflow run, event, ref, and merge state before signing.

## Signing mechanism

The attestation workflow uses GitHub artifact attestations through `actions/attest`, which uses a short-lived GitHub Actions OIDC identity and Sigstore-backed signing. The resulting attestation is persisted by GitHub's attestation service and a serialized Sigstore bundle is also retained as workflow evidence.

## Retention

The workflow retains an `attestation-receipt.json` and `sigstore-attestation-bundle.json` as a GitHub Actions artifact for 90 days. The GitHub attestation itself is stored separately by GitHub's attestation service. This is off-runner custody, but it is not described as independent third-party archival custody.

For any contract requiring independent/off-platform archival retention, externally controlled signing keys, WORM storage, legal-hold retention, classified/CUI storage, or customer-specific retention periods, this internal mechanism is insufficient until the corresponding authoritative architecture and evidence exist.

## Verification requirements

Before relying on an attested release index internally, verify all of the following:

- the attested file digest matches the intended `release-index.json`;
- the release index names the intended Git commit;
- the index records `MAIN_BRANCH_PUSH`, event `push`, and ref `refs/heads/main`;
- the triggering SARA gate completed successfully;
- the attestation identity and repository correspond to `Bdavis1390/Sara_pro`;
- referenced evidence artifacts remain within their own claims boundaries.

## Claims boundary

A valid cryptographic attestation proves provenance and integrity of the attested release-index file under the GitHub/Sigstore workflow identity. It does **not** prove that every scientific, technical, legal, security, partner, physical, or compliance claim referenced by the index is externally true or validated. It does not constitute ATO, CMMC certification, RMF authorization, legal review, government acceptance, partner validation, laboratory validation, field validation, or independent reproduction.
