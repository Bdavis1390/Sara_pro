# Worldshepherd — DON26BX05-NP004 Phase I Capture & Evidence Gate

**Date:** 2026-09-14  
**Status:** GO-CONTINGENT / DRAFT / CLAIMS-CONTROLLED  
**Topic:** DON26BX05-NP004 — NAVWAR Open Topic for Unified Assured Positioning, Navigation, and Timing Operational Awareness and Decision Support  
**Submission deadline:** 2026-09-23 12:00 PM ET  
**Primary public source:** https://navysbir.com/n26_5/DON26BX05-NP004.htm

## 1. Executive decision

Worldshepherd has a materially stronger fit to NP004 than a generic defense-software positioning statement would suggest. The repository already contains a bounded APNT software lane, explicit interface-contract custody, synthetic qualification, evidence graphs, replay, human acceptance controls, and a separate NP004 POC-A draft branch with an exact-head green CI matrix.

**Capture decision: GO-CONTINGENT.**

The opportunity is sufficiently aligned to justify proposal completion now, but submission readiness remains contingent on administrative eligibility/compliance confirmation and completion of a proposal-quality operator-facing demonstration plan. No claim of Navy validation, GPNTS integration, ASPN/pntOS interoperability, operational APNT performance, or measured operator improvement is authorized without supporting evidence.

## 2. Why this is unusually aligned

The NAVWAR topic explicitly seeks software—not new PNT sensors, timing sources, navigation algorithms, or hardware—to reduce fragmented operator interfaces and improve understanding of APNT status, confidence, threats, degradations, impacts, and recovery options. The public Q&A further states that Phase I may use synthetic data, should be API-first and modular, should run locally/air-gapped, may use rules-based analytics, should support a navigation-style operator display, and should preserve auditable decision history. The Government has also confirmed that commercially derived data-integration and decision-support platforms are responsive.

That means the proposal does not need to pretend Worldshepherd is a navigation engine. The strongest thesis is narrower and more credible:

> **Worldshepherd is a local, modular APNT operator-awareness and decision-trace layer that normalizes heterogeneous source state, correlates bounded evidence, presents explainable informational recovery candidates, records operator evaluation, and preserves replayable provenance without commanding the underlying platform.**

This boundary matches the public Phase I instruction that the capability remain an informational decision aid rather than an action-routing or platform-command system.

## 3. Existing repository evidence

### 3.1 Main-branch primitives

| Navy need / design target | Existing Worldshepherd evidence | Current claim state | Gap before proposal use |
|---|---|---|---|
| Normalize heterogeneous APNT source state | `worldshepherd_sara/apnt_adapter.py` provides a normalized PNT source model and synthetic adapter | IMPLEMENTED IN SOFTWARE | Map representative synthetic fields to a documented ASPN/pntOS-conformant fixture; do not claim live interoperability |
| Authoritative interface custody | `worldshepherd_sara/apnt_interface_contract.py` fails closed until required fields are mapped and validation evidence is present | IMPLEMENTED IN SOFTWARE | Obtain authoritative interface definitions post-award / Phase II as applicable |
| APNT status / confidence / recovery awareness | `worldshepherd_sara/apnt.py` derives bounded awareness states and informational recovery options | IMPLEMENTED IN SOFTWARE / DEMONSTRATOR | Expand beyond simple rule set only if proposal value exceeds added validation burden |
| Synthetic qualification evidence | `worldshepherd_sara/apnt_qualification.py` compiles replayable evidence and marks physical validity NOT_EVALUATED | PROVEN INTERNALLY FOR SOFTWARE-SYNTHETIC SCOPE ONLY | Keep physical/operational claims blocked |
| Evidence graph / provenance | APNT snapshot graph + qualification evidence graph | IMPLEMENTED IN SOFTWARE | Tie every UI recommendation to drill-down evidence references |
| Human authority boundary | `hmaa_human_acceptance.py` requires explicit human acceptance and prevents acceptance from becoming operational-validation evidence | IMPLEMENTED IN SOFTWARE | For NP004 Phase I, present this as audit/governance architecture, not action authorization |
| Signed bounded authorization primitive | `prime_sentinel_authorization.py` verifies short-lived Ed25519 assertions for a narrow requalification-release action | IMPLEMENTED IN SOFTWARE | **Do not repurpose as APNT platform command in Phase I** |
| Historical replay | `mission_replay.py` orders events, derives findings, and creates evidence relationships | IMPLEMENTED IN SOFTWARE | Integrate the NP004-specific trace into operator debrief UX |
| Adversarial gap custody | `test_apnt_nist_adversarial_gap_suite.py` intentionally records current blind spots rather than hiding them | PROVEN INTERNALLY FOR TESTED NEGATIVE-EVIDENCE SCOPE | Use as credibility evidence; never claim spoofing/jamming classification from this test |

