# GD-15 — Aerospace G4 Technical Handoff Preparation

**Posture:** INTERNAL CAPTURE / CLAIMS-CONTROLLED / NOT AUTHORIZED FOR EXTERNAL TRANSMISSION

## Purpose

Translate the Aerospace technical-team scoping questions into a verified handoff-preparation checklist for the W-RMABM G4 independent synthetic-software reproduction path.

This document does not authorize source release, create a contract, commit to schedule or price, or establish external validation.

## Communication state

Aerospace asked five scoping questions:

1. How big is the codebase?
2. What hardware/software is needed to run it?
3. How will the software be delivered?
4. Will Worldshepherd provide synthetic input data, documentation, and expected results?
5. When is the work needed?

A technical answer has already been sent. No further technical follow-up should be sent unless Aerospace responds or asks for a package/engagement step.

## Verified repository facts

- Draft PR: `#116` — `W-RMABM G4 independent reproduction preparation`.
- Current G4-prep branch: `golden-dome-rmabm-g4prep`.
- The originally communicated PR scope was **815 additions across 9 changed files** relative to `golden-dome-rmabm-g2d` before later handoff-preparation hardening.
- The 815-line figure is a historical PR-diff measure; it is **not** the evaluator-package line count.
- A minimal evaluator dependency closure has now been built and exercised independently of the broader SARA service stack.

## Evaluator bundle closure

The clean evaluator bundle candidate contains these 13 manifested source artifacts:

- `requirements-g4-evaluator.txt`
- `worldshepherd_sara/__init__.py`
- `worldshepherd_sara/rmabm_external_evaluation.py`
- `worldshepherd_sara/rmabm.py`
- `worldshepherd_sara/mission_replay.py`
- `worldshepherd_sara/sensor_fusion.py`
- `worldshepherd_sara/prime.py`
- `worldshepherd_sara/qualification.py`
- `tools/rmabm_external_evaluation.py`
- `tests/test_rmabm_external_evaluation.py`
- `docs/GD-10_G4_EXTERNAL_REPRODUCTION_PROTOCOL.md`
- `docs/GD-11_G4_EXTERNAL_EVALUATION_SCORECARD.md`
- `docs/GD-13_G4_EVALUATOR_HANDOFF.md`

The staged bundle additionally contains generated `MANIFEST.json` and `README_EVALUATOR.md`. CI verifies that no other file is present after execution caches are removed.

## Measured reference rehearsal

A branch-bound GitHub Actions rehearsal completed successfully against candidate commit:

`fa040b66d0dc3f9d7f7576d4d50a29ab465fe629`

Reference environment:

- Linux x86-64 GitHub-hosted Ubuntu runner;
- Python `3.12.14`;
- evaluator-only pinned Python dependencies;
- CPU execution only;
- no external mission-data feed required during benchmark execution.

Measured bundle properties:

- manifested source artifacts: **13**;
- manifested source bytes: **58,033 bytes**;
- manifested source lines: **1,500 lines**;
- total staged file bytes including generated manifest and evaluator README: **62,968 bytes**;
- bundle-content SHA-256: `f274cf792d4bd6669502739ee7e1304fde2a6cefc63d8bcd7e4b0b69cac14aec`;
- cache/unmanifested-file closure check: **PASS**.

Measured single synthetic CLI rehearsal on that CI reference environment:

- elapsed wall-clock time: **0.19 seconds**;
- maximum resident set size: **31,756 kB**;
- exit status: **0**;
- swaps: **0**;
- socket messages sent/received reported by `/usr/bin/time -v`: **0 / 0**.

These are **reference observations, not minimum hardware requirements, capacity guarantees, or performance benchmarks**. They substantiate that the previously communicated `2 CPU cores / 4 GB RAM / <1 GB working storage` planning configuration is conservative for this narrow reference run, but they do not establish tested minimums. Aerospace may use a different evaluator-controlled configuration.

