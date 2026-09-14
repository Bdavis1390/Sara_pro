# DON26BX05-NP004 — Worldshepherd Phase I Technical Volume Skeleton

**Working document — not submission-ready**  
**Date:** 2026-09-14  
**Claims state:** DRAFT / SIMULATED_ONLY where performance evidence is synthetic  
**Deadline:** 2026-09-23 12:00 PM ET  
**Instruction gate:** Validate all formatting, mandatory sections, Base/Option structure, and cost assumptions against the current DON Release 5 CSO instructions and DSIP template before submission.

## Proposal thesis

Worldshepherd will adapt its existing local, evidence-preserving decision-support software into a unified APNT operator-awareness prototype that ingests representative heterogeneous APNT source state, presents status/confidence/degradation information in a navigation-style single-pane workflow, provides explainable informational recovery candidates, and preserves a deterministic audit/replay trace. The Phase I system will remain an informational decision aid and will not command GPNTS, switch live PNT sources, alter navigation modes, or execute recovery actions.

## Recommended page architecture

Use the current official DON template if it prescribes a different order. This page allocation is a drafting aid only.

| Draft section | Approx. pages | Purpose |
|---|---:|---|
| 1. Problem / Navy operational need | 0.75 | Demonstrate precise understanding of fragmented APNT operator workload |
| 2. Proposed innovation | 1.25 | Explain the Worldshepherd adaptation and why it differs from another dashboard |
| 3. Technical approach / architecture | 2.00 | API-first modular pipeline, normalized state, evidence trace, local deployment |
| 4. Phase I use case and demonstration | 1.50 | One deep destroyer-transit-style synthetic scenario |
| 5. Metrics / verification / claims control | 1.25 | Latency, trace completeness, usability feasibility, negative evidence |
| 6. Work plan — Base | 1.00 | Tasks, milestones, deliverables |
| 7. Option / Phase II bridge | 0.75 | Interface mapping and transition preparation |
| 8. Team / facilities / commercialization-transition | 1.00 | Execution credibility and dual-use path |
| 9. Risk / cybersecurity / data rights | 0.50 | Air-gap, supply chain, CMMC gate, interface uncertainty |
| **Total drafting target** | **10.00** | Confirm exact current limit before finalization |

---

## 1. Problem / Navy operational need

### Draft core language

NAVWAR's NP004 challenge is not a shortage of PNT sensors. It is an operator-integration problem: multiple APNT and related systems expose fragmented health, confidence, integrity, threat, and recovery information through separate interfaces. In contested or degraded environments, the operator must establish what changed, which sources remain trustworthy, what the operational consequence may be, and which recovery path warrants consideration—while maintaining situational awareness.

Worldshepherd addresses this fragmentation at the software decision-support layer. It does not replace the underlying PNT systems. Instead, it creates a common evidence model that links source state to operator-facing alerts, explanatory rationale, informational recovery candidates, and replayable decision history.

### Evidence to insert

- Official NP004 objective and description.
- Public Q&A statements on anomaly triage, fallback awareness, local execution, auditable decision history, progressive disclosure, and synthetic Phase I data.
- One architecture figure: fragmented APNT inputs -> Worldshepherd -> navigation-style operator picture.

### Claims guardrail

Do not state that Worldshepherd presently detects jamming or spoofing. Phrase the objective as supporting **operator anomaly triage using representative indicators and bounded correlation**, with any independent classification method treated as future work unless separately demonstrated.

---

## 2. Proposed innovation

### Working name

**Worldshepherd APNT Mission Assurance Fabric (APNT-MAF)**

### Innovation statement

The proposed innovation is the combination of a normalized APNT source model, explicit interface-contract custody, evidence-linked decision support, progressive-disclosure operator UX, deterministic audit/replay, and a hard informational-only execution boundary in a local modular runtime.

The technical differentiator is not a novel navigation estimator. It is **decision provenance**: the operator can move from an alert to the exact supporting source state, rationale, recommendation identity, and recorded evaluation, then reproduce the event sequence after the scenario.

### Four differentiators

1. **Evidence-linked awareness** — alerts and recommendations carry source references rather than existing as opaque UI outputs.
2. **Fail-closed interface custody** — an external data mapping cannot be represented as validated until its authoritative contract fields and evidence are present.
3. **Deterministic replay** — a scenario can be reconstructed from ordered events and hash-linked decision-trace records.
4. **Claims-controlled autonomy boundary** — Phase I recommendations are informational only; no platform command or live recovery execution is implemented.

---

## 3. Technical approach / architecture

### 3.1 Logical flow

```text
Representative APNT sources
        |
        v
Contract-gated source adapters
        |
        v
Normalized APNT source state
        |
        v
Bounded correlation / awareness evaluator
        |
        +------------------+
        |                  |
        v                  v
Immediate operator alert   Evidence graph / rationale
        |                  |
        +---------+--------+
                  v
      Informational recovery candidate
                  |
                  v
       Operator evaluation record
                  |
                  v
       Hash-linked audit / replay
```