### 3.2 NP004 POC-A draft branch / PR #187

PR #187 (`worldshepherd/np004-apnt-poc-a-v0-1-20260912`) currently implements a synthetic informational operator-awareness/replay harness. Its exact recorded head is `178f3da3a3ccd7ca84ac05825229c01a10cec778`.

At that head, the repository reports successful completion of the dedicated NP004 gate plus the required build/test, verified-local, commit-closure, TLS private-backend, operational-resilience, rollback, restore, and NIST 800-171 precursor workflows.

The POC-A custody boundary is strong and should be preserved:

- synthetic-only six-state awareness/replay scenario;
- hash-linked source -> alert -> recommendation -> operator-response trace;
- immutable recommendation identity binding;
- APPROVE / REJECT / DEFER treated as evaluation records only;
- `execution_attempted=false` hard boundary;
- no action-routing or platform-command stage;
- deterministic replay digest;
- non-finite numerical inputs rejected;
- explicit exclusion of pntOS/ASPN/GPNTS integration, latency compliance, operator-performance improvement, and government validation claims.

PR #187 remains draft and blocked from merge pending independent review and explicit CRE1AWS incorporation authority. Proposal material may cite the existence of this prototype only within its exact evidence boundary.

## 4. Government requirement-to-evidence crosswalk

| Public NP004 requirement / Q&A position | Worldshepherd response | Readiness | Proposal language |
|---|---|---:|---|
| Improve operator understanding of APNT status, confidence, threats and recovery options | Existing APNT normalized source state + bounded awareness + informational recommendations | HIGH for synthetic feasibility | “Demonstrate a unified operator-awareness workflow over representative synthetic APNT source states.” |
| Do not develop new PNT sensor/navigation hardware/algorithms | Worldshepherd is software integration/awareness/provenance | HIGH | Explicitly exclude PNT estimator/sensor claims |
| Commercially derived decision-support platform is responsive | SARA/Worldshepherd is an existing software platform being adapted | HIGH | Lead with adaptation, not greenfield invention |
| Phase I synthetic data acceptable | Existing synthetic fixtures and qualification harness | HIGH | Use synthetic ASPN/pntOS-conformant representative data as the feasibility basis |
| API-first, modular, platform-independent architecture | Existing modular Python services, adapters, contracts and container-oriented deployment lane | MEDIUM-HIGH | Demonstrate loose coupling and contract-gated adapters |
| 3–8 PNT sources at 1–10 Hz design assumption | Current POC-A is scenario/replay oriented | MEDIUM/UNMEASURED | Treat as a **design/performance test target**, not achieved performance |
| Sub-second initial alert / initial recommendation chain | No current measured NP004 end-to-end latency evidence identified in this gate | GAP | Add benchmark harness and report p50/p95/p99; do not claim before measurement |
| Progressive disclosure: immediate alert, deeper evidence later | Evidence references and replay architecture are already suitable | MEDIUM-HIGH | Make this the UX organizing principle |
| Navigation/ECDIS-like familiarity | No current NP004-specific ECDIS-style UI evidence identified | GAP | Build low/medium fidelity navigation-style single-pane prototype; avoid claiming ECDIS standards compliance |
| Explainable recommendation / evidence support | Hash-linked evidence trace and rationale are present | HIGH for synthetic scope | Show click-through from alert -> source -> rationale -> operator record |
| Auditable history linking condition, evidence, recommendation, operator decision and outcome | POC-A directly targets this | HIGH for synthetic scope | Make decision trace a primary differentiator |
| Local/air-gapped execution | Verified-local/container architecture exists; proposal must demonstrate NP004 packaging | MEDIUM-HIGH | Commit to fully local runtime; document zero external dependency during demonstration |
| Containerized proof of concept encouraged | Repository already has containerized verified-local lane | HIGH architecture / DEMO TO VERIFY | Run NP004 demo in isolated container and preserve build/runtime evidence |
| Human/operator effectiveness metrics matter | Current software tests do not establish human-performance gains | GAP | Define surrogate-user evaluation protocol without making pre-award improvement claims |
| Phase I should remain informational decision aid | POC-A explicitly blocks execution | HIGH | Preserve non-actuation boundary as a design control |

