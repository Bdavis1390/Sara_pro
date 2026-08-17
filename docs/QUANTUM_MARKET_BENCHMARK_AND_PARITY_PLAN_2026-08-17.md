# Worldshepherd Quantum Market Benchmark and Parity Closure Plan

**Date:** 2026-08-17  
**Scope:** Quantum computing, hybrid orchestration, fault-tolerant resource estimation, annealing/optimization, quantum sensing/APNT, evidence governance, and mission integration.

## Positioning rule

Worldshepherd is **not** benchmarked as a QPU manufacturer. The correct comparison is a provider-neutral mission-integration and evidence-governance layer that uses external quantum computing/sensing resources while preserving classical baselines, provenance, uncertainty, negative evidence, no-skip gates, and human technical review.

The strongest market threat to that positioning is not IBM/Google hardware by itself. It is the emergence of broad full-stack platforms such as IonQ (compute + networking + sensing + security), Q-CTRL (infrastructure software + fielded quantum navigation + defense applications), NVIDIA CUDA-Q (QPU-agnostic accelerated orchestration), AWS Braket (multi-provider managed execution), and IBM's quantum-centric HPC workflow direction.

## Current market references and Worldshepherd use

| Market reference | Publicly demonstrated/current capability | Worldshepherd operational use |
|---|---|---|
| IBM Quantum | 2026 roadmap targets up to three 120-qubit Nighthawk modules / 7,500-gate circuits; quantum-centric HPC, profiling, verification/debug tools; Starling target 200 logical qubits / 100M gates in 2029 | First real-QPU evidence provider; benchmark for queue/latency/backend/calibration provenance; future quantum-centric workflow comparator |
| Quantinuum Helios | 98 fully connected physical qubits; 50 logical qubits in published configuration; 99.9975% 1Q and 99.921% 2Q gate fidelity; cloud and on-prem access | High-fidelity second-provider target; logical-qubit/QEC evidence comparator; cross-backend reproduction candidate |
| Google Quantum AI | Willow platform; public claim of verifiable quantum advantage via Quantum Echoes | Advantage-claim standard: WS may not use 'quantum advantage' without a task-specific, reproducible comparator and independent verification path |
| IonQ | Forte Enterprise 36 physical qubits; Tempo target 100 qubits / 99.9% fidelity; current portfolio extends into networking, sensing and security; Vector Atomic acquisition adds clocks/inertial/PNT | Second-provider computing target and APNT partner; strategic full-stack competitor/partner comparator |
| D-Wave | Generally available Advantage2 annealer with >4,400 qubits and ~40,000 couplers; production Leap access; optimization/materials focus | Add annealing as a distinct optimization backend/comparator for WS logistics/metasurface/materials; never compare annealing qubit count directly with universal gate-model qubits |
| NVIDIA CUDA-Q | QPU-agnostic CPU/GPU/QPU programming model; supports simulators and real QPUs; NVIDIA states integration with ~75% of publicly available QPUs | Preferred integration target for backend-neutral execution rather than reimplementing a compiler/runtime ecosystem; use for GPU-accelerated simulation and multi-provider execution |
| AWS Braket | Managed hybrid jobs, multiple hardware modalities/providers, containerized execution, priority QPU queueing, BYOC, metrics and cost tracking | Provider-breadth path; candidate execution fabric for IonQ/AQT/IQM/Rigetti/QuEra-style multi-provider evidence and reproducible containers |
| Microsoft QDK Resource Estimator | Local open-source qdk.qre workflow; application/hardware/QEC models; Pareto physical-qubit/runtime estimates; no Azure account required | Already integrated as governed resource-estimation engine; use rather than replace; add multi-architecture sensitivity sweeps |
| Q-CTRL Ironstone Opal | Field validation in air/land/sea; 2026 DO-160 safety-of-flight qualification; >100x claimed advantage over strategic-grade classical INS on its published benchmark; evaluation/system-integration partner path | Highest-priority APNT field-evidence partner; benchmark for relevant-environment and certification-level evidence |
| SandboxAQ AQNav | Quantum-sensor + AI magnetic navigation; current product page reports >200 sorties and >500 flight hours; system-of-systems integration | APNT calibrated-data/device target; comparator for integration, truth reference, uncertainty and denied-GNSS evidence |
| IonQ / Vector Atomic | Field-validated clocks, inertial sensors, gravimetry/PNT; >$200M government-contract history reported by IonQ | APNT timing/inertial/gravimetry evidence path and mission-hardware comparator |
| Infleqtion | Neutral-atom quantum systems plus commercial quantum RF, clock and inertial-navigation offerings | Parallel APNT sensing/time source; neutral-atom modality/provider comparator |

