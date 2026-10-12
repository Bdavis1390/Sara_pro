# Worldshepherd post-suspension portfolio registry — 2026-09-30

Status: **PUBLIC-SAFE RECONCILIATION REGISTRY**
Window: 2026-09-17 GitHub disruption through 2026-09-30 restoration/requalification work
Parent control: `POST_SUSPENSION_MASTER_LEDGER_2026-09-30.md`
Closure queue: GitHub Issue #518

This registry is intentionally broader than the code currently merged on `main`. Its purpose is to make material post-disruption work discoverable while preserving the difference between merged code, active pull requests, exact off-host custody artifacts, reconstructed work, external submissions, partner validation, and research hypotheses.

## Status vocabulary

- **MAINLINE** — merged/current protected repository evidence exists.
- **ACTIVE PR** — current GitHub PR exists; merge gates still apply.
- **HISTORICAL PR / REPLAY REQUIRED** — pre/restoration branch or PR is evidence but is not automatically current-main compatible.
- **OFF-HOST CUSTODY** — exact artifact exists outside public GitHub; publish only after provenance/disclosure review.
- **EXTERNAL VALIDATION / SUBMISSION** — work depends on an outside evaluator, challenge, partner, customer, or institution.
- **RESEARCH / HYPOTHESIS** — reproducible research may exist, but stronger physical/clinical/operational claims are not established.

## Core governance, recovery, and runtime

| Workstream | GitHub/public disposition | Evidence state / claim ceiling | Next gate |
|---|---|---|---|
| Post-suspension reconciliation control plane | **MAINLINE — PR #506 merged** | Recovery/governance software and process | Keep ledger/registry synchronized |
| TimeAuthority + ECHO Time Custody v0.2 | **MAINLINE — PR #511 merged** | Implemented/tested software | Continue current-main regression evidence |
| SDA mTLS wall-clock-valid fixture | **MAINLINE — PR #509 merged** | CI/test infrastructure fix | Preserve date-independent requalification |
| Yellow-Hat V22 controlled build | **MAINLINE — PR #510 merged** | Controlled-build/review evidence only | Independent verifier/signer custody/trusted-time/off-host-attestation gates remain |
| SARA Verified Local / SSPADAWANZZ | **MAINLINE**; current differential audit `WS-QE-2026-ADM-001` | `IMPLEMENTED IN SOFTWARE`; relay is governed local recording/audit, not external delivery | Current protected CI; no reuse of historical `6 passed` as current evidence |
| PRIME SENTINEL V2 | **HISTORICAL / RECOVERY LANE** | Prototype/authorization research; not canonical SARA by default | Current-main differential + regression |
| OVERWATCH | **MAINLINE/ARCHITECTURE LANE** | Observability/COP governance component | Keep evidence/claim separation with each integrated lane |
| Continuity Recovery V3 | **OFF-HOST CUSTODY** | Functional recovery/reconstruction reported with 177 tests; exact Git parity was not then certified | Exact-object comparison where gaps remain |
| Continuity Recovery V16 WHITEHAT | **OFF-HOST CUSTODY**; SHA-256 `ead45812bd3ce80912c9a5a71548fccbf9bdea929ea9d8cd2ade357bc73a887a` | 59/59 SARA, 114/114 Agent Authority, 10/10 QCRYPTO, 687/687 manifest, 13/13 validation; **production readiness false** with ten evidence blockers retained | Reconcile unique deltas against protected current main; do not overwrite newer code |
| Worldshepherd Engineering Release v0.21 | **RECOVERY BASELINE / OFF-HOST + historical repo evidence** | Frozen engineering-release evidence | Account for unique content in current registry |
| Lenovo/local exact-object recovery | **ISSUE #518** | Exact-object/provenance operation | Resolve listed BAROS/QPHONON/QX/ATIP/WS-SDA gaps without fabricated ancestry |

## Trust fabric, AGI, and autonomous control

