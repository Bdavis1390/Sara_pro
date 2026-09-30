# SPDX/QCRYPTO post-restoration reconciliation — 2026-09-30

## Current lane

`qcrypto/spdx-pqc-parameters` is the current narrow working branch for the SPDX Cryptographic Algorithm List PQC-parameter discussion. Its scope is limited to the proposed taxonomy fields, NIST FIPS 203/204/205 fixtures, and local validation of those fixtures.

The proposal remains **DRAFT / NOT AN SPDX POSITION** until upstream discussion reaches consensus.

## Historical branches reviewed

The following recovered branches contain useful evidence, but they are not wholesale-merged into this lane:

- `worldshepherd-spdx-intake-v1` — bounded SPDX 3.0.1 JSON-LD intake and admission-review preparation. This is broader SBOM/document intake, not the cryptographic-algorithm-list parameter model.
- `worldshepherd-spdx-validator-triangulation-v1` — validator-diversity workflow and review notes. Preserve as historical validation evidence; re-run against current validator versions before promotion.
- `worldshepherd-spdx-jena-semantic-v1` — additional semantic-validation diversity. Orthogonal to the present PQC taxonomy proposal.
- `worldshepherd-spdx-semantic-negative-v1` — semantic negative controls. Useful methodology, but not a substitute for validating the FIPS parameter relationships in this branch.
- `worldshepherd-spdx-reproduction-v1` — reproduction packaging for the broader SPDX validation lane. Preserve rather than importing branch drift.

## Reconciliation decision

Do not merge stale branch history merely to recover files. Reuse the **methodological invariants** instead:

1. preserve the authoritative source and transformation history;
2. separate local shape/integrity checks from standards conformance claims;
3. include negative controls that prove the validator rejects evidence drift;
4. keep semantic, implementation-security, interoperability, certification, and admission claims separate;
5. rebase/promote only against current `main` after required CI passes.

This branch implements those invariants with `scripts/validate_spdx_pqc_fixtures.py` and its negative-control test suite.

## Claim boundary

Passing the local validator proves only that the checked fixture relationships and local claim ceilings satisfy the rules encoded by this branch. It does **not** prove SPDX acceptance, NIST implementation validation, CAVP status, side-channel resistance, cryptographic implementation security, interoperability, hardware readiness, or certification.

## Promotion gate

Before merging this lane:

- current `main` must be incorporated without conflict;
- repository-required status checks must pass on the updated head;
- `QCRYPTO SPDX PQC Fixture Gate` must pass;
- the PR must continue to state that the schema proposal is not an accepted SPDX position;
- upstream submission remains discussion-first and should use the existing SPDX Issue #88 unless maintainers direct otherwise.
