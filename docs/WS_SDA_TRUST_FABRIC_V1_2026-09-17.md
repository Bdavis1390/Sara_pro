# Worldshepherd SDA Trust Fabric V1

Status: **IMPLEMENTED IN SOFTWARE — G1 candidate; internal CI required**
Date: 2026-09-17
Program: Worldshepherd
Primary runtime: SARA / PRIME SENTINEL / ECHO SENTINEL LINK / OVERWATCH
Repository: `Bdavis1390/Sara_pro`

## 1. Mission

WS-SDA V1 turns the existing Worldshepherd evidence-governance stack into a bounded,
unclassified Space Domain Awareness integration baseline.

The system is designed around one invariant:

> No operational conclusion outruns the identity, provenance, uncertainty, policy,
> authorization, and evidence that support it.

V1 is **not** an operational orbit-determination service, a UDL integration, a
classified-network capability, or a government-approved SDA product. It is a
software integration and qualification baseline from which those external gates can
be pursued honestly.

## 2. Cross-project convergence

This implementation deliberately reuses the strongest applicable work across the
Worldshepherd portfolio rather than creating a parallel space-only stack.

| Worldshepherd lane | Reused in WS-SDA | Boundary |
|---|---|---|
| SARA | canonical registry/audit patterns, fail-closed workflow execution, recovery discipline | orchestration only; does not create sensor truth |
| PRIME SENTINEL | explicit authority, policy-bound action, short-lived signed authorization pattern, configuration custody | no autonomous operational effects |
| ECHO SENTINEL LINK | stable event identity, semantic digests, replay/dedup conflict detection, checkpoint/anchor lineage | local/internal evidence is not independent witnessing |
| OVERWATCH | target presentation layer for source health, conflict, uncertainty, lineage and degraded state | visualization does not upgrade evidence |
| APNT | authoritative interface-contract pattern, source normalization, adversarial input discipline | no ASPN/pntOS/GPNTS or SDA partner acceptance is implied |
| CISNET | contested-link policy, trusted-link selection, survivability and provenance concepts | simulation baseline; not operational BPSec assurance |
| DDIL | deterministic rejoin/reconciliation and visible equal-authority conflicts | not a safety-certified consensus protocol |
| Mission Replay | deterministic event ordering, debrief evidence graph, human-authority follow-on proposals | post-event reasoning remains evidence bounded |
| HMAA | human acceptance, external-response and partner-boundary patterns | no external partner validation is inherited |
| PRE / Capture Engine | requirement-delta, readiness, opportunity and evidence-target framing | prediction does not upgrade maturity |
| Software provenance / SBOM / attestation | component/build provenance and external-verifier state model | no SLSA/FIPS/CMMC status is implied |
| OPA policy envelope | PDP/PEP separation, action digest, escalation to human approval | design guidance until bound to an SDA PEP |
| OpenTelemetry work | future common audit/trace semantic mapping | telemetry is observability, not authorization |
| QCRYPTO | custody, crypto-agility and transition-planning discipline | no post-quantum protection claimed until implemented and validated |
| restriction-provenance 10x work | measurable residual-risk baselines, signed evidence/witness methodology | bounded software metric only |
| QPHONON 10+10 work | independent security/reliability-control methodology | physical QPHONON claims are not imported |
| Golden Dome / W-RMABM | synthetic distributed-sensing benchmark and partner-gap patterns | no weapon or operational tracking claim is imported |
| BR3D / digital-twin work | future evidence-linked visualization, replay and residual views | graphics never substitute for source evidence |
| physics/materials/BAROS validation | uncertainty, calibration, hazard and simulation-to-test discipline | physical/clinical results remain separate and validation-gated |
| Stegriage | artifact provenance and metadata-triage discipline | never treated as attribution or hidden-message proof by itself |
| SPACEGHOST / space research | mission-context and space-domain scenario framing | speculative/flight claims remain quarantined |
| Revenue/capture program | packaging, evidence-to-execution and partner-readiness process | commercial readiness is not technical validation |

Personal credential, wallet, recovery, seed, private-key, customer-secret, CUI,
classified, export-controlled, and unrelated personal materials are explicitly
excluded from WS-SDA ingestion and development.

## 3. G1 — Provenance-bound canonical observation

Implemented in `worldshepherd_sara/sda.py`.

A canonical observation contains separate representations for:

- source identity and source class;
- adapter identity and version;
- interface-contract identity and digest;
- source event identity and monotonic source sequence;
- observed/received time and clock uncertainty;
- reference frame;
- 3-D position and velocity;
- 6x6 covariance;
- measurement confidence;
- source reliability;
- handling/releasability tags;
- raw-source digest;
- transformation lineage;
- optional external source-signature reference.

### Critical semantic separation

WS-SDA does not collapse these into a single confidence number:

```text
measurement uncertainty
!= measurement confidence
!= source reliability
!= source authenticity
!= provenance integrity
!= release authorization
```

This prevents a cryptographically authentic but physically bad measurement from
being treated as trustworthy merely because its transport identity is valid.

## 4. Source-isolation state machine

```text
external/synthetic source
        |
        v
strict schema
        |
        v
contract identity + digest
        |
        v
adapter/source binding
        |
        v
sequence/replay gate
        |
        v
time/frame/releasability checks
        |
        +---- REJECT ------> invalid identity/contract/replay
        |
        +---- QUARANTINE --> structurally valid; policy/quality violation
        |
        +---- DUPLICATE ---> exact idempotent replay
        |
        +---- ACCEPT ------> ECHO-compatible audit/evidence
```