| Workstream | GitHub/public disposition | Evidence state / claim ceiling | Next gate |
|---|---|---|---|
| WS-SDA G1–G10 trust fabric | **HISTORICAL PR / REPLAY REQUIRED**; early merged G1/G2 lineage plus later clean recovery stack #498–#505 | Implemented/tested software by gate; external/independent replication remains lane-specific | Sequential current-main replay; account for stale parallel PR unique work |
| Competent AGI Qualification Gate | **HISTORICAL PR #489 / replay-review** | Qualification framework only; **not certified AGI** | Held-out transfer/causal/reset/rule-change and external evaluation |
| General-Agent Runtime v0.2 | **HISTORICAL PR #493 / replay-review** | Implemented research software | Current-main replay and held-out capability tests |
| Executable Novel-Skill Lab | **HISTORICAL PR #495 / replay-review** | Implemented research software | Backend + held-out transfer/novel-skill validation |
| Open-ended AGI patch | **OFF-HOST CUSTODY**; one frozen patch SHA-256 `2b08387af726ff23294aac28a6ad75b8d6e6b8c798420e160d750cd5f5dd6b15` | 10/10 local tests on frozen patch; no AGI certification claim | Compare/replay only if unique relative to current AGI branches |
| BDS-NG26 RI-0.1F | **POST-DISRUPTION R&D LANE** | Internal/reproducibility stage | RI-0.1G HIVE capability + independent verification |
| HIVE/SWARM coordination | **CROSS-CUTTING R&D** | Architecture/software/simulation depending on implementation | Delay/AoI, event-triggered comms, deterministic safety, consensus, provenance, human-authorization validation |
| 13+1 drones / humanoids / companion platforms | **RESEARCH / DESIGN LANE** | Requirements/design hypotheses until model/bench/flight evidence | Co-design battery/propulsion/structure/sensing/autonomy/manufacturing; hardware validation |

## Quantum, cryptography, and verification

| Workstream | GitHub/public disposition | Evidence state / claim ceiling | Next gate |
|---|---|---|---|
| QCRYPTO production/KMS candidate | **HISTORICAL PR #208 + recovery artifacts** | Host-ready/research deployment evidence; no live-value authorization | Current-main disposition + external/live handshake evidence where appropriate |
| QCRYPTO Bitcoin Hardening v2.3/v2.4 | **OFF-HOST CUSTODY** during suspension | v2.4 reported 163/163 + compileall; no deployed-network adoption claim | Reconcile unique deltas into later current QCRYPTO line |
| QCRYPTO Bitcoin Hardening v3.0–v3.2 | **OFF-HOST / external reproduction packages** | Frozen independent-reproduction artifacts circulated to external reviewers | Preserve custody/provenance; reconcile unique code/evidence into v3.6/current line |
| QCRYPTO + TSV v3.6 | **ACTIVE PR #512 — DRAFT** | Exact package 301/301; dedicated recovery gate/CodeQL/resilience/NIST/closure pass; required gate blocked only by recovered trailing-whitespace projection | Create separately recorded CI-clean Git projection; rerun full exact-head gates; do not alter custody identity |
| Hybrid PQ Proof-of-Ownership / PoO | **HISTORICAL PR #356 + policy branch** | Verified-local hybrid Ed25519-quorum + FIPS 204 ML-DSA-65 evidence; policy binding still a separate gate | Bind policy ID/epoch/digest/suite into signed authorization and requalify current-main |
| Bitcoin migration exposure baseline v0.1 | **ACTIVE PR #514** | Evidence-bounded exposure classifier + human-gated migration-state model; no live funds/signing/broadcast | Exact-head CI; fixture-derived script classification; key-reuse reconciliation; non-broadcasting simulator |
| QSB / Yukon optimization | **EXTERNAL SUBMISSION** | Internal candidate/performance work exists; official result not yet established | Permitted-surface check, frozen verifier/harness, CPU hit reconstruction, provenance scan, official Yukon evaluation |
| ECDSA.fail optimization | **EXTERNAL SUBMISSION** | Optimization/research candidates exist; official validity/submission not yet established | Allowed-source-only diff, shot/correctness, clean ancillae, phase cleanliness, forward/reverse validation, official CLI submit |
| QPHONON v0.4 | **OFF-HOST + HISTORICAL PRs #207/#441/#448** | Reconstructed archive reported 12/12 offline tests; exact late ancestry incomplete | Issue #518 exact/replay reconciliation; current-main tests |
| WS-QBENCH | **RESEARCH / REPRODUCIBILITY** | Reproducibility-audit stage; exact projected-displacement validation; unresolved convention/sign issue preserved | Resolve convention discrepancy with falsifiable source-convention audit |
| WS-QFLOQUET | **RESEARCH** | Peer-reviewed-literature supported / numerically demonstrated | Hardware/partner validation before performance claims |
| WS-QX 0.1 | **HISTORICAL PR #410 / exact-object target** | Evidence-qualification substrate | Issue #518 current-main recovery without fabricated ancestry |
| Q-VCP through v1.0 | **OFF-HOST / R&D** | v0.7: 32,768-pattern agreement, fault cases; v1.0: 10,272-location routability audit; promotion withheld | Independent reproduction, hash/source verification, schedule recomputation, corruption tests, fault campaigns |
| SCITT/CCF / COSE adversarial corpus | **EXTERNAL VALIDATION / RESEARCH** | Pinned multi-vector corpus; accepted/refused separation; external implementation evidence only | Controlled policy-vs-cryptographic-commitment adjudication and independent reproduction |
| QCRYPTO external reproducer | **EXTERNAL VALIDATION** | Supabase/hosted execution evidence lane; availability/custody must remain explicit | Preserve/export evidence; re-run only under controlled reproducible environment |

