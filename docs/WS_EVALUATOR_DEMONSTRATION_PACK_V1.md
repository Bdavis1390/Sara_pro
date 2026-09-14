# Worldshepherd Evaluator Demonstration Pack v1

Status: INTERNAL EVALUATION PACKAGE — NOT A GOVERNMENT ENDORSEMENT OR CERTIFICATION

## Selection thesis

Worldshepherd should be preferred **only when the mission places high value on evidence-governed decision support**: source-to-decision provenance, explicit confidence/uncertainty, human authorization, auditable/reversible decisions, modular integration, claims control, degraded-state behavior, and non-proprietary evidence outputs.

Worldshepherd should **not** be preferred today solely on the basis of deployment scale, classified accreditation history, 24x7 operational references, or fielded sensor-to-effector C2 history. Public evidence from established defense platforms shows those are incumbent strengths. Worldshepherd must earn selection through a narrower, measurable wedge rather than unsupported parity claims.

## Current reproducible evidence

### Selection-core baseline

Evidence workflow: `Worldshepherd Selection Baseline`

Green run: GitHub Actions run `34798178408` on commit `4eb7acac35349ab7071de1a566c1d94ce6878d78`.

Result: `BASELINE_PASS_WITH_UNRESOLVED_GATES`.

The evidence bundle records:
- 46 scoped selection-core test files executed;
- PRE qualification index generated;
- controlled operational-resilience drill passed;
- PUBLIC-ONLY security boundary present;
- preferred-choice evidence matrix present;
- selection-test manifest present;
- open-source license absent and explicitly unresolved.

The controlled outage/recovery drill recorded recovery in 2.0 seconds on that CI environment while verifying restored readiness, retained state, and exact build identity. This is internal CI evidence only, not an operational RTO/SLA claim.

### Retained negative evidence

The nonlinear MHD G10 research suite remains open negative evidence. In the 2026-09-13 baseline, ideal cross-helicity relative drift was approximately `3.6710178210651096e-05`, above the frozen `2e-05` acceptance limit. The limit is not relaxed. The research status remains `SIMULATED_ONLY` and is tracked independently from the procurement-selection core.

### Bounded synthetic scale benchmark

Evidence workflow: `Worldshepherd Scale Benchmark`

Green run: GitHub Actions run `34798335924` on commit `f8d51e88af6cd82e9c649ad4095e89cb5ded4340`.

CI host recorded by the benchmark:
- AMD EPYC 9V74 80-Core Processor;
- 4 logical CPUs exposed to the runner;
- Python 3.11.16;
- Linux Azure runner.

Measured deterministic in-process synthetic 2-D fusion results:

| Observations | Serialized input | p95 latency | Synthetic function throughput at p95 |
|---:|---:|---:|---:|
| 500 | 0.055 MB | 1.651 ms | ~2,002 MB/min |
| 2,500 | 0.275 MB | 8.562 ms | ~1,930 MB/min |
| 10,000 | 1.102 MB | 36.970 ms | ~1,788 MB/min |

These numbers are **not** end-to-end ISR performance. The benchmark excludes network transport, request parsing, authentication, persistence, historical retrieval, imagery/video/radar decoding, model inference, classified-domain controls, cross-domain transfer, and operator UI. It does not generate a 5 GB/min burst. It is evidence that the deterministic synthetic fusion primitive is measurable and fast enough to justify deeper integration testing—not proof of DIU PROJ00716 compliance.

## Government requirement alignment

Canonical machine-readable crosswalk: `config/worldshepherd_requirements_to_evidence_crosswalk_v0_1.json`.

Key public source references:
- Army Agentic AI Decision Management: https://armysbir.army.mil/topics/agentic-ai-schema-driven-decision-management/
- NAVWAR APNT DON26BX05-NP004: https://www.navysbir.com/n26_5/DON26BX05-NP004.htm
- DIU Space Threat Intelligence Synthesis Engine PROJ00716: https://www.diu.mil/work-with-us/submit-solution/PROJ00716
- DARPA IPTO: https://www.darpa.mil/about/offices/ipto

