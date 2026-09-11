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
- Pre-GD-15 head reviewed for this note: `f1e13148fdff2e3b3406f62e5fc9e5de31d52443`.
- PR #116 currently represents **815 additions across 9 changed files** relative to `golden-dome-rmabm-g2d`.
- The 815-line figure is a PR-diff measure; it is **not** the final evaluator-package line count.
- The evaluator package must include the complete import/dependency closure required by the frozen execution path.

## Current execution dependency closure

The G4 evaluation path includes at least:

- `worldshepherd_sara/rmabm_external_evaluation.py`
- `worldshepherd_sara/rmabm.py`
- `worldshepherd_sara/mission_replay.py`
- `worldshepherd_sara/sensor_fusion.py`
- `worldshepherd_sara/prime.py`
- `worldshepherd_sara/qualification.py`
- package initialization material required for import
- `tools/rmabm_external_evaluation.py`
- `tests/test_rmabm_external_evaluation.py`
- evaluator protocol, scorecard, and handoff documents
- dependency/install metadata required for a reproducible clean-environment run

The final transfer manifest must be generated from the actual frozen evaluator bundle rather than inferred from PR statistics.

## Runtime facts and claims control

Repository metadata declares Python `>=3.11`. The existing verified container path uses a pinned `python:3.12-slim` base image. The main project metadata includes FastAPI, Uvicorn, and Pydantic, with pytest/httpx as test extras; however, the narrow G4 evaluation path should be reduced to and tested against the smallest dependency set actually required by the evaluator bundle.

The evaluation logic is CPU software and does not depend on a GPU, accelerator, external sensor, classified system, operational data feed, or network connection during benchmark execution.

The previously communicated `2 CPU cores / 4 GB RAM / <1 GB working storage` values are **planning estimates, not measured minimum requirements**. Before a transfer package is frozen, run a clean-environment resource rehearsal and record peak memory, disk footprint, wall-clock runtime, Python version, OS/kernel/container details, and dependency versions. Future external wording should distinguish measured requirements from planning estimates.

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

1. **Evaluator route confirmed** — Aerospace identifies the technical/commercial mechanism and authorized transfer channel.
2. **Minimal bundle defined** — exact dependency closure, docs, test harness, CLI, synthetic generator, and scorecard selected.
3. **Dependency set reduced and pinned** — evaluator-only install path documented.
4. **Clean-environment rehearsal completed** — Linux x86-64/Python 3.12 reference run with measured resource usage and no external data dependency during execution.
5. **Expected-results fixture prepared** — demonstration seeds may be documented, while the final evaluator seed remains evaluator-selected.
6. **Leakage review passed** — no secrets/CUI/classified/export-controlled/proprietary operational material.
7. **Manifest generated** — file path, bytes, lines, SHA-256, frozen commit/ref, and bundle digest.
8. **Human release review completed** — only then may the authorized package be transferred.

## Current relationship/evidence state

Aerospace's technical questions constitute substantive scoping interest, not acceptance, contract award, validation, or agreement to evaluate. G4 remains **PREPARED / OUTREACH ACTIVE — NOT INDEPENDENTLY REPRODUCED** until an evaluator outside the Worldshepherd development process performs the frozen protocol in an evaluator-controlled environment and records all mandatory assertions as passing.
