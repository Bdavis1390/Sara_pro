# Worldshepherd — Scientific evidence continuation (2026-11-09)

**Status:** candidate integration on a review branch. **Owners:** umbrella #281 (platform assurance), #282 (science/validation), #283 (growth/externalization). This document adds no top-level tasks and does not change existing claim maturity.

## Purpose

Convert Worldshepherd's scientific-discovery objective into a repeatable protocol: propose a falsifiable question, preregister a claim and null hypothesis, retain failed controls, verify data lineage, reproduce results, challenge interpretations, and submit evidence to human/independent review. Prediction, AI-generated rationale, paper, simulation, and physical observation are different evidence categories.

**Policy source of truth:** `docs/CLAIMS_AND_EVIDENCE_POLICY.md`; supporting maturity map: `docs/WORLDSHEPHERD_CAPABILITY_MAP.md`. The v0.2 candidate under `tools/claim_evidence_gate/` is a **standalone adapter** and must not be described as an installed SARA subsystem.

## Current evidence ledger and next gates

| Workstream | Evidence available or historical state | Current defensible description | Specific next gate | Umbrella |
| --- | --- | --- | --- | --- |
| SARA / PRIME / ECHO / OVERWATCH | Canonical local runtime, CI and governance/provenance documentation in this repository | Implemented software for explicitly tested boundaries; partner/operational assertions require their own tests | Exact-commit clean clone, independent witness verification, controlled SARA adapter review | #281 |
| Scientific claim gate | Local v0.2 standard-library reference implementation; synthetic example; 17 local regression tests passing on 2026-11-09 | Internal test of evidence envelope integrity, **not** scientific truth or formal assurance | Protected CI, supply-chain review, signed ECHO anchor, schema compatibility, human review | #281 |
| RF / resonance and adaptive materials | Hypotheses, models and relevant published research; no newly confirmed calibrated material energy-exchange result from this work session | HYPOTHESIS / SIMULATED ONLY as appropriate to each artifact | Predeclared blind comparison, detector-nonlinearity controls, calibrated RF power ledger, phase/reference and uncertainty budget, independent replicate | #282 |
| Quantum formal reasoning | Public AI-assisted formal proof methods offer reusable verification patterns; no Worldshepherd independent kernel replay completed here | Methodology and reproducibility target, not Worldshepherd theorem proof | Pin Lean/compiler/dependency versions; theorem-statement correspondence audit; reproduce kernel checks; check assumptions | #282 |
| Original Palace 54-anchor campaign | Private recovery README records zero exit codes for A001–A036 but 12 60° GMRES nonconvergences; A037/A038 failed; A039 hit a memory gate; A040–A054 unexecuted at recorded checkpoint | **INCOMPLETE**, process exit is not solver convergence; historical state may have changed after that record | Reconcile latest private logs; independently check tolerances/residuals/boundary conditions; supervised A039; resume remaining cases only within approved compute budget | #282 |
| 18 dissertations | User-directed portfolio in progress; this document does not assert manuscripts were individually audited | Manuscript/evidence inventory **not yet established** here | Obtain canonical title, version, author, claim, raw evidence, novelty search, replication gate and independent reviewer for each thesis | #282 |
| Space sensing / optical communications | Public Titania/Inaros developments and existing Worldshepherd space/autonomy design work | Technology relevance / systems-research, **not** qualified flight hardware | Optical-link and sensor simulation with fault injection, calibrated measurements, qualified interface evidence | #282 |
| External opportunities, IP and partnerships | Existing #283 outreach/capture workflow; no submission or partner validation inferred from this document | PIPELINE / REVIEW REQUIRED | Verify live solicitation/contact; separate approval, release/IP and submission gates; use approved evidence-qualified language | #283 |

## Proposed machine-verifiable control loop

1. **PRE:** prepare research question, competing models, quantitative observable, null, preregistered acceptance/falsification criteria.
2. **PRIME:** obtain bounded owner authorization for freeze, execution, budget and eventual release.
3. **SARA:** route experiment/simulation/proof with exact configuration, code version, environment and timestamp.
4. **ECHO:** retain raw input/output hashes and, after integration, independently anchored receipts (a string is not a verified signature).
5. **OVERWATCH:** reconcile every event against summaries, check required control outcomes, expose contradictions, exceptions and unverified claims.
6. **Scientific review:** separate software integrity, numerical convergence, proof soundness, empirical calibration, novelty, and independent reproduction.
7. **Human approval:** promote claims only within observed scope; failed tests are never deleted.

## Gate acceptance criteria for prototype v0.2

- 100% of declared raw artifacts verified against their recorded SHA-256 in a bounded test snapshot.
- Exact preregistered schema hash must match a **separately trusted** pre-run pin; shipping the pin with the package is not independent anchoring.
- All required controls must be verified `kind=control` and `PASS`; an incorrect or absent hash fails the control.
- Status requests must match claim types and contain a verified artifact of the corresponding evidence class.
- Summary/event count and event IDs must reconcile.
- Outcome is always `claim_automatically_proven=false`, `external_independence_verified=false`, `requires_human_review=true`.
- Local test result is only local; no GitHub CI, hardware experiment, certified system, independently validated scientific result, or partner endorsement is claimed until evidence is attached.

## Release / confidentiality

This is a **public** repo. Do not add private Palace archives, proprietary experimental logs, unique unpublished apparatus configurations, credentials, CUI, export-controlled information, or ownership-sensitive draft IP. Generic synthetic fixtures are safe for public software-method review. Confidential scientific records remain in owner-controlled stores and should be referenced by approved, nonrevealing hashes only after the public-release gate.

## Next integration decision

Review `tools/claim_evidence_gate/` as a standalone research adapter. Do not install it into canonical SARA or change `main` until the PR's CI, policy review and integration tests succeed. Preserve the distinction between internal software test pass and actual science.
