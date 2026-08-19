# Worldshepherd Quantum Readiness Fabric (QRF)

Status: architecture + governance scaffold; does **not** assert ownership of a QPU or quantum advantage.

## Purpose

Bring Worldshepherd to a credible 2026 quantum R&D operating standard by closing the gaps that are accessible without fabricating an in-house quantum computer:

1. provider-agnostic quantum program representation and execution;
2. classical/null baselines before quantum attribution;
3. ideal/noisy simulation before QPU spend;
4. fault-tolerant resource estimation before scalability claims;
5. immutable QPU provenance, calibration and result evidence;
6. reproducibility across runs/backends where practical;
7. post-quantum security migration now;
8. project-specific quantum relevance gates so quantum is not forced into unrelated work.

## External benchmark direction

The reference architecture is aligned to the direction visible across current major programs:

- IBM: modular/fault-tolerant roadmap, Qiskit primitives, error mitigation and runtime execution.
- Google Quantum AI: quantum error correction and logical-qubit scaling as core milestones.
- Quantinuum: logical-qubit execution and high-fidelity trapped-ion systems.
- Microsoft: fault-tolerant quantum resource estimation.
- AWS Braket: hybrid quantum-classical jobs and multi-provider QPU access.
- NVIDIA CUDA-Q: CPU/GPU/QPU hybrid programming and accelerated simulation.
- OpenQASM 3 and QIR: portable program/IR layers for heterogeneous quantum backends.
- NIST PQC: ML-KEM, ML-DSA and SLH-DSA are deployment-ready standards for quantum-resistant security.
- NSF Project Triad: integrated quantum sensing, networking and computing is an important systems-level benchmark direction.

Primary references:

- https://www.ibm.com/quantum/hardware
- https://quantumai.google/roadmap
- https://www.quantinuum.com/products-solutions/quantinuum-systems/helios
- https://learn.microsoft.com/en-us/azure/quantum/intro-to-resource-estimation
- https://docs.aws.amazon.com/braket/latest/developerguide/braket-jobs.html
- https://developer.nvidia.com/cuda-q
- https://openqasm.com/
- https://www.qir-alliance.org/
- https://csrc.nist.gov/projects/post-quantum-cryptography
- https://www.nsf.gov/news/nsf-launches-project-triad-advance-quantum-technology-real

## QRF layers

### Q0 — Claims and evidence gate

Every quantum-tagged result receives:

- project ID and experiment ID;
- domain: computing, sensing, networking, materials or PQ security;
- evidence level;
- backend class and provider;
- circuit/program digest;
- calibration identifier where applicable;
- classical baseline reference;
- result digest;
- uncertainty/statistical metadata;
- claim ceiling.

No evidence object may upgrade itself. Promotion requires a new evidence record satisfying the next gate.

### Q1 — Classical/null baseline

Required before quantum attribution.

Examples:

- optimization: MILP/CP-SAT/metaheuristic baseline;
- materials: DFT/MD/phase-field baseline;
- sensing: calibrated conventional IMU/magnetometer/clock baseline;
- numerical/Glob: permutation/randomized/null-model baseline;
- metasurface: FDTD/FEM/full-wave baseline.

### Q2 — Portable quantum formulation

Represent quantum workloads in a portable form where possible:

- OpenQASM 3 for gate/circuit interchange;
- QIR for compiler/intermediate-representation portability;
- Hamiltonian/oracle/problem specification stored separately from provider code.

Provider-specific SDKs become adapters, not the canonical scientific record.

### Q3 — Simulation ladder

Required order unless a justified exception is recorded:

1. analytic/toy check;
2. ideal statevector/stabilizer simulation;
3. noisy simulation with explicit noise model;
4. hardware-aware transpilation/compilation;
5. QPU execution.

A simulation is never labeled a hardware result.

### Q4 — Resource estimation

Any future fault-tolerant/scalability claim must record at minimum:

- logical qubits;
- logical gate/depth estimate;
- selected QEC model;
- physical-qubit estimate;
- runtime estimate;
- factory/ancilla assumptions when relevant;
- sensitivity to physical error rate.

### Q5 — QPU execution and reproduction

For each QPU run retain:

- provider/backend;
- timestamp;
- backend topology/native gates;
- calibration snapshot/identifier when exposed;
- compilation/transpilation settings;
- shots;
- seed where meaningful;
- raw measurement/result object digest;
- post-processing code/version;
- mitigation settings;
- comparison to the registered classical baseline.

Strong validation should include repeated runs and, where the problem permits, a second backend/provider.

### Q6 — Quantum sensing/networking partner lane

Worldshepherd should treat quantum sensing and networking as partner-hardware domains until calibrated hardware is physically controlled and tested. SARA can still own:

- interface contracts;
- telemetry/provenance;
- time synchronization requirements;
- estimator/fusion logic;
- uncertainty propagation;
- degraded-state behavior;
- security/governance.

### Q7 — Post-quantum security lane

PQC is deployable now and should not wait for a fault-tolerant QPU.

Migration order:

