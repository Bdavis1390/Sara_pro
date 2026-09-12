# WS-FUSION-CTRL-001 — Simulator-Only Fusion Control Demonstrator

## Purpose

Establish an auditable Worldshepherd control pattern for fusion research without creating any live hardware command path.

The demonstrator now exercises:

1. diagnostic sample validation and provenance;
2. state estimation from paired demonstration optical signals;
3. a model-generated virtual-actuator proposal;
4. an independent deterministic PRIME-style safety gate;
5. append-only hash-chained audit/replay evidence;
6. strict read-only FAIR-MAST source identity and metadata access;
7. deterministic replay with evidence fingerprints;
8. non-mutating mapping into the existing SARA audit event shape;
9. offline diagnostic fault injection and safe-failure verification.

## Safety boundary

This branch intentionally contains **no**:

- EPICS machine-control client;
- CODAC/RTF machine-control integration;
- magnet power-supply driver;
- gas injection command interface;
- neutral-beam or RF-heating command interface;
- plasma-facing hardware actuator transport.

The only actuator enabled by the default demo is `virtual_vertical_balance`, measured in arbitrary simulator units.

The FAIR-MAST client is GET-only, HTTPS-only, host-allowlisted, and provides no arbitrary-URL fetch method. Zarr array reading is deliberately kept outside the control core so archive access cannot be mistaken for actuator authority.

## Core data contract

Every `SensorSample` carries:

- timestamp;
- shot identifier;
- diagnostic identifier;
- value and unit;
- uncertainty;
- validity flag;
- quality label;
- provenance identifier.

Every state estimate carries estimator identity, confidence, and source diagnostics.
Every control proposal carries model identity, confidence, rationale, target virtual actuator, and requested value.

## PRIME-style safety gate

The deterministic gate operates independently from the proposal generator and rejects proposals when any of the following holds:

- actuator is not allowlisted;
- units do not match the configured envelope;
- model identity is missing;
- value or confidence is invalid;
- confidence is below threshold;
- command is outside min/max bounds;
- command timing is non-monotonic;
- slew rate exceeds the configured limit.

Rejected proposals receive `applied_value = null`.

## Demonstration estimator

`DifferentialOpticalEstimator` uses a normalized difference between upper and lower synthetic optical-emission channels. It exists only to exercise the control/data architecture. It is **not** represented as a validated plasma-position estimator.

## Virtual controller

`ProportionalVirtualActuatorController` generates an abstract correction from the simulated vertical displacement. It has no hardware semantics.

## Audit, replay, and SARA bridge

`FusionAuditLedger` creates a sequence-numbered SHA-256 hash chain over sensor, state, proposal, and gate-decision events. The goal is deterministic replay evidence, not cryptographic non-repudiation.

`FusionReplayRunner` requires paired series, matching shot identity, bounded pair-time skew, and strictly increasing replay time. A canonical SHA-256 fingerprint changes when replay input changes and remains stable for identical input/configuration.

`fusion_audit_bridge.py` maps fusion audit records into the existing SARA `ts/event/actor/payload` structure without writing the SARA audit file or invoking an admin endpoint. It refuses to impersonate `admin`, `operator`, or `SSPADAWANZZ_ADMIN`.

## FAIR-MAST source lane

`fair_mast_adapter.py` provides:

- a strict source identity (`FairMastSource`);
- stable source provenance for each sample index;
- GET-only host-allowlisted shot metadata access;
- conversion of already-read archive series into `SensorSample` objects;
- Level-1/Level-2 quality labels;
- a conservative quality rule that blocks derivative-sensitive Level-2 magnetics by default because upstream FAIR-MAST issue #211 documented severe quantization for at least one Level-2 magnetics case and recommended Level-1 raw data for derivative-sensitive work.

The repository pins a reproducible public source target at:

`data/fair_mast/shot_30420_amc_manifest.json`

That manifest identifies FAIR-MAST shot `30420`, Level-1 source `amc`, signals `time` and `plasma_current`, and the public Zarr location `s3://mast/level1/shots/30420.zarr/amc`.