### 3.2 Source-adapter layer

Use the existing `NormalizedPntSource` contract as the internal boundary. For Phase I, ingest representative synthetic data conforming to publicly available ASPN/pntOS structures to the extent authoritative public specifications permit. If a field or message mapping is not supported by an authoritative source, label it representative and synthetic rather than claiming interoperability.

### 3.3 Awareness / correlation layer

The initial feasibility implementation may use deterministic, explainable rules. Inputs should include source identity, health/integrity indicators, confidence, timestamp/freshness, and provenance where available. The evaluator produces an awareness state and operator-facing rationale.

The proposal may describe a path to statistical/ML methods, but explainability and local edge execution remain requirements. Do not add ML merely to sound advanced.

### 3.4 Progressive-disclosure UX

The initial alert path should expose only the minimum information required for rapid comprehension: affected source/state, severity, confidence/integrity cue, and informational recovery candidate. Supporting evidence and rationale appear on operator drill-down. This architecture directly separates fast alerting from deeper evidence-package generation.

### 3.5 Audit/replay

Record, at minimum:

- source observation/event identity;
- derived alert identity;
- supporting evidence references;
- informational recommendation identity;
- operator evaluation (approve/reject/defer as a recorded assessment, not action authority);
- timestamps and ordering;
- trace hash/digest;
- final scenario state.

### 3.6 Non-actuation boundary

No Phase I module may issue a command to GPNTS, a navigation system, a source-selection controller, an INS mode, or another operational platform. A user interaction indicating APPROVE/REJECT/DEFER records the operator's assessment of the informational recommendation only.

---

## 4. Phase I use case and demonstration

### Representative scenario

A shipboard navigation team transits a constrained strait while multiple representative PNT sources update. The scenario evolves from nominal operation to degradation/disagreement, operator triage, informational recovery evaluation, recovery monitoring, and restoration.

### Minimum source set

Design the benchmark and demo to support the Government's published architectural assumption of **3–8 simultaneous PNT sources updating at 1–10 Hz**. The exact semantic content should remain representative/synthetic unless authoritative interface definitions are available.

### Demonstration sequence

1. Start local/air-gapped containerized runtime.
2. Load pinned synthetic scenario and configuration digest.
3. Display nominal multi-source status.
4. Introduce a synthetic degradation/disagreement event.
5. Measure ingest-to-initial-alert latency.
6. Show initial alert and informational recovery candidate.
7. Drill into source/evidence/rationale.
8. Record operator evaluation without executing an action.
9. Continue through recovery/restoration.
10. Replay the trace and verify deterministic digest / event linkage.

### Required evidence artifacts

- exact Git commit;
- dependency/build manifest;
- fixture digest;
- configuration digest;
- container image/build evidence;
- benchmark output with p50/p95/p99 latency;
- trace-completeness result;
- screenshots or demo capture tied to the exact build;
- known-limitations/negative-evidence register.

---

## 5. Metrics / verification / claims control

### Software feasibility metrics

| Metric | Phase I measurement concept | Current evidence state |
|---|---|---|
| Source ingestion | 3–8 representative sources, 1–10 Hz | TARGET — benchmark required |
| Initial alert latency | ingest -> alert/recommendation presentation | TARGET — measurement required |
| Trace completeness | % scenario events linked through evidence/alert/recommendation/operator record where applicable | POC-A mechanism exists; proposal benchmark required |
| Deterministic replay | repeated identical input produces identical replay digest | POC-A implemented/tested for synthetic scope |
| Fail-closed malformed input | invalid/non-finite/contract-invalid input rejected | Existing test evidence in POC-A/interface contract |
| Air-gapped runtime | demonstration completes with no external service dependency | TARGET — exact demo evidence required |
| Operator comprehension | surrogate task accuracy/time | PLANNED — no current improvement claim |

### Claims-control table

| Claim | Allowed now? | Required evidence to promote |
|---|---|---|
| Existing synthetic APNT awareness/replay software | YES, exact tested scope only | Preserve exact commit/test evidence |
| ASPN/pntOS interoperability | NO | Authoritative mapping + conformance evidence |
| GPNTS integration | NO | Government interface + integration evidence |
| Sub-second alert performance | NO | Reproducible benchmark on pinned build/environment |
| Spoofing/jamming detection | NO | Validated classifier/detection evidence |
| Operator effectiveness improvement | NO | Defined surrogate evaluation + results |
| Navy validation | NO | Government acceptance/test evidence |

---

## 6. Phase I Base work plan — draft

**Task 1 — Requirements and evidence baseline.** Freeze claims boundary; map public NP004 requirements to measurable acceptance criteria; pin representative source schema and scenario.