## Materials, EM, propulsion, and physics

| Workstream | GitHub/public disposition | Evidence state / claim ceiling | Next gate |
|---|---|---|---|
| UC06-P1 / programmable EM control | **ACTIVE PR #513 — DRAFT** | Diagnostic/software implementation only; no hardware actuation/convergence claim | Content-aware current-main merge; D5 residual adjudication; medium/fine recovery evidence |
| Programmable EM boundary / metasurface architecture | **MAINLINE research ingest + UC06** | Architecture/hypothesis/simulation depending on artifact | Hardware tile/component validation; calibrated field/scattering measurements |
| WS–AlTi M1-MSZ-Prime | **MAINLINE public-safe research ingest; fuller package held under IP strategy** | IP-stage programmable deposited aluminum meta-alloy thesis | Filing/modeling/coupon/microscopy/mechanical/thermal/environmental + partner validation |
| Constitutive discovery v0.4/v0.5 | **RECOVERY LANE** | Numerical/material-model R&D | Compare exact revisions, current-main qualification, independent data validation |
| Plasma / field-stability propulsion research | **RESEARCH / HYPOTHESIS** | Field stability, density, EM confinement, thermal/control variables; no unexplained-thrust claim | Calibrated force accounting, controls, repeatability, competing explanations |
| Acoustic levitation | **RESEARCH INTAKE** | Literature/physics intake until reproduced | Quantitative model + controlled experiment if promoted |
| Boron allotrope/materials intake | **RESEARCH INTAKE** | Frontier material research input | Source verification + application-specific model/validation |
| LHC/accelerator developments | **RESEARCH INTAKE** | External frontier input | Reproducible notes/models only where directly relevant |
| W-state / quantum-decay / quantum-control intake | **RESEARCH INTAKE** | External result analysis and internal modeling | Reproduction/source audit before stronger internal claims |
| Space solar / space-energy intake | **RESEARCH INTAKE** | External technology analysis | System-level performance/cost/thermal/orbital model before integration claims |

## Flight, space, digital engineering, and operating environment

| Workstream | GitHub/public disposition | Evidence state / claim ceiling | Next gate |
|---|---|---|---|
| WS-FLIGHT-001 v0.2 | **OFF-HOST / partner-validation package** | Executable read-only/shadow software; synthetic tests pass; not flight-qualified/host-validated | Simulator/HIL or approved host interface/resource envelope |
| WS-FLIGHT-001-SPIRE v0.1 | **OFF-HOST / partner-validation package** | Python 3.6-compatible shadow package; not Spire-host validated | Spire sandbox/runtime, telemetry, resource, persistence/downlink requirements |
| Orbital validation — Spire / Rocket Lab / EnduroSat / D-Orbit | **EXTERNAL VALIDATION / OUTREACH** | Ground/HIL-first proposal; no flight integration claim | Partner response + approved interface + ground/HIL evidence before flight |
| SPACEGHOST SG-QA 001–007 | **RECOVERY LANE** | Frozen QA/research artifacts | Inventory unique deltas and current-main relevance |
| CAE / DATL | **RECOVERY LANE** | Engineering/data-assurance tooling lane | Current-main compare and claims mapping |
| QNCP / skill-enforcement | **RECOVERY LANE** | Governance/runtime supporting artifacts | Compare against current SARA/agent-authority implementation |
| WS-SOE v0.1A / NixOS canary | **CANARY / RESEARCH** | Environment experiment only | VM/canary evidence; no workstation cutover until gates pass |
| Ubuntu/Lenovo continuity | **OFF-HOST OPERATIONS** | Backup/recovery and non-destructive workstation continuity | Keep repos/artifacts/checksums recoverable; avoid secrets/private data in Git |