**Important:** the manifest is source identity only. It explicitly states that no archived diagnostic values are embedded in this repository. Therefore this branch does not yet claim a completed replay of real FAIR-MAST signal arrays.

## Fault campaign

`fusion_faults.py` injects faults only into offline `SensorSample` fixtures and checks for safe failure. The standard campaign covers:

- dropped lower-channel sample;
- excessive pair timestamp skew;
- shot-identity mismatch;
- missing provenance;
- non-finite diagnostic value;
- explicit invalid-sensor flag.

These checks enforce data-integrity invariants. They are not substitutes for validated plasma-physics anomaly thresholds.

## CI validation

Branch-scoped GitHub Actions CI uses:

- `actions/checkout@v7`;
- `actions/setup-python@v7`;
- CPython 3.11;
- pinned `pytest==9.1.1`;
- `contents: read` workflow permissions;
- an explicit Python compile gate before tests.

At commit `bf33f96d367668b1d0ada3bc07e03a887581310d`, the complete targeted suite reported:

```text
29 passed in 0.09s
```

The successful suite covers simulator control, FAIR-MAST adapter/source manifest, deterministic replay, SARA audit mapping, and the diagnostic fault campaign.

## Run the simulator

From the repository root on this branch:

```bash
PYTHONPATH=. python scripts/run_fusion_control_demo.py
```

Expected result: one accepted or rejected virtual-actuator decision plus `ledger_ok: true` when the chain is intact.

## Run the targeted tests

```bash
python -m pytest -q \
  tests/test_fusion_control.py \
  tests/test_fair_mast_adapter.py \
  tests/test_fair_mast_manifest.py \
  tests/test_fusion_replay.py \
  tests/test_fusion_audit_bridge.py \
  tests/test_fusion_faults.py
```

## Claims state

### IMPLEMENTED IN SOFTWARE + CI VALIDATED

- provenance-bearing simulator data contract;
- demonstration differential estimator;
- virtual controller;
- independent deterministic PRIME-style gate;
- hash-chained audit ledger;
- strict read-only FAIR-MAST source adapter;
- FAIR-MAST source manifest and quality guard;
- deterministic replay/fingerprint engine;
- non-mutating SARA audit bridge;
- six-case diagnostic fault campaign.

### SUPPORTED BY EXTERNAL SOURCE EVIDENCE

- FAIR-MAST exposes historical MAST metadata/data for research;
- upstream examples identify the shot-30420 Level-1 AMC path and `plasma_current` signal;
- upstream issue #211 documents Level-2 magnetics quantization risk relevant to derivative-sensitive analysis.

### REQUIRES DATA VALIDATION

- retrieval and checksum/provenance capture of actual FAIR-MAST arrays;
- replay against those retrieved arrays;
- verification of units, calibration, signal quality, time bases, missing values, and diagnostic-specific metadata;
- comparison against an independent state-estimation method.

### REQUIRES LAB/PARTNER VALIDATION

Any claim that Worldshepherd estimates or controls real plasma position, improves stability/confinement, suppresses ELMs, reduces heat loads, or safely commands a fusion machine.

### NOT CURRENTLY CLAIMED

- control of a real tokamak;
- improved fusion performance;
- net fusion power;
- propulsion from these control effects;
- plasma shielding or other unsupported macroscopic protective effects.

## Next gates

1. Acquire a bounded real FAIR-MAST diagnostic slice with exact archive provenance and content hash; keep it read-only.
2. Validate units, time base, calibration/quality metadata, and missing-value behavior before replay.
3. Replay that recorded public slice through the evidence pipeline and capture a deterministic report.
4. Add an independent second estimator/observer and explicit disagreement handling.
5. Expand fault injection to delayed, duplicated, contradictory, and metadata-corrupted streams using justified invariants.
6. Only after those gates pass, evaluate a **non-actuating** EPICS-compatible telemetry adapter.