## 5. The productization breakthrough: Worldshepherd Mission Assurance Fabric

NP004 should not be framed as a one-off dashboard. It can be the anchor demonstration for a reusable product category:

**Worldshepherd Mission Assurance Fabric (WMAF)** — a non-actuating, evidence-preserving decision-support layer for heterogeneous operational systems.

The reusable kernel is:

`Source adapters -> normalized state -> bounded correlation -> operator alert -> evidence-linked recommendation -> human evaluation record -> immutable audit/replay`

For NP004 the domain adapter is APNT. In future non-NP004 domains, the same assurance kernel can surround sensing, autonomy, maintenance, logistics, or defensive systems while domain-specific hardware remains outside the Worldshepherd trust boundary.

This is also the correct relationship to companies such as Sentradel: their counter-UAS hardware can remain a separate physical system, while a future Worldshepherd integration—if mutually validated—could consume permitted status/events for provenance, assurance, and operator decision support. **No weapon actuation interface is part of this NP004 architecture or claim.**

## 6. Non-actuation boundary — mandatory

For the NP004 Phase I proposal and prototype:

1. Worldshepherd may ingest representative APNT source/status information.
2. Worldshepherd may correlate/display status and confidence.
3. Worldshepherd may generate informational alerts and recovery candidates.
4. Worldshepherd may record an operator's evaluation of those candidates.
5. Worldshepherd may preserve evidence, provenance, replay, and audit history.
6. Worldshepherd **must not command the navigation platform, select a live source, transition INS modes, route an operational action, or issue any kinetic/non-kinetic actuation command.**

This is both a claims-control boundary and a direct response to NAVWAR's Phase I Q&A.

## 7. Nine-day capture critical path

### Gate A — eligibility and submission compliance (highest priority)

Confirm, from the current Release 5 CSO instructions and DSIP account, before final proposal assembly:

- proposing entity is SBIR-eligible at submission/award as required;
- all DSIP registrations and entity identifiers are active;
- current Volume 1–7 requirements;
- exact Release 5 technical-volume template and page limit;
- exact Base/Option cost ceilings and periods of performance;
- minimum SBC workshare requirement;
- CMMC Level 2 (Self) / NIST 800-171 / SPRS posture required at award;
- foreign-risk and ownership disclosures;
- mandatory certifications/supporting documents.

**No proposal should be marked submission-ready until this administrative gate is verified against the current Release 5 instructions in DSIP.**

### Gate B — proposal-quality technical evidence

Required before claiming a strong Phase I feasibility package:

- preserve PR #187 exact-head evidence and independent-review status;
- add an NP004 performance benchmark for synthetic 3–8 source, 1–10 Hz loads;
- measure alert-path latency and report distributions; no invented latency number;
- add an ASPN/pntOS-conformant synthetic input fixture using only public/authoritative specifications;
- package the demo as a fully local/containerized execution path;
- add an operator-facing navigation-style single-pane prototype using progressive disclosure;
- demonstrate replay from condition -> evidence -> informational recommendation -> operator evaluation;
- produce screenshots/video only after the exact build is pinned and evidence digest recorded.

### Gate C — human-factors feasibility

Phase I proposal should commit to measurable surrogate-user evaluation rather than claiming current operator gains. Candidate metrics:

