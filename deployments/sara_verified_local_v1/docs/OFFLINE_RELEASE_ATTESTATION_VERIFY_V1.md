# Worldshepherd Offline Release Attestation Verification v1

## Purpose

Provide an evaluator-controlled, fail-closed path for verifying a Worldshepherd release-evidence artifact when the verification host is disconnected from the network.

This path reuses GitHub Artifact Attestations / Sigstore-backed verification rather than inventing a Worldshepherd-specific signing root.

## Required inputs

The verifier requires three explicit files:

1. the exact release artifact to verify, such as `release-index.json`;
2. the corresponding attestation bundle produced by the release-attestation workflow;
3. a trusted-root file exported while online for later offline verification.

It also requires GitHub CLI (`gh`) on the offline host.

## Trusted-root preparation

On a connected preparation host, obtain trusted roots using the supported GitHub CLI path:

```bash
gh attestation trusted-root > trusted_root.jsonl
```

Refresh this material whenever new signed artifacts are imported into the disconnected environment. Retain the trusted-root file as evaluator-controlled evidence.

## Verification

From the installed `worldshepherd-sara` package:

```bash
ws-release-attestation-offline-verify \
  --artifact release-index.json \
  --bundle sigstore-attestation-bundle.json \
  --trusted-root trusted_root.jsonl \
  --repository Bdavis1390/Sara_pro \
  --output offline-verification-receipt.json
```

The implementation delegates cryptographic verification to:

```text
gh attestation verify <artifact> -R <owner/repo> --bundle <bundle> --custom-trusted-root <trusted-root>
```

Worldshepherd wraps the result only to create a bounded custody receipt with hashes of all three explicit inputs.

## Fail-closed behavior

Verification fails before a PASS receipt can be generated when:

- any required file is missing;
- any required file is empty;
- the repository identifier is malformed;
- GitHub CLI is unavailable;
- `gh attestation verify` returns a non-zero status;
- the verification timestamp is not timezone-aware.

A failed verification is not converted to a warning or partial pass.

## Receipt

A PASS receipt binds:

- repository identity;
- artifact filename + SHA-256;
- attestation-bundle filename + SHA-256;
- trusted-root filename + SHA-256;
- UTC verification timestamp;
- verifier mechanism.

The complete receipt can itself be hashed by the CLI output for discrepancy/custody tracking.

## Claims boundary

A PASS establishes only that the supplied artifact verified against the supplied attestation bundle and trusted-root material using GitHub's supported offline attestation-verification path.

It does **not** establish:

- independent correctness of claims contained inside the artifact;
- independent reproduction of SARA behavior;
- government/customer acceptance;
- certification, accreditation, CMMC/NIST conformity, ATO, or classified/CUI authorization;
- operational effectiveness;
- scientific, physical, clinical, or regulatory validation.

For Worldshepherd Assurance Composite Benchmark scoring, this can support the offline/disconnected-verification dimension only after the exact implementation passes CI and a real disconnected verification is retained as evidence. Documentation and unit tests alone do not earn maximum evidence points.
