# Worldshepherd Quantum Mission Evidence Profile — Draft 0.1

**Status:** INTERNAL DRAFT — external technical, legal, IP and security review required before publication or standards claims.  
**Date:** 2026-08-17  
**Purpose:** Define a vendor-neutral minimum evidence profile for admitting quantum computing, quantum annealing, quantum sensing, quantum networking, quantum-materials calculations, and quantum-assisted physical metrology into Worldshepherd mission workflows.

## 1. Scope

This profile governs **evidence custody and mission qualification**, not quantum-hardware design.

It applies to evidence originating from:

- universal gate-model QPUs;
- quantum annealers;
- CPU/GPU/QPU portable runtimes;
- managed multi-provider quantum services;
- quantum sensors, clocks, inertial systems, magnetometers and gravimeters;
- quantum-network/communications systems;
- quantum chemistry/materials calculations;
- quantum-assisted metrology and physical experiments.

A provider MAY supply evidence in its native format. Worldshepherd MUST retain the native source artifact and MUST normalize only a governed representation; normalization MUST NOT overwrite the native artifact.

## 2. Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, `SHOULD NOT`, and `MAY` describe Worldshepherd profile requirements. This draft does not claim recognition as an external standard.

## 3. Universal evidence envelope

Every admitted external evidence object MUST contain or bind to:

1. project identity;
2. evidence type and computational/physical modality;
3. provider/lab identity;
4. source/run/job/device identity where applicable;
5. collection/execution UTC time;
6. native raw-artifact SHA-256;
7. configuration SHA-256;
8. program/problem/protocol identity;
9. result identity;
10. software/firmware/runtime identity where available;
11. environment/test-condition identity where material;
12. current Worldshepherd campaign gate identity;
13. declared claim boundary;
14. data-use/security/export/classification restrictions where applicable;
15. negative, failed, anomalous or degraded evidence status.

Missing mandatory fields MUST produce a fail-closed intake decision. A provider's reputation, contract status, marketing claim or prior qualification MUST NOT substitute for the missing evidence object.

## 4. Raw-artifact custody

Worldshepherd MUST:

- retain the original artifact whenever legally/security-permitted;
- compute the artifact SHA-256 locally at intake;
- compare the local hash with the supplied evidence record;
- reject digest mismatches;
- preserve a separately hashed normalized representation;
- never treat a copied textual summary as equivalent to the raw artifact when the raw artifact is available.

## 5. Classical and null controls

### 5.1 Quantum computation / optimization

Before attributing benefit to a quantum path, the evidence package MUST identify a classical baseline appropriate to the same frozen task/instance family.

For optimization, the baseline SHOULD include the strongest practical comparator available for the task family, such as exact enumeration for toy instances, CP-SAT, MILP, domain heuristics, GPU methods or another accepted solver.

### 5.2 Sensing / metrology

Sensor/metrology packages MUST identify a truth/reference method, calibration identity and quantified uncertainty/error model.

Physical experiments MUST retain applicable null/sham/control cases. A physical support experiment MUST NOT be promoted into a different physical claim merely because the measurement used quantum technology.

## 6. Evidence-stage separation

Worldshepherd MUST distinguish at minimum:

- concept;
- classical baseline;
- ideal simulation;
- noisy simulation;
- fault-tolerant resource estimate;
- calibrated model/surrogate;
- integrated simulation;
- single external hardware execution;
- reproduced external hardware;
- hardware-in-loop;
- relevant-environment evidence;
- operational demonstration.

A later-stage artifact MUST NOT skip an unsatisfied current campaign gate.

A simulator, emulator, syntax checker, resource estimator or portable runtime target MUST NOT be labeled as hardware execution without independent provider/device/job evidence.

## 7. Gate-model QPU profile

A gate-model hardware record MUST retain:

- provider and named backend/device;
- immutable job/run identity;
- canonical program/circuit digest;
- transpiled/ISA program digest where applicable;
- backend/device properties or calibration identity where exposed;
- shot count;
- sampled outcome distribution/result digest;
- queue and end-to-end latency where measurable;
- QPU/usage time where exposed;
- execution cost or explicitly documented zero-cost plan;
- failure/error/degraded state information.

## 8. Cross-backend reproduction profile

Cross-backend reproduction MUST NOT require identical sampled result digests.

Independent runs MUST have:

- distinct run identities;
- distinct immutable result-record digests;
- the same frozen canonical workload/program identity;
- the same governed classical baseline;
- explicit provider/backend identities;
- valid sampled distributions;
- predeclared statistical acceptance thresholds.

Worldshepherd's current reference comparison uses pairwise total-variation distance and squared Bhattacharyya coefficient/fidelity. Thresholds MUST be declared before interpreting the compared runs and MAY be tightened for a specific mission/problem.

Statistical agreement supports only the frozen experiment. It MUST NOT be generalized into quantum advantage or mission validity without the corresponding evidence.

## 9. Quantum annealing profile

Annealing evidence MUST be labeled as `quantum_annealing` and MUST NOT be represented as a universal gate-model QPU execution.

The package MUST retain, where available:

- solver name and current working-graph/solver identity;
- solver-properties digest;
- QUBO/BQM problem digest;
- embedding context;
- sample/energy distribution;
- read count;
- QPU access/sampling/programming timing;
- wall latency and cost;
- frozen mission-instance family digest;
- strong classical comparator digest.

Annealing qubit counts MUST NOT be compared numerically with universal gate-model physical/logical qubit counts as though they were equivalent resources.

## 10. Managed multi-provider job profile

For a managed execution service such as Amazon Braket, the evidence package MUST retain:

