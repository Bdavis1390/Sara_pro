# Worldshepherd QRF — APNT Quantum-Sensing Partner Evaluation Package

**Date:** 2026-08-17  
**Primary gate:** `WS-APNT-EXT-02`  
**Target transition:** `synthetic_surrogate` -> `calibrated_model`  
**Later live-device gate:** `WS-APNT-EXT-04` (`integrated_simulation` -> `single_external_hardware`)

## Purpose

Identify and evaluate external quantum-sensing partners capable of supplying the calibrated device/data evidence required by the Worldshepherd APNT campaign. The objective is **not** a generic partnership announcement. The objective is a bounded technical evidence package that can pass `quantum_external_evidence.py`, be tied to the APNT campaign, and later support a live hardware-integration path.

Vendor marketing claims, press releases, demos, and capability statements are useful for partner selection but are **not Worldshepherd evidence** until actual artifacts are delivered and pass intake and technical review.

## Why this is the next APNT gate

Worldshepherd currently holds `WS-APNT` at the concept evidence stage. Before any hardware result can be promoted, the campaign requires a frozen simulated benchmark followed by a **calibrated named sensor/device or dataset** with a truth reference and quantified uncertainty.

For `WS-APNT-EXT-02`, the QRF intake package must ultimately supply at least:

- `project_id=WS-APNT`
- `evidence_type=quantum_sensor`
- `metadata.campaign_gate_id=WS-APNT-EXT-02`
- named `provider_or_lab`
- named `backend_or_device`
- immutable raw-artifact SHA-256
- immutable configuration SHA-256
- explicit UTC collection timestamp
- `calibration_id`
- `truth_reference_id`
- non-negative quantified `uncertainty`
- `metadata.observable`
- `metadata.units`
- `metadata.sample_rate_hz`
- `metadata.calibration_certificate_digest`
- `metadata.test_protocol_digest`
- an accepted record collected in a calibration or integration-lab context

The request should also ask for failures, exclusions, anomalous runs, dropouts, saturation events, degraded cases, and known limitations rather than only best-case results.

## Current partner priority

The following ordering is an **internal evidence-acquisition fit ranking**, not a probability of agreement, endorsement, or proof that access is available to Worldshepherd.

### 1. Q-CTRL — Ironstone Opal

**Current fit: highest priority for `WS-APNT-EXT-02` and later live-platform gates.**

Why it ranks first:

- Q-CTRL currently states that it is engaging select partners for additional field trials and system-integration demonstrations.
- Q-CTRL reports quantum-navigation field validation on airborne, ground, and maritime platforms.
- In July 2026 Q-CTRL announced that Ironstone Opal had achieved RTCA DO-160 safety-of-flight qualification.
- Ironstone Opal is positioned as a complete quantum-assured navigation system rather than a bare sensor component, which makes interface/integration evidence directly relevant to later Worldshepherd HIL gates.

Official current references:

- https://q-ctrl.com/our-work/positioning-navigation-and-timing
- https://q-ctrl.com/ironstone-opal
- https://q-ctrl.com/blog/q-ctrl-to-showcase-worlds-first-airworthiness-qualified-quantum-navigation-gps-backup-at-the-farnborough-international-airshow

**Requested first engagement:** a bounded technical evaluation discussing calibrated output/data access, truth-reference methodology, uncertainty, interface schemas, update rates, degraded-GNSS test evidence, and a path to a later system-integration demonstration.

### 2. SandboxAQ — AQNav

**Current fit: strongest parallel magnetic-navigation comparator/integration path.**

Why it ranks second:

- SandboxAQ describes AQNav as a GNSS-independent magnetic-navigation system combining high-sensitivity quantum magnetometers with AI/quantitative models and geomagnetic maps.
- Its current product page reports testing across more than 200 sorties and more than 500 flight hours.
- The system is specifically positioned for continuity in GPS-compromised environments and operational integration.

Official current references:

- https://www.sandboxaq.com/solutions/aqnav
- https://www.sandboxaq.com/press/sandboxaq-announces-aqnav---worlds-first-commercial-real-time-navigation-system-powered-by-ai-and-quantum-to-address-gps-jamming
- https://www.sandboxaq.com/press/sandboxaq-publishes-scientific-and-technical-milestones-for-magnetic-anomaly-based-navigation