**Task 2 — Synthetic APNT ingestion and normalization.** Implement/validate representative ASPN/pntOS-conformant synthetic adapters through the contract-gated normalization layer.

**Task 3 — Operator-awareness correlation.** Mature bounded explainable correlation, confidence presentation, alert generation, and informational recovery candidates.

**Task 4 — Navigation-style operator UX.** Implement a low/medium-fidelity single-pane workflow using progressive disclosure and operator-familiar navigation conventions without claiming ECDIS standards compliance.

**Task 5 — Local deployment and performance characterization.** Package the capability for isolated containerized execution; benchmark the 3–8 source / 1–10 Hz envelope and alert latency.

**Task 6 — Verification, replay, and Phase II transition plan.** Execute pinned scenarios, preserve evidence artifacts, document negative evidence/limitations, produce final report and initial Phase II plan.

### Milestones

- M1: requirements/evidence matrix frozen;
- M2: synthetic interface fixture accepted by internal conformance gate;
- M3: end-to-end local demo functional;
- M4: benchmark/evidence package complete;
- M5: surrogate operator evaluation feasibility results documented;
- M6: final report + Phase II interface/integration plan.

Exact Base period must match current Release 5 instructions.

---

## 7. Phase I Option / Phase II bridge — draft

The Option should reduce Phase II integration risk rather than add speculative features. Candidate work:

- harden adapter/plugin boundaries for authoritative GPNTS/ASPN/pntOS message mappings;
- refine HMI from surrogate feedback;
- prepare Platform One/Iron Bank-compatible containerization path;
- expand test vectors and fault/degradation taxonomy using Government-furnished information when available;
- mature cybersecurity artifacts and interface threat model;
- define representative-environment integration and verification plan;
- prepare Phase II prototype backlog, T&E matrix, transition plan, and data-rights strategy.

Do not describe Phase I Option work as if Government ICDs or live Fleet interfaces are already available.

---

## 8. Team / facilities / transition

### Prime role

Worldshepherd / proposing SBC: software architecture, data integration, decision trace, HMI, containerized local runtime, evidence/qualification harness, cybersecurity artifact generation.

### Partner rule

Do not add a hardware or APNT partner simply to make the team look larger. A partner is justified only if it closes an explicit eligibility, authoritative-interface, HMI/user-research, or transition gap.

### Sentradel relationship

Sentradel is **not required for NP004**. Treat it as a separate future mission-assurance adapter candidate in the broader Worldshepherd strategy, subject to mutual technical validation. Keep counter-UAS/kinetic functionality out of the NP004 proposal.

### Transition

The public topic identifies GPNTS as the transition owner. The Phase II story should therefore emphasize adapter/interface maturation, representative environment validation, HMI measurement, and integration with Government-provided message/interface definitions—not expansion into unrelated Worldshepherd modules.

---

## 9. Risks and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Public ASPN/pntOS mapping differs from Government integration details | Rework in Phase II | Contract-gated adapter boundary; normalized internal model |
| UI becomes feature-heavy and increases cognitive load | Weak HMI score | Progressive disclosure; one deep use case; surrogate task measurement |
| Latency target missed | Reduced feasibility | Measure early; profile ingest/alert path; keep evidence drill-down off critical alert path |
| Proposal overclaims maturity | Credibility loss | Assertion-to-evidence matrix; explicit `NOT_YET_EVIDENCED` state |
| CMMC/administrative gate incomplete | Award/submission risk | Treat compliance verification as capture Gate A, not paperwork afterthought |
| POC-A review remains incomplete | Cannot treat branch as incorporation-ready | Cite only exact tested evidence; keep PR blocked until independent review and authority approval |

---

## 10. The one-sentence close

**Worldshepherd gives the APNT operator a local, explainable, replayable operational picture in which every alert and informational recovery candidate can be traced to its supporting source evidence—without replacing the Navy's PNT systems or commanding them.**

## Submission-readiness checklist

- [ ] Current Release 5 CSO instructions verified in DSIP.
- [ ] Current technical-volume template applied.
- [ ] Entity/SBIR eligibility verified.
- [ ] SAM/UEI/CAGE/DSIP records verified as applicable.
- [ ] CMMC Level 2 (Self) award-time requirement closure plan verified.
- [ ] Base and Option exact periods/cost ceilings verified.
- [ ] Workshare calculation verified.
- [ ] Volumes 1–7 and mandatory attachments complete.
- [ ] Technical assertions mapped to evidence.
- [ ] No unsupported ASPN/pntOS/GPNTS compatibility claim.
- [ ] No unsupported latency or human-performance claim.
- [ ] POC-A draft status and review limitation disclosed internally.
- [ ] Final technical volume independently reviewed for compliance and technical credibility.