## Security and supply-chain assurance

| Workstream | GitHub/public disposition | Evidence state / claim ceiling | Next gate |
|---|---|---|---|
| White/Blue/Red/Grey/Yellow/Black-hat Worldshepherd audits | **DEFENSIVE SECURITY PROGRAM** | Bounded authorized hardening lenses | Continue finding→fix→regression cycle; no “perfect security” claim |
| SPDX 3.x / PQC proposal | **ACTIVE PR #507 — DRAFT** | Internal adapter/proposal/fixtures; no upstream acceptance claim | Current CI + SPDX community discussion/consensus before external contribution PR |
| OCSF compiled-schema invariant / MISP lane | **HISTORICAL CONTRIBUTION LANE** | Prior implementation/contribution evidence; G3/external route remained | Revalidate against current upstream/project state before further submission |
| SARA software SBOM / dependency / vulnerability evidence | **MAINLINE CI** | Build/security evidence | Maintain pinned/reproducible evidence and human-review triage |
| Authority v3 / governed authorization APIs | **R&D / SERVICE LANE** | Real database authorization flow and ECHO receipts reported; external verifier remained a gate | Current-main source/evidence mapping + independent verifier |

## Opportunities, submissions, and partner validation

| Workstream | GitHub/public disposition | Evidence state / claim ceiling | Next gate |
|---|---|---|---|
| SCAR AOI 03/01 | **EXTERNAL CAPTURE / PARTNER LANE** | Bounded assurance adapter concept; no integration/TRL claim before approved-interface demo | Library access/compliance; narrow emulator/interface test; answer government clarification schedule |
| Space Safari / SSC SYD89-26-RPO-RLSV | **EXTERNAL RFI LANE** | Mission-assurance pathway may be outside core scope; response alignment work continues | Entity/SAM/UEI/CAGE, NIST 800-171/SPRS, JCP/DD2345/CUI gates and RFI-specific fit before submission |
| Mars Hill Appalachian Resilient Systems & Governed AI Testbed | **EXTERNAL PILOT OUTREACH** | Phase-0 software/data evaluation concept | Academic/data-validation scope, measurements, local partner, later funded-agreement gate |
| DEM&S CoP / Trustworthy Digital Ecosystems | **SUBMITTED INTEREST** | Participation/presentation interest sent | Registration/presenter guidance |
| JHU/APL AFRL IDIQ capability statement | **SUBMITTED CAPABILITY** | Capability statement sent | Technical/subcontracting/collaboration routing |
| SEI IV&V / software assurance | **EXTERNAL VALIDATION INQUIRY** | Frozen-artifact fit inquiry initiated | Fit response, then protocol/test-matrix if invited |
| ATLAS teaming / SCAR assurance adapter | **PARTNER OUTREACH** | Proposed bounded adapter; no integration claim | Partner/customer interface and emulator evidence |
| AI Force / OSTP / NIST AI TE / broader public-sector AI assurance | **OUTREACH / OPPORTUNITY LANE** | Governance/evaluation positioning | Program-specific eligibility, artifact, and evaluation gates |
| Curious nerdworX / Brandon Davis Solutions commercialization | **REVENUE / COMMERCIALIZATION LANE** | Commercial umbrella; claims inherited from underlying evidence only | Package validated work by contribution, IP, disclosure, and partner readiness |
| Sierra Space / space-industry validation | **PARTNER OUTREACH** | Validation/partnership request lane | Concrete approved use case + interface/validation plan |

## Important non-merger rule

A row in this registry is **not** permission to publish its private payload or merge its historical branch. The registry is the public pointer; the artifact moves to public Git only when provenance, licensing, security/privacy, IP, claims, and current-main regression gates permit it.

## Immediate closure sequence

1. Merge only exact-head-green PRs.
2. Keep #512 exact custody bytes immutable; create a separately identified CI-clean projection.
3. Keep #513 draft until current-main overlap resolution and scientific D5/medium-fine gates.
4. Promote #514 only after the full exact-head gate set completes green.
5. Use Issue #518 for BAROS/QPHONON/WS-QX/ATIP/WS-SDA exact-object closure.
6. Preserve QSB/ECDSA.fail as `OFFICIAL RESULT PENDING` until official challenge evaluation/submission succeeds.
7. Keep defense/space solicitations gated by their institutional/compliance requirements; restored GitHub is necessary for some workflows but never substitutes for eligibility/CUI/export-control requirements.