**Requested first engagement:** a calibrated/replayable AQNav evaluation dataset or controlled integration path with truth-position source, magnetic sensor identity/calibration, map/source provenance, uncertainty/error statistics, timing, interface schema, and failed/degraded cases.

### 3. IonQ / Vector Atomic

**Current fit: strong precision timing, inertial, synchronization, gravimetry, and PNT hardware path.**

Why it ranks third:

- IonQ completed its acquisition of Vector Atomic on October 7, 2025.
- IonQ states the acquired portfolio includes precision atomic clocks, inertial sensors, synchronization hardware, gravimetry, and PNT systems.
- IonQ describes Vector Atomic systems as deployable/field-validated across sea, airborne, space, and other demanding environments.

Official current reference:

- https://www.ionq.com/news/ionq-completes-acquisition-of-vector-atomic-the-global-leader-in-advanced

**Requested first engagement:** access to a field-relevant timing/inertial sensor evaluation with a calibration identity, truth reference, uncertainty budget, output/interface definition, environmental profile, and repeatability evidence.

### 4. Infleqtion

**Current fit: parallel inertial-navigation and resilient timing candidate.**

Why it ranks fourth:

- Infleqtion currently markets quantum inertial sensing for long-duration GPS-independent navigation.
- Its current materials state that inertial sensing supplies the position/navigation portion of PNT and Tiqker atomic-clock technology supplies timing.
- Company filings describe development of next-generation quantum inertial and gravimetric sensors targeted at real-world GPS-denied deployment.

Official current references:

- https://infleqtion.com/inertial-sensing/
- https://ir.infleqtion.com/sec-filings/all-sec-filings/content/0001193125-26-227233/d117679d424b3.htm

**Requested first engagement:** calibrated inertial/timing output data or live evaluation access with uncertainty, truth reference, timing stability/drift characteristics, interfaces, environmental limits, and availability for later HIL integration.

## Required technical questions for every candidate

The first technical contact should seek direct answers and/or artifacts for the following topics.

### Device and configuration identity

- Exact product/system name and version.
- Sensor modality or modalities: atom interferometry, magnetic anomaly navigation, optical clock, inertial sensor, gravimeter, hybrid system, or other.
- Hardware serial/device identifier available for an evaluation unit or dataset.
- Firmware/software build/version and whether a configuration manifest can be supplied.
- Configuration changes between calibration, bench test, field test, and supplied dataset.

### Calibration and traceability

- Calibration identifier and date.
- Calibration certificate/report availability.
- Calibration laboratory or responsible organization.
- Traceability chain and reference standard where applicable.
- Recalibration interval and conditions that invalidate calibration.

### Truth reference

- Exact truth/reference system used during validation.
- Reference device/system identifier.
- Reference accuracy and uncertainty.
- Time synchronization method between sensor and truth stream.
- Coordinate frames, datum, units, timestamp conventions, and transformation chain.

### Measurement definition

- Observable(s) produced by the system.
- Units.
- Raw sample/update rate.
- Processed navigation solution rate.
- Latency and jitter.
- Dynamic range, saturation limits, dead zones, dropout behavior, startup/warmup time, and recovery behavior.

### Quantified uncertainty and error

- Measurement uncertainty definition and confidence/coverage convention.
- Bias and drift metrics.
- Short-term and long-term stability.
- Accuracy/precision under representative motion.
- Error distribution or residual series, not just a single aggregate metric.
- Conditions under which the quoted uncertainty does not hold.

### Denied/degraded-reference behavior

- Performance with GNSS unavailable.
- Performance with degraded, spoofed, or intentionally inconsistent reference inputs where tested.
- Transition behavior when GNSS/reference data disappears or returns.
- Failure detection and integrity/health indicators.
- Any dependence on preloaded maps, prior calibration, external timing, or external communications.

### Data and interface access

- Availability of raw or minimally processed sensor data.
- Availability of synchronized truth/reference data.
- Interface specification: Ethernet, serial, CAN, PTP, PPS, ROS/ROS2, NMEA, custom API, or other.
- Message schema and timestamp source.
- Replay capability for offline Worldshepherd evaluation.
- SDK/API availability and platform/OS constraints.

### Negative evidence

Worldshepherd specifically requests disclosure of:

