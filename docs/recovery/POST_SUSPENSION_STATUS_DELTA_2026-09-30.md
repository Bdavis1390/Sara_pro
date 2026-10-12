# Post-suspension live status delta — 2026-09-30

This file is the authoritative live-status override for row states in the companion master ledger and portfolio registry when protected-main promotions occurred after those larger documents were authored.

Protected main at this update: `3c6f9c8ad19707a6ff1b2473f31b9a82f16b29ce`.

## Promotions completed during reconciliation

- **PR #506** — post-suspension reconciliation control plane: **MERGED**.
- **PR #509** — SDA mTLS wall-clock-valid test fixture: **MERGED**.
- **PR #510** — Yellow-Hat V22 controlled-build evidence gate: **MERGED** after exact-head protected gates passed.
- **PR #511** — TimeAuthority + ECHO Time Custody v0.2: **MERGED**.
- **PR #507** — SPDX-PQC draft proposal/evidence package: **MERGED** as an internally validated repository artifact. This is **not** a claim of upstream SPDX adoption or acceptance.
- **PR #514** — QCRYPTO Bitcoin migration exposure baseline v0.1: **MERGED** at merge commit `3c6f9c8ad19707a6ff1b2473f31b9a82f16b29ce` after the complete refreshed exact-head protected gate set passed. Claims remain software/R&D only; no live funds, broadcast, deployed Bitcoin PQ mechanism, BIP 361 adoption, or CRQC prediction is claimed.

## Still gated

- **PR #512 — QCRYPTO + TSV v3.6 recovery:** **DRAFT**. Exact package/replay testing is 301/301 and dedicated recovery/CodeQL/resilience/NIST/closure gates pass. Repository Required Test and Build fails only at `git diff --check` because exact recovered source contains contribution whitespace. The custody artifact stays immutable; any CI-clean normalization is a separately identified derived Git projection.
- **PR #513 — UC06-P1 / EM control:** **DRAFT**. Requires content-aware merge against current SARA surfaces plus D5 residual adjudication and medium/fine recovery evidence. No hardware actuation/convergence claim.
- **PR #516 — reconciliation ledger/registry:** **OPEN** until its own exact-head repository gates pass against current protected main.
- **Issue #518:** open exact-object/forward-port closure queue for BAROS, QPHONON, WS-QX, ATIP/LSRP, WS-SDA and registry closure. SSPADAWANZZ is already dispositioned through current-main differential audit `WS-QE-2026-ADM-001`.

## Submission state after GitHub restoration

- **QSB / Yukon:** GitHub connectivity blocker is cleared; **OFFICIAL RESULT PENDING / NOT YET SUBMISSION-QUALIFIED** until challenge-permitted source, frozen evaluator/harness, CPU hit reconstruction, provenance checks, and official Yukon evaluation are complete.
- **ECDSA.fail:** GitHub connectivity blocker is cleared; **NOT YET SUBMISSION-QUALIFIED** until allowed-source-only changes, required shots/correctness, clean ancillae, phase cleanliness, forward/reverse validation, and official CLI submission pass.
- **SCAR / Space Safari / defense opportunities:** not GitHub-only blockers. Eligibility, SAM/entity/UEI/CAGE, SPRS/NIST 800-171, JCP/DD2345, CUI/export-control, partner, library-access, and solicitation-specific gates remain controlling where applicable.

## Claims rule

A merge proves only the bounded repository/software claim stated by that PR. It does not establish field, flight, clinical, production, regulatory, partner, certification, accreditation, award, or deployed-network status unless those are independently evidenced by the named gate.