- managed job ARN/identity;
- underlying device ARN/provider;
- job completion status;
- container image URI and immutable image digest;
- source artifact digest;
- result artifact digest;
- program digest;
- output-storage identity;
- task/shot counts;
- queue/runtime/end-to-end timing;
- cost;
- sampled result distribution for comparable workloads.

A managed-service simulator device MUST NOT count as provider-parity hardware evidence.

## 11. Portable execution layer profile

A portable layer such as CUDA-Q MAY be used to express and execute a canonical workload across CPU/GPU/QPU targets.

The portable execution record MUST preserve:

- canonical workload digest;
- requested and resolved target;
- target options excluding secrets;
- runtime version;
- result distribution and digest;
- wall latency.

Selecting a hardware-capable target MUST NOT itself satisfy hardware provenance. Hardware promotion requires a provider-specific job/device evidence record.

## 12. Quantum sensor/APNT profile

A quantum-sensor/APNT package MUST retain:

- named device/system;
- calibration identity;
- observable(s) and units;
- sample rate/bandwidth where relevant;
- interface/data schema;
- truth/reference method;
- uncertainty/error characterization;
- environmental/platform conditions;
- denied/degraded reference condition where mission relevant;
- repeat/run identities;
- negative/failed/anomalous evidence where available;
- provenance and data-use restrictions.

A vendor product sheet, flight-count statement, certification announcement or meeting alone MUST NOT satisfy this profile.

## 13. Quantum materials profile

A materials-computation package MUST retain:

- actual physical/periodic structure artifact and digest;
- composition/site ordering and provenance;
- basis/pseudopotential/method identity;
- active-space/reduction definition when used;
- Hamiltonian digest;
- classical reference (HF/DFT/exact active-space or appropriate equivalent);
- quantum algorithm/backend details;
- uncertainty/error/convergence information.

Nominal composition alone MUST NOT be treated as a frozen atomistic structure.

Quantum calculation agreement MUST NOT substitute for physical coupon/material validation where the mission claim is about fabricated material behavior.

## 14. Human technical review

A structurally complete package MAY proceed only to `ready_for_technical_review`.

A promotion recommendation requires an identified authorized human reviewer bound to the exact ingest-decision digest. The reviewer MUST explicitly address:

- technical validity;
- provenance;
- uncertainty/error treatment;
- negative/failed/anomalous evidence;
- claim-boundary compliance;
- conflicts/bias considerations;
- known limitations.

AI-generated completion MUST NOT constitute human approval.

## 15. Canonical state change

Human technical review MAY recommend promotion. It MUST NOT mutate project state automatically.

A separate governed state-change action MUST verify:

- the current gate is the gate reviewed;
- the review is bound to the retained evidence package;
- no intervening configuration/evidence change invalidates the decision;
- the target stage does not exceed the evidence cap;
- separate safety/deployment/mission authorization requirements remain intact.

## 16. Negative evidence and failed runs

Worldshepherd SHOULD retain failed, null, anomalous and degraded runs when legally/security-permitted.

A package MUST NOT selectively omit material failures known to affect the interpreted claim. Evidence selection policy SHOULD be frozen before comparative evaluation where practical.

## 17. DDIL / degraded-state custody

For mission workflows that may operate disconnected, intermittent or bandwidth-limited:

- evidence MUST be locally timestamped and hashed;
- local configuration identity MUST be retained;
- provider synchronization MAY be deferred;
- delayed synchronization MUST preserve original local identities rather than regenerate them;
- conflicts or missing provider acknowledgements MUST be surfaced rather than silently repaired.

## 18. Conformance levels

### QM-E0 — structurally complete
All mandatory envelope fields and hashes present; no scientific acceptance implied.

### QM-E1 — technically reviewed
Identified-human review accepted; no mission-stage promotion implied.

### QM-E2 — reproduced
Required repeat/cross-provider or repeat/sensor evidence satisfies predeclared reproduction criteria.

### QM-E3 — integrated
Evidence is incorporated into the mission system with classical/reference comparator and HIL/degraded testing appropriate to the lane.

### QM-E4 — relevant environment
Evidence satisfies the lane's defined relevant-environment acceptance criteria.

### QM-E5 — operational demonstration
Operational demonstration evidence exists. This profile level still does not grant deployment/safety authority by itself.

## 19. Required conformance tests before external publication

Before Worldshepherd presents this profile as a differentiated market capability, it SHOULD demonstrate at minimum:

1. rejection of a package with a mismatched raw-artifact digest;
2. rejection of a later-stage package aimed past the active gate;
3. rejection of an incomplete sensor package missing calibration/truth reference;
4. rejection of a simulator/portable-target record relabeled as hardware;
5. rejection of reused identical result-record identity as independent reproduction;
6. acceptance of two statistically consistent but non-identical real-QPU result distributions under predeclared thresholds;
7. acceptance of a complete managed-job package with retained provider/container/source/result provenance;
8. human review bound to the exact accepted ingest decision;
9. demonstration that review recommendation does not mutate canonical state;
10. DDIL/deferred-sync evidence identity preservation.

## 20. Publication boundary

This is an **internal Worldshepherd draft**. Before publication as a specification or external assurance claim, obtain:

- external technical review;
- legal/IP review;
- security/data-classification review;
- review for compatibility with applicable customer/agency evidence and authorization requirements;
- versioned release approval.

## 21. Positioning statement if validated

If the conformance tests and external review are completed, a defensible positioning statement would be:

> Worldshepherd provides a vendor-neutral Quantum Mission Evidence Profile for qualifying heterogeneous quantum compute and sensing evidence under common provenance, comparator, statistical-reproduction, no-skip and human-review controls.

Until then, this remains an internally implemented/drafted architecture and MUST NOT be described as an independently certified standard.