- failed test runs
- aborted test runs
- runs excluded from published performance summaries
- sensor dropouts
- saturation events
- calibration failures
- environmental excursions
- known systematic errors
- platform-specific failure modes
- cases where a classical navigation solution outperformed the quantum-assisted solution

A partner unable to share sensitive raw data may instead provide a governed redacted/aggregated evidence package, but the omission must be declared rather than silently removed.

### Environmental and integration envelope

- Temperature, vibration, shock, magnetic, EMI/EMC, pressure/altitude and humidity ranges as applicable.
- Size, weight and power.
- Mounting/alignment requirements.
- Initialization/alignment time.
- Vehicle/platform dependencies.
- DO-160, MIL-STD, environmental or safety qualification evidence where applicable.

### Commercial, security and rights constraints

- Evaluation-unit or dataset availability.
- Lead time.
- Evaluation cost or data-license cost.
- Minimum engagement size.
- Export-control restrictions.
- Classification/CUI restrictions if relevant.
- Data-use, publication and derivative-analysis rights.
- Whether Worldshepherd may retain hashed/raw evidence for engineering provenance.
- Whether independent third-party validation is permitted.

## Minimum requested deliverables for `WS-APNT-EXT-02`

A technically useful first package should contain:

1. A named device/system identity and version.
2. A calibration identity plus certificate/report or equivalent traceability information.
3. A synchronized sensor dataset and truth/reference dataset, or controlled access sufficient to reproduce the comparison.
4. An uncertainty budget or equivalent quantified error model.
5. Observable definitions, units and sampling/update rates.
6. Configuration, firmware/software and interface identity.
7. The frozen test protocol or sufficient detail to reproduce it.
8. Known exclusions, failed/anomalous runs and limitations.
9. Environmental/test conditions.
10. Rights sufficient for Worldshepherd to retain provenance and validation artifacts.

Worldshepherd will compute its own immutable digests after receipt; partner-provided checksums are useful but do not replace Worldshepherd intake hashing.

## Evaluation sequence

### Phase A — Evidence/data qualification

1. Complete the internal simulated APNT benchmark prerequisite.
2. Obtain one partner's calibrated evidence package.
3. Normalize timestamps, frames and units without altering raw-source preservation.
4. Compute immutable raw/configuration/calibration/test-protocol identities.
5. Run the existing Worldshepherd truth-reference sensor metrics harness.
6. Quantify residuals, bias, drift, uncertainty consistency, dropout behavior and denied/degraded-reference performance.
7. Create the `ExternalEvidenceRecord` bound to `WS-APNT-EXT-02`.
8. Run structural intake.
9. Conduct separate technical review before changing evidence stage.

### Phase B — Integrated replay

For `WS-APNT-EXT-03`, replay at least two accepted calibrated records through the Worldshepherd APNT fusion/control interface, including degraded/denied-reference injections. Preserve the interface schema and fusion-algorithm identities.

### Phase C — Live hardware

For `WS-APNT-EXT-04`, connect one named calibrated quantum-sensing system to the live Worldshepherd APNT interface against a truth reference. Do not call replayed historical data a live hardware test.

### Phase D — Reproduction, HIL and field environment

Proceed only in campaign order. Repeated hardware evidence, hardware-in-loop control integration, relevant-environment trials and operational demonstration remain separate gates.

## Contact strategy

Use the following order unless availability, export/security constraints, or test access materially change:

1. **Q-CTRL first** — strongest explicit current signal for system-integration/field-trial partners.
2. **SandboxAQ in parallel** — strongest current magnetic-navigation operational dataset/comparator path.
3. **IonQ / Vector Atomic** — precision timing/inertial/PNT alternative with field-validated hardware claims.
4. **Infleqtion** — parallel inertial/timing path and useful technology-diversity comparator.

Do not ask any partner to substantiate a generic claim such as “quantum advantage.” Ask for a defined measurement package against a declared truth reference. Worldshepherd should determine performance from the returned evidence.

## Claims control

This package is an acquisition/test specification, not evidence. Current vendor statements are used only to prioritize outreach. No partner listed here has yet satisfied a Worldshepherd APNT evidence gate merely by being named, by publishing a result, or by expressing willingness to collaborate. Promotion requires actual delivered evidence, structural intake, technical validation, and sequential campaign-gate closure.
