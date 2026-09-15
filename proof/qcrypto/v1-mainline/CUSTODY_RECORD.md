# Worldshepherd QCRYPTO v1 — Mainline Custody Record

**Purpose:** preserve a compact, reviewable record of the frozen QCRYPTO proof-of-work anchors separately from the large technical PR.

## Canonical evidence anchors

- Implementation commit: `b65302d2e849dcad67b553378d3fce11b404f3c5`
- Implementation tree: `81af4f67c9ad781c392dca277b9f433ea3827107`
- Publication commit: `c34ab9017c75ead5fde2f4e4c6ed8a883e1e9233`
- Publication tree: `9e897cb9642b9a761ed6098a1f8ad8356bee7af8`
- Historical public white-page blob: `b02398f0ff0b210ca089bb340e91f8002c61e2d5`
- Preservation head: `22ca8074daeb8e08f55a9094c68aebf31b72269d`
- Preservation tree: `ffc31d2d802051c3f96baa134e73e8b744fb4969`

## Evidence artifact hashes

- QCRYPTO ECHO bridge ZIP: `sha256:15dc39ef59a8bbe10e48f858f1bb42d34c9c35adb33045b9f7635201c5df698e`
- White-page publication-readiness ZIP: `sha256:6abd5f27414ff036547a1d8832fc14d4b53c22dcdd5258c9059e3270aabeb663`
- Proof-preservation receipt ZIP: `sha256:50ce0c06e297cfaf907d88c94aa4d150ca504e58185d2d69165f9f0bb4df0eaf`
- Portable proof bundle ZIP: `sha256:3ac4b9d6a94c50dad951ed5c33446ccaaffc876b9d9ad398aefe2a6b7e472522`

## Frozen refs

- `proof/qcrypto-v1-20260915` -> `22ca8074daeb8e08f55a9094c68aebf31b72269d`
- `proof/qcrypto-v1-20260915-mirror` -> `22ca8074daeb8e08f55a9094c68aebf31b72269d`

The mirror is redundant reachability only. Neither proof ref is currently protected, so these refs are not described as immutable.

## Verified preservation state

At preservation head `22ca8074...`:

- QCRYPTO Proof Preservation Gate: PASS
- QCRYPTO White Page Publication Gate: PASS / `posting_status: GO`
- Required Test and Build: PASS
- portable bundle top-level SHA-256 reverified locally
- every entry in the portable bundle `SHA256SUMS.txt` reverified locally
- all three original Actions artifact ZIP hashes reverified locally

## Due-diligence findings

1. The preservation and publication commits are reported by GitHub as **unsigned**.
2. The two frozen proof refs are **unprotected**.
3. The repository rulesets endpoint currently reports no repository rulesets.
4. Current protected `main` has advanced to `48ea5c8466946d7d1ac426f9658a7fed5b8a8a55` and is GitHub-verified.
5. The technical QCRYPTO head and current `main` are diverged; the technical branch is 176 commits ahead and 10 commits behind current `main`, with merge base `17e1720bbfe5415edd4cf20b7f42b803a6d4a328`.
6. PR #208 remains draft/open/unmerged and currently spans 176 commits / 102 changed files. This is a reviewability risk, not a defect in the frozen evidence.
7. The original GitHub Actions artifacts are retained only through December 2026; the repository payload copies and portable bundle mitigate that retention limit.
8. No external timestamp/notary, signed tag/release, independent third-party validation, or independent storage copy is claimed yet.

## Prepared external timestamp request

A local RFC 3161 TimeStampReq was generated for the exact portable bundle SHA-256.

- Bundle SHA-256: `3ac4b9d6a94c50dad951ed5c33446ccaaffc876b9d9ad398aefe2a6b7e472522`
- RFC 3161 request SHA-256: `7e39671254effc6f5e2c1d475b8aa37ef776487d14faf5c551705def45fca00e`

The request is preparation only. No external TSA response or signed timestamp token is claimed.

## Claims boundary

This custody record supports repository provenance and proof preservation only. It does not establish production deployment, migration execution, live-value authorization, post-quantum security of the Ed25519 checkpoint, Federal compliance, WS-CAE conformance, external certification, independent validation, signed authorship of the historical commits, or physical-system qualification.
