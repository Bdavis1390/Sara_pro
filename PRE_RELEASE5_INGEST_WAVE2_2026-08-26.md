# PRE Release-5 Ingest — Wave 2 — 2026-08-26

Claims-controlled requirement ingest for reusable Worldshepherd capability development. Operative proposal requirements remain subject to direct solicitation/DSIP freeze review.

## PRE-RD-2026-0006 — Dynamic open mission enclave
- Demand: CONFIRMED_DEMAND
- Topic: DAF26BZ05-DV033 — Dynamic Open Systems Enclave
- Source status: OFFICIAL_SOURCE_VERIFIED subject to final proposal-package review
- Horizon: 0-90D
- Requirement signal: legacy platforms need a modular high-speed computing enclave that can accept new processing/sensor/software capability without redesigning the host platform.
- Existing WS capability: SARA service orchestration; ECHO provenance; PRIME authorization; OVERWATCH health/replay — IMPLEMENTED IN SOFTWARE where retained evidence exists.
- Missing: aircraft/mission-platform integration, flight-qualified compute, airworthiness, operational BLOS evidence.
- Build now: Common Services / Dynamic Mission Enclave with adapter boundary, identity, configuration custody, SBOM, telemetry, policy, health, rollback and replay.
- Evidence target: same bounded service module deployed through two synthetic platform adapters with preserved configuration/provenance and rollback evidence.

## PRE-RD-2026-0007 — Parallel sensor fusion qualification
- Demand: CONFIRMED_DEMAND
- Topic: DON26BZ05-NV077 — Multi-Core Parallel Processing for Sensor Fusion Architecture
- Source status: OFFICIAL_SOURCE_VERIFIED subject to final proposal-package review
- Horizon: 0-90D
- Requirement signal: parallel spatial alignment, temporal correlation and attribute fusion while reducing latency without losing track integrity.
- Existing WS capability: provenance/observability/orchestration architecture — IMPLEMENTED IN SOFTWARE.
- Missing: validated multi-sensor fusion engine, representative NAVAIR data, aircraft processor validation.
- Build now: synthetic multi-sensor truth set + parallel stage benchmark + source/track lineage.
- Evidence target: latency, throughput, track-retention, association accuracy, CPU/core utilization and failure/degradation results.

## PRE-RD-2026-0008 — Task-aware radar data compression
- Demand: CONFIRMED_DEMAND
- Topic: OSW26BZ05-DV018 — AI/ML-Based Radar Data Compression
- Source status: OFFICIAL_SOURCE_VERIFIED subject to final proposal-package review
- Horizon: 0-90D / 3-12M
- Requirement signal: compress raw/complex radar data while preserving downstream imaging/detection/track utility; later move to embedded resource-constrained hardware.
- Existing WS capability: experiment governance/provenance patterns — IMPLEMENTED IN SOFTWARE.
- Missing: representative radar dataset, trained compression model, task-fidelity benchmark, embedded implementation.
- Build now: generic Sensor Compression Qualification Harness.
- Evidence target: compression ratio, reconstruction error, downstream task fidelity, latency, RAM, bandwidth and power/resource estimates.

## PRE-RD-2026-0009 — Semantic reduction under DDIL and low SWaP
- Demand: CONFIRMED_DEMAND
- Topic: DPA26BZ05-DV019 — Semantically-Aware ISR
- Source status: OFFICIAL_SOURCE_VERIFIED subject to final proposal-package review
- Horizon: 0-90D / 3-12M
- Requirement signal: preserve mission-relevant information while reducing transmission load under degraded communications and edge power constraints; retain confidence/uncertainty and traceability.
- Existing WS capability: ECHO provenance/confidence architecture, SARA workflow, PRIME governance — IMPLEMENTED IN SOFTWARE where evidenced.
- Missing: semantic encoder, representative ISR data, measured reduction/fidelity, edge-power benchmark, UAS integration.
- Build now: semantic reduction benchmark using public/synthetic sensor data and task-aware utility metrics.
- Evidence target: reduction ratio, mission-task fidelity, confidence calibration, latency, memory, watts/joules, packet-loss robustness.

## PRE-RD-2026-0010 — CMMC/NIST 800-171 recurring delivery gate
- Demand: CONFIRMED_DEMAND
- Source: recurring Navy/DoW Release-5 cybersecurity clauses
- Source status: OFFICIAL_SOURCE_VERIFIED at topic level; exact contract requirement remains topic/award specific
- Horizon: 0-90D
- Requirement signal: CMMC/NIST 800-171 readiness recurs across software, autonomy, RF, C2 and digital-twin opportunities.
- Existing WS capability: local role separation, audit, configuration and bounded administration — IMPLEMENTED IN SOFTWARE.
- Missing: documentary SSP/POA&M, assessment status, complete control evidence, SPRS/CMMC state.
- Build now: fail-closed compliance-evidence layer with UNKNOWN default for unverified status.
- Evidence target: machine-readable mapping from internal control evidence to readiness gaps without claiming compliance/certification.

## PRE-RD-2026-0011 — Interpretable RF classification on modest compute
- Demand: CONFIRMED_DEMAND
- Topic: OSW26BZ05-DV022 — Signal Classification and Anomaly Detection in Contested Spectral Environments
- Source status: OFFICIAL_SOURCE_VERIFIED subject to final proposal-package review
- Horizon: 3-12M
- Requirement signal: transparent/modular RF classification, anomaly detection, CPU-class deployment, containerization and continuous updateability.
- Existing WS capability: governance/container/evidence architecture — IMPLEMENTED IN SOFTWARE.
- Missing: labeled RF datasets, trained classifiers, benchmarked accuracy/anomaly detection, explainability and resource measurements.
- Build now: RF Classification Lab with strong classical baselines and synthetic/public data only until representative partner data exists.
- Evidence target: accuracy, unknown-class detection, calibration, inference latency, CPU/RAM, explanation artifact, model/version lineage and OOD performance.

## Cross-wave architecture conclusion
The recurring requirement family is now:

`legacy source/platform -> adapter -> common services -> bounded algorithm -> confidence/provenance -> human/policy gate -> qualification evidence -> replay`

Priority reusable modules:
1. Qualification Evidence Compiler
2. Evidence Graph Service
3. DDIL/fault-injection harness
4. Dynamic Mission Enclave/Common Services
5. Sensor Fusion Qualification Harness
6. Sensor Compression Qualification Harness
7. Edge/SWaP Benchmark Harness
8. CMMC/NIST readiness evidence layer
9. RF Classification Lab

No module acquires platform, compliance, certification, physical or operational validity merely through this ingest.