The PR-triggered rehearsal also passed, but GitHub's pull-request checkout used a synthetic merge commit. For source-revision provenance, the branch-bound push-run candidate above is the preferred internal reference.

## Evaluator-only dependencies

The narrow bundle no longer requires the broader FastAPI/Uvicorn service stack. Its pinned test/reproduction environment consists of:

- `annotated-types==0.8.0`
- `pydantic==2.13.4`
- `pydantic-core==2.46.4`
- `typing-extensions==4.16.0`
- `typing-inspection==0.4.4`
- `iniconfig==2.3.0`
- `packaging==26.3`
- `pluggy==1.6.0`
- `Pygments==2.21.0`
- `pytest==8.4.2`

`pip==26.2.1` was used in the CI reference environment. Package-file hash locking remains a future hardening gate; exact version pinning alone must not be described as cryptographic dependency provenance.

## Synthetic inputs and expected results

The evaluator controls the final challenge seed and challenge identifier. Worldshepherd may provide the deterministic generator and protocol but must not select the final recorded seed.

The required evidence checks remain:

- same-seed deterministic challenge/result reproduction;
- distinct challenge binding for different seeds;
- `HOLD` when identified human authority is absent;
- `BLOCK` for prohibited consequential-action requests;
- rejection of post-hash challenge mutation;
- attestation binding challenge, result/audit, replay, decision counts, and claims boundary.

Expected results are bounded control assertions only. They are not expected mission-performance results.

## Delivery posture

No package should be transmitted until Aerospace confirms an institutionally permissible engagement and transfer mechanism and Worldshepherd completes release review.

Permissible delivery candidates, subject to Aerospace preference and release approval:

1. checksum-bound source archive;
2. exact repository snapshot/commit reference;
3. source archive plus evaluator-specific dependency constraints;
4. reproducible container definition and pinned base-image digest, if permitted by the evaluator environment.

Every delivered artifact should be represented in a SHA-256 manifest with exact path, bytes, line count where meaningful, and digest.

Do not include credentials, secrets, private keys, CUI, classified material, export-controlled mission data, proprietary government/vendor interfaces, real threat data, or operational missile-defense data.

## Schedule posture

There is no government or contractual deadline attached to this independently initiated request. The communicated two-to-four-week evaluation window is a preference after an approved frozen handoff, not a contractual commitment or evaluator deadline.

## Required gates before material transfer

1. **Evaluator route confirmed — OPEN.** Aerospace must identify the technical/commercial mechanism and authorized transfer channel.
2. **Minimal bundle defined — PASS internally.** Exact evaluator dependency closure, docs, test harness, CLI, synthetic generator, and scorecard are selected.
3. **Dependency set reduced and pinned — PASS internally.** Evaluator-only install path exists and has been exercised in CI.
4. **Clean-environment rehearsal — PASS for reference environment.** Linux x86-64/Python 3.12 run completed with recorded resource observations; this does not establish minimum hardware.
5. **Expected-results fixture — PASS internally.** Demonstration/rehearsal seeds may be documented, while the final evaluator seed remains evaluator-selected.
6. **Leakage review — REQUIRED AT FINAL FREEZE.** No secrets/CUI/classified/export-controlled/proprietary operational material may be present.
7. **Manifest generated and closure-checked — PASS for candidate `fa040b66...`.** Paths, bytes, line counts, per-file SHA-256 values, source revision, and bundle digest are recorded; caches/unmanifested files are rejected.
8. **Human release review — OPEN.** Only after evaluator route/terms are known and the final transfer candidate is re-frozen may release be authorized.

## Current relationship/evidence state

Aerospace's technical questions constitute substantive scoping interest, not acceptance, contract award, validation, or agreement to evaluate. G4 remains **PREPARED / OUTREACH ACTIVE — NOT INDEPENDENTLY REPRODUCED** until an evaluator outside the Worldshepherd development process performs the frozen protocol in an evaluator-controlled environment and records all mandatory assertions as passing.
