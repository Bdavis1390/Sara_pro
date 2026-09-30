# Worldshepherd V22 — GitHub Controlled-Build Evidence

Date: 2026-09-30

## Result

**CONTROLLED BUILD CANDIDATE — PASS**

GitHub Actions workflow `Worldshepherd V22 Controlled Build`, run `36721728664`, completed successfully for PR #510 after the resolver gate exposed and the branch corrected two missing transitive runtime constraints (`cffi==2.1.1` and `pycparser==3.0`).

This evidence remains candidate evidence and earns no production-readiness credit by itself.

## Source binding

- Repository: `Bdavis1390/Sara_pro`
- PR: `#510`
- Branch head SHA: `1354a4d4dc75463f3712015031e1896091b8a32a`
- Tested PR merge SHA recorded by the evidence manifest: `681f415222399661f11b43d7cf3f0e2d78f5f788`
- Builder: GitHub-hosted Actions runner, Python `3.12.14`, pip `26.2.1`

## Evidence artifact

- GitHub Actions artifact ID: `11099991155`
- GitHub artifact ZIP SHA-256: `7e11cdc730289d3df7129f3c452fd742ad3323ffae2772ef46fd780afa8192dc`
- Frozen evidence tar SHA-256: `dfdbefe472c34687f96e5f82cd49c3b2cd7188ef5952b421c25db6e503e6dbc3`
- Internal evidence checksum ledger: **PASS**

## Runtime dependency evidence

- Resolved/hash-locked runtime components: **22**
- `--require-hashes` replay: **PASS**
- CycloneDX version: **1.7**
- SBOM component count: **22**
- Candidate hash-lock SHA-256: `eaade72392a05803bb716120c88569d26307690cf651ee21e3535872a9d929a6`
- Candidate SBOM SHA-256: `0d21dd1c74801761372a2cf60681e1368dc63c09886f3442ccc6882449fb67d4`

The controlled resolver demonstrated that `cryptography==50.0.1` resolves through `cffi==2.1.1` and `pycparser==3.0`; those packages were absent from the pre-V22 exact constraint set and are now explicitly pinned on the PR branch.

## Build evidence

- SARA wheel: `worldshepherd_sara-0.1.0-py3-none-any.whl`
- Wheel SHA-256: `b84d044c97260cd772ba01b54209727b2d4106bbfc45b336080c85c84786506d`
- Docker base reference verified by the runner: `python@sha256:7a8b475003c4fe15a2cd4e55e5cfc2f3560bdc9333d624f24cdd6d4340fd7a17`
- Pulled base image ID: `sha256:72a58063c7563c5c64052da2becebce3f25b60055cb351b668c4e2df9153702c`
- Built SARA image ID: `sha256:4209055d5ace6582590fba9956457a0e91bf72b7c632e588c5e946634346fbc0`
- Built image revision label: `681f415222399661f11b43d7cf3f0e2d78f5f788`

## Adjacent repository gate

The V22 controlled-build workflow is green. The repository-level `Required Test and Build` gate on PR #510 is presently blocked by the already-identified wall-clock expiry of the SDA ephemeral mTLS test certificate. That defect is isolated in PR #509 (`CI: keep SDA mTLS test certificates wall-clock valid`), where `Required Test and Build`, CodeQL, rollback, TLS architecture, NIST precursor, and other gates have passed. V22 deliberately does not duplicate that unrelated one-file test-fixture repair.

## Main-only provenance boundary

V22's main-push job is configured to rebuild the dependency evidence and SARA wheel from the exact reviewed main commit, retain the evidence archive, and use `actions/attest` to produce GitHub/Sigstore SLSA provenance for the **SARA wheel itself**. Pull-request jobs retain read-only token permissions and cannot mint that main provenance.

## Claims boundary

**IMPLEMENTED IN GITHUB CI + CONTROLLED-BUILD CANDIDATE.** This record does not independently establish production deployment, independent validation, non-exportable PRIME/ECHO signer custody, trusted time, off-host anti-rollback anchoring, measured-boot host attestation, or independent adversarial assessment. Those gates remain fail-closed.