Recurring evaluator signals are:
1. auditable decision packages and traceability;
2. transparent reasoning, confidence, and provenance;
3. human control;
4. containerized/modular/open integration;
5. degraded-state resilience and replay;
6. measurable performance;
7. controlled-environment cybersecurity;
8. sustainment and transition.

## Integrated evaluator demonstration

Executable: `tools/selection_demo/run_evaluator_demo.py`

CI workflow: `.github/workflows/worldshepherd-evaluator-demo.yml`

The scenario uses only repository synthetic fixtures and must demonstrate in one repeatable run:
1. synthetic observation fusion with complete source lineage;
2. mission replay from source event to finding to proposed follow-on action;
3. policy evaluation that keeps high-authority actions behind human review;
4. an explicitly denied action failing closed;
5. identified-human approval, denial, and revocation states;
6. a DDIL equal-clock/equal-authority divergence surfaced as an unresolved conflict rather than silently overwritten;
7. deterministic closure of that conflict only after a newer/higher-authority human resolution;
8. evidence references for every top-level demonstration claim;
9. a semantic digest that matches across repeated scenario execution.

A green result is internal reproducible synthetic evidence. It is not operational validation or government acceptance.

## When an evaluator should choose Worldshepherd

Worldshepherd has its strongest selection case when the requirement prioritizes all or most of the following:
- the decision itself must be reconstructable and auditable;
- source provenance must survive fusion and downstream decisions;
- uncertainty/confidence must remain explicit;
- AI output cannot silently become execution authority;
- human approval/denial/revocation must be first-class state;
- contradictory or partitioned state must surface visibly rather than be silently discarded;
- modules/adapters must remain replaceable;
- evidence should export in non-proprietary machine-readable form;
- claims must remain bounded to actual validation evidence;
- degraded-state behavior and recovery must be tested explicitly;
- the buyer wants a focused governance/evidence layer that can complement larger incumbent C2/data platforms rather than require wholesale replacement.

## When an evaluator should not choose Worldshepherd yet

Worldshepherd should not be represented as the preferred direct prime where the decisive gate is currently:
- an already-authorized CUI/classified production enclave;
- current CMMC/SPRS evidence that has not been independently established;
- an existing FCL/PCL or TS/SCI staffing path;
- production operation at division/global sensor-to-effector scale;
- validated multi-INT operational performance;
- 24x7 mission support with customer references;
- proven multi-year operational data retention/retrieval at the requested scale;
- a commercial open-source license where that license decision has not been completed;
- flight, weapon, sensor, materials, propulsion, or other physical-system validation not evidenced by the software repo.

In those cases, the correct route is PARTNER/PREPARE until the gate closes.

## Competitive reality

Public incumbent evidence establishes a high bar:
- Palantir AIP for Defense advertises deployment on defense networks, including classified systems and tactical-edge environments.
- Scale Donovan advertises FedRAMP High / IL4, classified and air-gapped deployments, mission-tailored agents, and traceability.
- Anduril Lattice has public production and division-scale C2/data-mesh deployments across large tactical-edge footprints.

Worldshepherd therefore does not claim to beat incumbents on deployment history. Its proposed differentiation is a composable **evidence-and-authorization fabric** that makes claims, decisions, uncertainty, provenance, human authority, degraded-state reconciliation, and qualification evidence explicit and independently reviewable.

## Remaining preferred-choice gates

1. **End-to-end scale:** move from function microbenchmark to application/API + persistence + historical retrieval + representative multimodal pipeline testing.
2. **Controlled environment:** establish the actual contract-specific authorized boundary and required CMMC/NIST/SPRS/clearance evidence.
3. **Licensing:** perform IP/dependency review and make a deliberate licensing/business decision where open source is required.
4. **External validation:** obtain at least one independent evaluator, pilot, or partner reproduction of the evidence package.

Until these gates close, the correct claim is:

> **Worldshepherd has an internally proven, differentiated evidence-governance wedge. It is not yet universally preferred-choice ready.**