## Competitive assessment

### Category A — Worldshepherd intentionally does not seek parity

1. **Owned universal QPU hardware** — IBM, Quantinuum, Google, IonQ and others are years and very large capital programs ahead. WS target: integrate, benchmark and govern rather than fabricate.
2. **Owned annealing QPU** — D-Wave is mature and commercially available. WS target: add D-Wave as a backend/comparator where the problem formulation is appropriate.
3. **Owned QEC/logical-qubit stack** — market leaders have physical implementations; WS has only estimator/governance tooling. WS target: consume and validate external logical/QEC evidence.
4. **Quantum-sensor manufacturing** — Q-CTRL, SandboxAQ, IonQ/Vector Atomic and Infleqtion have field/device programs. WS target: multi-vendor sensor integration and evidence custody.

### Category B — parity is achievable through integration

1. **Backend neutrality** — current WS is IBM-first. Target: IBM + at least one independent gate-model provider + D-Wave annealing + one managed multi-provider fabric.
2. **Hybrid orchestration** — current WS has governed execution paths but not CUDA-Q/Braket-scale provider breadth or GPU acceleration. Target: CUDA-Q adapter and Braket execution record.
3. **Reproducible execution** — current WS has immutable digests and CI. Target: container image digest, environment/SBOM identity, repeated provider runs, statistical cross-backend comparison.
4. **Resource estimation** — current WS uses Microsoft QDK correctly. Target: multi-architecture/QEC sensitivity envelope, not one smoke estimate.
5. **PQC / crypto agility** — current WS source inventory is discovery-only. Target: runtime TLS/SSH/OIDC/JWT/release-signing/backup cryptography inventory and a non-production PQ/hybrid migration trial.

### Category C — potential Worldshepherd differentiator

Worldshepherd should compete on **provider-neutral evidence custody and mission qualification**, not ownership of every quantum modality.

Required differentiators:

- one evidence schema spanning QPU execution, sensing, materials, optimization and physical metrology;
- mandatory classical/null comparator before quantum promotion;
- explicit separation of simulator, resource-estimator, QPU, repeated-QPU, HIL, relevant-environment and operational evidence;
- local raw-artifact SHA-256 verification;
- current-gate enforcement and no stage skipping;
- retention of negative, failed, anomalous and degraded evidence;
- identified-human technical review bound to the exact ingest decision;
- separate canonical state-change decision;
- latency, cost, queue, degraded-state and provenance metrics treated as mission variables;
- provider/vendor claims never accepted as Worldshepherd validation evidence without intake/review.

## Parity closure targets

### P0 — already closed internally

- [x] evidence-capped 97/100 mission gate
- [x] Qiskit/Aer ideal/noisy execution
- [x] IBM Runtime hardware adapter
- [x] Microsoft QDK resource-estimator integration
- [x] classical-vs-quantum application benchmark harness
- [x] typed external evidence intake
- [x] local artifact re-hash
- [x] stage-locked external campaigns
- [x] identified-human technical review
- [x] APNT synthetic truth-reference harness
- [x] lane-specific fail-closed physical/scientific validators

### P1 — minimum market parity evidence

- [ ] Execute `QRF-BELL-001` on one real IBM QPU and pass full ingest + human technical review.
- [ ] Repeat on the same IBM backend and perform statistical reproducibility analysis.
- [ ] Execute the same canonical workload on a second independent gate-model provider (preferred: Quantinuum or IonQ, direct or via Braket).
- [ ] Add distribution-level cross-backend reproducibility metrics; do not require identical sampled-result digests.
- [ ] Add D-Wave Advantage2 annealing adapter/comparator for an appropriate WS optimization benchmark.
- [ ] Add CUDA-Q backend adapter or an equivalent portable execution layer.
- [ ] Run one AWS Braket reproducible-container hybrid job and retain device ARN/provider, container digest, queue/runtime/cost/result provenance.
- [ ] Run Microsoft QDK estimates across at least three hardware/QEC assumption sets and retain Pareto sensitivity rather than a single estimate.

### P2 — application/mission parity evidence

