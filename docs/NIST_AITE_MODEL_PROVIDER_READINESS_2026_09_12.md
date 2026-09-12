# Worldshepherd — NIST AITE model-provider readiness assessment

**Status:** PREPARATION ONLY / NOT ENROLLED / NOT SUBMITTED  
**Program:** NIST Artificial Intelligence Technology Evaluation (AITE)  
**Date:** 2026-09-12

## 1. Purpose

Assess whether a bounded Worldshepherd model or model adapter could legitimately enter NIST AITE as a **model provider** without misrepresenting the broader Worldshepherd/SARA system as an AITE-compatible model or treating an eventual AITE score as AGI/system/deployment validation.

## 2. Authoritative AITE boundary

NIST describes AITE as a neutral third-party, sequestered testbed that evaluates AI model performance on blind data to reduce train/test contamination. AITE supports two participant tracks: data providers and model providers. Participation is open to participants that can abide by the AITE Participation Agreement and rules.

Current Phase 1 accepts only a very limited number of additional application tests and models. Models are queued first-come, first-served as capacity permits. The initial tasks are image-analysis / vision-language-model tasks in quantum science, genomics, and public-safety video. NIST states that any model meeting the API and evaluation criteria may be submitted.

NIST states that submitted models/data are treated as controlled unclassified information and that results are public. The AITE roadmap says published results identify model, dataset, task, metric, scores, and uncertainty. NIST expressly disclaims endorsement and cautions that performance on the current small task set should not be generalized automatically to new data or tasks.

## 3. Worldshepherd fit

### Potentially reusable internal concepts

Pending PR #168 contains an internal AGI/evaluation stack with protected-artifact custody, pre-run commitments, post-run result sealing, provenance, external-evaluator handoff rules, and replication controls. Those controls are conceptually useful for preparing an external evaluation, but PR #168 remains open and is not itself AITE evidence.

### What AITE would evaluate

AITE evaluates the submitted **model implementation/API**, not the Worldshepherd governance architecture as a whole. SARA, PRIME SENTINEL, ECHO SENTINEL LINK, OVERWATCH, the AGI gate, human approvals, orchestration, and deployment controls must not be counted as model-performance evidence unless the relevant AITE specification explicitly includes them in the submitted artifact and scoring protocol.

## 4. Current readiness state

`AITE_MODEL_PROVIDER_STATE = NOT_READY`

Blocking gaps:

1. **Participation Agreement not reviewed/accepted.** No agreement, registration, or NIST invitation/acceptance is claimed.
2. **Exact AITE API contract not implemented.** The public FAQ states compatible models must adhere to the API, but this branch does not claim an AITE-compatible adapter.
3. **Initial-task compatibility not established.** The current tasks emphasize VLM/image analysis in quantum-dot, genomics, and public-safety domains. Worldshepherd has not demonstrated a submitted model matching those tasks.
4. **CUI handling path not validated.** NIST states submitted models/data are treated as CUI. Worldshepherd's internal NIST 800-171 precursor work does not establish authorization or readiness to exchange/process CUI for AITE.
5. **Public-result consent not given.** Results are intended to be public and associated with model identity; explicit organizational approval is required before participation.
6. **Entity/submitter identity unresolved.** Curious nerdworX LLC remains in formation in current Worldshepherd records. A precise legal submitting organization must be established before representing an organizational participation state.
7. **No external score exists.** Internal CI, public benchmarks, synthetic tests, or PR #168 evidence must not be represented as AITE results.

## 5. Proposed bounded adapter architecture

If the participation/API requirements are obtained and approved, implement a dedicated `AITE_MODEL_ADAPTER` with these properties:

- one fixed submitted model/version identity;
- exact task-specific request/response schema required by NIST;
- no hidden access to holdout/evaluation labels;
- no training, self-modification, retrieval of protected answers, or state carryover unless explicitly permitted by the AITE specification;
- deterministic configuration manifest and dependency lock;
- bounded timeout/resource policy;
- input/output hashing and local evidence record **outside** any prohibited interaction with the evaluator;
- explicit separation between the submitted model and SARA/PRIME/ECHO/OVERWATCH governance components;
- version freeze before submission;
- a mapping from NIST-reported metrics to Worldshepherd evidence records without promoting the score beyond the tested task;
- public-result acknowledgement and claims-control language.

## 6. Acceptance criteria before contacting NIST for participation

A preparation package is ready for a model-provider inquiry only after:

- [ ] the current AITE Evaluation Plan and Participation Agreement are obtained and reviewed;
- [ ] at least one active AITE task is technically compatible with a model Worldshepherd can lawfully submit;
- [ ] the task/API specification is implemented locally against public/synthetic fixtures;
- [ ] the submitted model identity/version is frozen;
- [ ] CUI handling implications are reviewed and an allowed exchange/deployment path is established;
- [ ] the legal submitter/organization is accurately identified;
- [ ] CRE1AWS explicitly accepts public-result publication risk;
- [ ] the claims-control statement below is included in any participation inquiry.

## 7. External-safe claims statement

> Worldshepherd is evaluating whether a bounded model implementation can meet NIST AITE's model-provider API and participation requirements. Worldshepherd has not been accepted into AITE, has not submitted a model, and has no AITE result. Internal evaluation/governance artifacts are not NIST validation and are not being presented as evidence of AGI, certification, operational readiness, endorsement, or system-level performance.

## 8. Relationship to the Worldshepherd AGI gate

An AITE result, if later obtained, should enter the AGI/evaluation stack as **one externally generated, task-scoped evidence item**. It must not by itself change `intelligence_state`, establish AGI, establish replication across unrelated lanes, establish deployment authorization, or establish scientific consensus.

AITE is therefore valuable precisely because it supplies a neutral, blind-data measurement source while preserving the Worldshepherd rule that no single benchmark or evaluator can silently promote broader capability claims.

## 9. Next action

Do **not** contact or enroll automatically. First obtain/review the current Participation Agreement and task/API specifications, then prepare a concise non-proprietary model-provider inquiry for CRE1AWS review. The public AITE contact listed by NIST is `aite-poc@list.nist.gov`.

## Claims boundary

This document is internal preparation based on public NIST AITE material and repository state. It does not establish AITE participation, NIST acceptance, CUI authorization, standards conformity, certification, independent validation, AGI, or operational readiness.