1. cryptographic inventory;
2. identify RSA/ECC dependence and long-lived sensitive data;
3. add crypto-agility interfaces;
4. test ML-KEM for key establishment and ML-DSA/SLH-DSA for signatures where compatible;
5. use hybrid deployment patterns where protocol/ecosystem constraints require them;
6. preserve rollback/interoperability testing and signed migration evidence.

## Project application matrix

### SARA / Worldshepherd OS

Immediate:

- add QPU/backend registry and quantum evidence records;
- OpenQASM/QIR artifact digests in the audit plane;
- simulator/QPU distinction enforced by schema;
- resource-estimator evidence type;
- PQC migration inventory;
- cloud-QPU credentials isolated from result metadata.

Claim ceiling: quantum-capable orchestration, not quantum computer ownership.

### WS-AlTi M1-MSZ-Prime

Use quantum only where it can add information beyond classical materials methods:

- reduced electronic-structure/Hamiltonian studies;
- VQE or related eigensolver benchmarks for carefully selected active spaces;
- resource estimation for larger chemistry/material workloads;
- strict comparison with DFT/experiment.

Do not use quantum output to bypass coupon manufacture, microscopy, mechanical tests or process validation.

### Adaptive metasurface / programmable EM boundary

Priority remains full-wave/multi-physics classical simulation.

Quantum lanes:

- QAOA or other quantum optimization as a benchmark for discrete tile-state/control allocation;
- quantum-materials models for candidate tunable material behavior;
- partner quantum sensors for field/metrology experiments where sensitivity justifies them.

Signed phase coupling is classical EM/control mathematics and must not be relabeled as entanglement.

### APNT / assured PNT

High-value partner lane:

- atomic-clock integration;
- quantum inertial sensing;
- quantum magnetometry;
- timing/network synchronization;
- PQC for control/data links.

SARA owns fusion, provenance, fault handling and interface governance; sensor physics remains partner-validated until Worldshepherd has calibrated devices.

### GLOB / numerical target research

Default classification: classical mathematical/numerical research.

A quantum experiment is allowed only after a legitimate problem mapping exists: e.g. an explicit oracle, Hamiltonian, amplitude-estimation task or optimization objective with a classical null model. Number coincidences, prime indexing or permutation orbits are not quantum evidence by themselves.

Claim ceiling stays quantum-simulated unless the profile is deliberately upgraded after a defensible algorithm and QPU experiment exist.

### EM / electrogravitic propulsion research

Quantum methods may support:

- materials electronic-structure calculations;
- sensor/metrology design;
- noise-limited force measurement.

They may not be used as evidence that anomalous propulsion exists. Net-force claims still require controlled physical measurement with null tests and conventional momentum/thermal/EM artifact rejection.

### Autonomous logistics / optimization

Use hybrid quantum optimization only as a challenger to strong classical solvers. Record:

- solution quality;
- wall-clock latency;
- QPU queue/compute time;
- total cost;
- robustness across instances;
- scaling behavior.

Quantum is promoted only when the project-specific trade space improves.

## Evidence ladder

| Level | Meaning | Allowed language |
|---|---|---|
| concept | idea/problem mapping | quantum candidate |
| classical_baseline | null/reference established | benchmark-ready |
| ideal_simulation | ideal circuit/model result | quantum-simulated (ideal) |
| noisy_simulation | explicit noise model | quantum-simulated (noisy) |
| resource_estimated | FT resource model run | fault-tolerant resource estimate |
| qpu_executed | real backend result | executed on named QPU |
| reproduced_qpu | repeat/second backend evidence | reproduced quantum execution |
| independently_reproduced | external reproduction | independently reproduced |

"Quantum advantage" is not generated by this ladder. It requires a task-specific demonstration against appropriate classical methods, with cost/accuracy/runtime definitions fixed in advance.

## Immediate acceptance criteria

Worldshepherd is "up to snuff" at the accessible software/evidence layer when all are true:

- [ ] QRF tests pass in CI.
- [ ] At least one ideal and one noisy simulator adapter are operational.
- [ ] At least one real QPU adapter executes a reproducible smoke workload.
- [ ] One fault-tolerant resource estimator is integrated.
- [ ] OpenQASM 3 or QIR artifact export/digest is retained.
- [ ] Classical baseline is mandatory for every project quantum experiment.
- [ ] Backend calibration/provenance is retained for QPU jobs.
- [ ] PQC inventory is complete and at least one non-production hybrid migration test passes.
- [ ] WS-AlTi runs one materials benchmark with classical reference.
- [ ] Metasurface runs one optimization benchmark with classical reference.
- [ ] APNT has a named quantum-sensing partner/test path or is explicitly marked unavailable.
- [ ] GLOB remains claims-gated and cannot promote numerical structure into quantum evidence.

## What remains impossible to bridge in software

These require capital equipment and/or external partners:

- qubit fabrication;
- cryogenics/laser/vacuum hardware for leading QPU modalities;
- in-house fault-tolerant logical qubits;
- calibrated quantum inertial/magnetic/clock hardware;
- deployed entanglement-distribution network;
- independent laboratory replication.

Those are partner/acquisition/physical-validation gaps, not code gaps.