- [ ] APNT: acquire one calibrated external quantum-sensor/device/dataset package and close `WS-APNT-EXT-02` only after human review.
- [ ] Metasurface: calibrate reduced objective against retained Maxwell/FEM/FDTD evidence and compare classical optimizer, gate-model QPU and annealing backend where formulation permits.
- [ ] Logistics: freeze a real mission instance family and compare CP-SAT/MILP/heuristic, gate-model QAOA and annealing/hybrid solvers end-to-end including queue/cost/latency.
- [ ] AlTi: freeze an actual periodic structure, produce classical electronic-structure references and only then derive/reduce a Hamiltonian for quantum comparison.
- [ ] GLOB: promote only if a legitimate measurable search/sampling/optimization/Hamiltonian mapping beats null and classical-complexity objections.
- [ ] EM support: keep quantum work limited to bounded materials/metrology tasks unless independent controlled physical force/energy evidence exists.

### P3 — differentiation evidence

- [ ] Demonstrate the same mission problem through >=3 mutually independent compute/provider modalities under one evidence schema.
- [ ] Demonstrate a sensor-fusion mission using >=2 independent APNT sensing sources under one calibration/uncertainty provenance model.
- [ ] Demonstrate automatic fail-closed rejection of a vendor package with missing calibration/negative evidence while accepting a complete package.
- [ ] Demonstrate degraded/DDIL execution with preserved local evidence custody and delayed provider synchronization.
- [ ] Publish a vendor-neutral Quantum Mission Evidence Profile / benchmark specification after legal/IP review.
- [ ] Obtain external technical review/audit of the Worldshepherd evidence-governance methodology.

## Market-readiness interpretation

Worldshepherd should not claim 'market leadership in quantum computing.' The defensible present positioning is:

> **Worldshepherd is an emerging provider-neutral quantum mission integration and evidence-governance architecture. It is designed to qualify when and how external quantum computing and sensing resources can enter mission workflows, with classical/null baselines, provenance, uncertainty, no-skip evidence stages, and human review.**

The strongest future claim, if P1-P3 evidence is completed, is not 'better QPU.' It is:

> **A vendor-neutral mission qualification layer that can compare, combine, reject and govern competing quantum compute and sensing modalities using one retained evidence chain.**

## Source-to-use provenance

Primary/current sources used for this benchmark:

- IBM Quantum Roadmap: https://www.ibm.com/roadmaps/quantum/
- IBM Quantum 2026: https://www.ibm.com/roadmaps/quantum/2026/
- Quantinuum Helios: https://www.quantinuum.com/products-solutions/quantinuum-systems/helios
- Google Quantum AI: https://quantumai.google/
- IonQ Forte Enterprise: https://www.ionq.com/quantum-systems/forte-enterprise
- IonQ Tempo: https://www.ionq.com/quantum-systems/tempo
- IonQ Vector Atomic completion: https://investors.ionq.com/news/news-details/2025/IonQ-Completes-Acquisition-of-Vector-Atomic-the-Global-Leader-in-Advanced-Quantum-Sensing/default.aspx
- D-Wave Advantage2 GA: https://www.dwavequantum.com/company/newsroom/press-release/d-wave-announces-general-availability-of-advantage2-quantum-computer-its-most-advanced-and-performant-system/
- NVIDIA CUDA-Q: https://developer.nvidia.com/cuda-q
- Amazon Braket Hybrid Jobs: https://docs.aws.amazon.com/braket/latest/developerguide/braket-jobs.html
- Amazon Braket hardware: https://aws.amazon.com/braket/quantum-computers/
- Microsoft Quantum Resource Estimator: https://learn.microsoft.com/en-us/azure/quantum/intro-to-resource-estimation
- Q-CTRL Ironstone Opal: https://q-ctrl.com/ironstone-opal
- Q-CTRL 2026 airworthiness announcement: https://q-ctrl.com/blog/q-ctrl-to-showcase-worlds-first-airworthiness-qualified-quantum-navigation-gps-backup-at-the-farnborough-international-airshow
- SandboxAQ AQNav: https://www.sandboxaq.com/solutions/aqnav
- Infleqtion: https://ir.infleqtion.com/

## Claims control

Vendor specifications, roadmaps, press releases and product claims in this document are market intelligence, not Worldshepherd validation evidence. Forward-looking vendor roadmaps are not treated as achieved capabilities. Cross-company qubit counts, logical-qubit definitions, annealing qubits and benchmark metrics are not treated as directly interchangeable. Worldshepherd mission scores change only through the governed evidence campaign and human-review process.