A stable source event that reappears with changed semantic content is not silently
accepted. The canonical stable event ID remains constant while its semantic digest
changes, allowing ECHO to record a conflict.

## 5. Fusion baseline

G1 includes a deliberately narrow deterministic reference fusion:

- same reference frame;
- same observation epoch;
- six state components;
- diagonal inverse-variance weighting;
- explicit pairwise normalized residual conflicts;
- complete observation-to-hypothesis evidence graph.

Measurement confidence and source reliability are **not** used as numerical fusion
weights. They remain independent quality/governance signals.

This is intentionally not JPDA, MHT, orbit determination, maneuver detection,
conjunction assessment, or an operational tracker.

## 6. Security and reliability gates

The target remains **10x**, but only where a measurable non-zero baseline exists.

### 6.1 Ratio metrics

For a frozen benchmark, G9 may claim a 10x improvement only when:

```text
candidate_metric <= 0.10 * frozen_baseline_metric
```

Candidate ratio metrics include:

- p95 source-to-canonical latency;
- median source-adapter engineering effort;
- operator interventions per fixed observation count;
- recovery time after injected store corruption;
- evidence-chain reconstruction time.

### 6.2 Zero-tolerance invariants

Already-closed attack channels are not described as "10x more zero." They become
non-regression invariants:

- untraceable accepted observation: 0;
- stale interface-contract digest accepted: 0;
- mutated same-sequence replay accepted: 0;
- backwards source sequence accepted: 0;
- source identity substitution accepted: 0;
- unknown schema field accepted: 0;
- non-finite state value accepted: 0;
- malformed/asymmetric covariance accepted: 0;
- policy-exceeding releasability silently accepted: 0;
- evidence conflict silently discarded: 0.

## 7. G1 executable acceptance criteria

The dedicated SDA CI gate must prove at minimum:

1. strict unknown-field rejection;
2. covariance shape/symmetry/finite-value enforcement;
3. enabled contracts require validation evidence;
4. canonical semantic mutation changes the semantic digest;
5. valid observations advance replay state;
6. exact replay is idempotent;
7. mutated same-sequence replay fails closed;
8. backwards sequences fail closed;
9. source spoofing and stale contract digests fail closed;
10. stale/future/frame/releasability/clock violations quarantine;
11. ECHO deduplicates exact events and detects semantic conflict;
12. deterministic inverse-variance fusion preserves lineage;
13. governance confidence/reliability values cannot silently alter the physical fusion weight;
14. contradictory measurements create explicit conflict evidence.

## 8. G2-G10 completion roadmap

| Gate | Objective | Exit evidence |
|---|---|---|
| G1 | canonical observation + source isolation + bounded fusion | unit/integration CI and ECHO conflict tests |
| G2 | workload identity | per-service identity, short-lived credentials, mTLS, revocation, no ambient shared bearer authority on SDA path |
| G3 | adapter isolation | sandboxed adapters, quotas, schema/size/time limits, source quarantine and blast-radius tests |
| G4 | standards interop | authoritative CCSDS ODM/TDM fixtures + round-trip/negative tests; partner formats remain contract gated |
| G5 | provenance-aware multi-hypothesis fusion | covariance/reference-frame/time normalization, contradiction retention, degraded-source exclusion and alternative hypotheses |
| G6 | PRIME releaseability/authorization | policy revision + action digest + human approval binding; TOCTOU mutation forces reevaluation |
| G7 | DDIL/degraded operation | disconnected ingest, bounded store/forward, deterministic rejoin, explicit conflicts, mission replay |
| G8 | adversarial corpus | >=60 frozen attacks/faults with quantified detection and false-negative budget |
| G9 | 10x benchmark | predeclared baseline/candidate hardware+workload, latency/recovery/reconstruction ratios and uncertainty |
| G10 | independent replication | frozen protocol repeated by an external evaluator/partner with evidence package |

No higher gate is inferred from a lower one.

## 9. External integration rule

Every external connector follows:

```text
authoritative specification
    -> explicit interface contract
    -> fixture corpus
    -> negative/adversarial tests
    -> enabled adapter
    -> internal qualification
    -> partner validation
    -> production authorization
```

Until partner validation exists, the correct claim is **REQUIRES PARTNER VALIDATION**.

## 10. Claims block

```yaml
claim:
  statement: "Worldshepherd implements a strict provenance-bound SDA canonical observation, source-isolation gate, replay/conflict controls, and deterministic reference fusion with evidence lineage."
  status:
    - IMPLEMENTED_IN_SOFTWARE
  evidence:
    - deployments/sara_verified_local_v1/worldshepherd_sara/sda.py
    - deployments/sara_verified_local_v1/tests/test_sda.py
  configuration: "feature/ws-sda-trust-fabric-v1-20260917 and CI evidence for exact tested commit"
  limitations:
    - "Unclassified synthetic/reference software baseline."
    - "No operational orbit determination or validated aerospace tracker."
    - "No UDL/CCSDS partner acceptance yet."
    - "No government authorization, CMMC certification, classified-network approval, or flight validation."
  next_gate: "Pass exact-head CI, then implement G2 workload identity and G4 authoritative CCSDS fixtures without weakening G1 invariants."
```

## 11. Completion definition

"Complete" for WS-SDA is evidence-gated:

- **Internal product completion:** G1-G9 all pass on frozen configurations.
- **Externally validated completion:** G10 passes with an independent evaluator.
- **Operational deployment completion:** separate customer/government accreditation,
  partner interface acceptance, environment authorization, and mission-specific
  validation are complete.

Those states must never be conflated.