- time to identify degraded/source-disagreement state;
- correct comprehension of source confidence/integrity;
- correct selection/evaluation of the informational recovery candidate in synthetic scenarios;
- time to open supporting rationale/evidence;
- workload/usability measure appropriate to non-human-research demonstration constraints and Government guidance.

Any actual human-subject activity must follow the solicitation/Q&A boundary; the public Q&A states the Government does not expect human research under this SBIR.

## 8. Technical narrative spine

A competitive ten-page-class technical narrative should revolve around five proof points rather than a broad Worldshepherd catalog:

**Problem:** fragmented APNT displays increase cognitive burden and slow contested-PNT triage.

**Novel adaptation:** Worldshepherd converts heterogeneous APNT source state into a unified, evidence-linked operator picture without replacing the underlying PNT systems.

**Trust mechanism:** every alert/recommendation is traceable to source state and replayable; uncertainty and known blind spots remain visible.

**Deployment mechanism:** local, modular, API-first, container-oriented architecture designed for isolated shipboard operation and later GPNTS/ASPN/pntOS mapping.

**Phase I proof:** one deep synthetic shipboard scenario, measurable latency/usability objectives, containerized local demonstration, and a claims-controlled evidence package that supports Phase II interface integration.

## 9. Disqualifying overclaims

Do not write or imply any of the following unless new evidence is created and independently reviewed:

- “ASPN compatible” or “pntOS compatible” based only on internal normalized fields;
- “GPNTS integrated”;
- “detects spoofing” or “detects jamming” from the existing bounded rule set;
- “sub-second” without a pinned benchmark;
- “improves operator decision speed/accuracy” without measured surrogate-user evidence;
- “operationally validated,” “Navy validated,” “combat proven,” or “TRL 6”;
- any platform control, live PNT source selection, navigation-mode transition, or autonomous action capability.

Use the existing claims lexicon: **IMPLEMENTED IN SOFTWARE**, **PROVEN INTERNALLY** only for the exact tested software scope, **SIMULATED ONLY**, **REQUIRES PARTNER VALIDATION**, and **REQUIRES LAB VALIDATION** as appropriate.

## 10. Current capture score

| Dimension | Score | Rationale |
|---|---:|---|
| Technical fit | 19/20 | Topic explicitly requests the type of data-integration/decision-support architecture Worldshepherd is building |
| Existing evidence maturity | 13/15 | Strong software + exact-head POC evidence; no Navy/physical/live-interface validation |
| Eligibility/compliance confidence | 7/15 | CMMC and administrative submission readiness must be verified, not assumed |
| Team/prime probability | 8/10 | Software-heavy Phase I can plausibly be primed without a hardware partner if entity eligibility is satisfied |
| Gap-to-demo | 8/10 | Core trace exists; UI, synthetic-standard mapping, and benchmark evidence are the main technical gaps |
| Award value | 9/10 | Strong strategic value for a funded software adaptation lane; exact current funding must be confirmed from Release 5 CSO instructions |
| Strategic value | 10/10 | Establishes a reusable evidence-preserving mission-assurance product category |
| Follow-on potential | 5/5 | Direct GPNTS transition owner and Phase II interface path are explicit in public topic material |
| Deadline feasibility | 4/5 | Nine days is tight but feasible if scope remains disciplined and existing evidence is reused |
| **Total** | **83/100** | **GO-CONTINGENT** |

This score is an internal capture heuristic, not a probability of award.

## 11. Immediate next gate

The most important next technical action is **not more breadth**. It is to close three measurable NP004 gaps:

1. benchmark the exact synthetic alert path under the Government's stated 3–8 source / 1–10 Hz design envelope;
2. produce a navigation-style progressive-disclosure UI that consumes the same immutable trace;
3. build a proposal evidence appendix mapping every technical assertion to commit, test, workflow run, fixture, screenshot, or explicit `NOT_YET_EVIDENCED` state.

If those three are completed without weakening the claims boundary, Worldshepherd moves from “interesting architecture” to a credible, inspectable Phase I feasibility package.
