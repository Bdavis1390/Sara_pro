# WS-FUSION-CTRL-001 — Simulator-Only Fusion Control Assurance Demonstrator

## Purpose

Establish an auditable Worldshepherd control-assurance pattern for fusion research without creating any live hardware command path.

The branch now exercises:

1. provenance-bearing diagnostic validation;
2. a demonstration optical state estimator;
3. abstract virtual-actuator proposals;
4. an independent deterministic PRIME-style safety gate;
5. SHA-256 hash-chained audit and deterministic replay;
6. strict read-only FAIR-MAST source/data validation;
7. non-mutating mapping into the existing SARA audit shape;
8. offline diagnostic fault injection;
9. estimator-consensus/disagreement handling;
10. provenance-gated external observer intake;
11. archive evidence readiness classification;
12. an explicit archive-to-control admission gate.

## Hard safety boundary

This branch intentionally contains **no**:

- EPICS machine-control client;
- CODAC/RTF machine-control integration;
- magnet power-supply driver;
- gas injection command interface;
- neutral-beam or RF-heating command interface;
- plasma-facing hardware actuator transport.

The default actuator remains `virtual_vertical_balance` in arbitrary simulator units.

## Control architecture

```text
measurement / archive source
        |
        v
provenance + validity checks
        |
        v
state estimator(s)
        |
        +---- external observer adapter (source validated only)
        |
        v
estimator consensus / disagreement gate
        |
        v
model-generated virtual proposal
        |
        v
independent PRIME-style deterministic safety gate
        |
        v
virtual actuator only
        |
        v
hash-chained audit + deterministic replay
```

Archive data has a separate claims gate:

```text
FAIR-MAST evidence -> archive readiness -> control admission
                                      |
                                      +-> analysis allowed when justified
                                      +-> control denied unless all control evidence requirements pass
```

## Core contracts

Every `SensorSample` carries timestamp, shot identity, diagnostic identity, value/unit, uncertainty, validity, quality, and provenance.

Every `PlasmaStateEstimate` carries timestamp, shot identity, displacement estimate, confidence, estimator identity, and source diagnostics.

Every `ControlProposal` carries timestamp, shot identity, virtual actuator, requested value/unit, model identity, confidence, and rationale.

## PRIME-style safety gate

The deterministic gate is independent of the proposal generator and rejects:

- non-allowlisted actuators;
- unit mismatches;
- missing model identity;
- non-finite values or invalid confidence;
- confidence below threshold;
- values outside configured bounds;
- non-monotonic command timing;
- excessive slew.

Rejected proposals receive `applied_value = null`.

## Demonstration estimator and controller

`DifferentialOpticalEstimator` uses a normalized difference between upper/lower synthetic optical-emission channels. It exists to exercise the data/control architecture and is **not** a validated plasma-position estimator.

`ProportionalVirtualActuatorController` produces an abstract correction from the demonstration displacement. It has no physical actuator semantics.

## Estimator consensus and external observers

`StateConsensusGate` requires multiple distinct estimator identities and rejects:

- insufficient estimators;
- duplicate estimator identity presented as independence;
- cross-shot estimates;
- low-confidence estimates;
- excessive estimator time skew;
- disagreement outside a configured tolerance.

The tolerance is a software policy parameter, **not** a validated plasma-physics threshold.

`ExternalObserverAdapter` does not implement magnetic or equilibrium reconstruction. It only admits an externally produced estimate when method, diagnostics, provenance, quality, confidence, estimator identity, and source validation are explicit. This creates a partner/laboratory integration point without fabricating a second physics model.

## Audit, replay, and SARA bridge

`FusionAuditLedger` creates a sequence-numbered SHA-256 hash chain over control-pipeline events.

`FusionReplayRunner` requires paired series, matching shot identity, bounded pair-time skew, and strictly increasing time. Identical inputs/configuration produce a stable evidence fingerprint; changed inputs change that fingerprint.

`fusion_audit_bridge.py` maps fusion records into SARA's existing `ts/event/actor/payload` event shape without writing the SARA audit file or invoking privileged endpoints. It rejects impersonation of `admin`, `operator`, and `SSPADAWANZZ_ADMIN`.

## FAIR-MAST source and data evidence

The pinned source manifest is:

`data/fair_mast/shot_30420_amc_manifest.json`

It identifies historical MAST shot `30420`, Level-1 group `amc`, signals `time` and `plasma_current`, and:

`s3://mast/level1/shots/30420.zarr/amc`

### Metadata-only live probe

The bounded live metadata probe confirmed directly from the STFC public archive:

- Zarr format 2;
- `time`: shape `[30000]`, dtype `<f4`, units `s`;
- `plasma_current`: shape `[30000]`, dtype `<f4`, units `kA`;
- source description: `Plasma Current and PF/TF Coil Currents`;
- upstream quality label: `Not Checked`;
- no uncertainty field observed in the probed signal attributes.

Metadata evidence is persisted at:

`evidence/fair_mast/shot_30420_amc_metadata_probe_20260912.json`

Metadata probe report SHA-256:

`ffddced3a27e0b479298e5a09203ad59bba1460dd58ef43954d0e248eb416c0b`

### Bounded real-value integrity probe

A one-shot GitHub Actions job fetched only the pinned `time/0` and `plasma_current/0` compressed chunks, decoded them according to the declared Zarr metadata, calculated hashes/statistics, and discarded the raw arrays. Raw values were **not** committed.

Evidence is persisted at:

`evidence/fair_mast/shot_30420_amc_data_probe_20260912.json`

Validated results:

- 30,000 finite time samples;
- time range approximately `-2.00000024 s` to `3.99979949 s`;
- strictly increasing time base;
- median sample interval approximately `0.000200033 s` (~5 kHz);
- 30,000 finite plasma-current samples;
- plasma-current units `kA`;
- time compressed-chunk SHA-256: `3d1f90c80e334a581dc2185e0718c4a0c26e0dddf00d1bb8898fdca46c0f8aae`;
- current compressed-chunk SHA-256: `6766652b81e6af1586222aa9f5496f61f5dcf813d810fe1e2a7f2e55025a7a64`;
- bounded paired `0–0.35 s` window: 1,750 finite pairs;
- paired-window SHA-256: `636d6da6e4f74e112789d239e45c177bc78bfc4feffe169ab1e244f49f1b5f75`;
- probe report SHA-256: `4d7823c39cca64353a35aa848542fc12b6e783377242a7f4b46dca427e552489`.

This establishes real archive reachability, decoding, time-base integrity, finite-value coverage, and reproducible content fingerprints. It does **not** establish plasma-position estimation or safe control.

## FAIR-MAST quality guard

FAIR-MAST issue #211 documented severe quantization in at least one Level-2 MAST magnetics dataset and derivative artifacts, while Level-1 raw data avoided that specific issue. `FairMastQualityPolicy` therefore blocks derivative-sensitive Level-2 magnetic-looking signals by default. This is a conservative workaround for the documented case, not a claim that every Level-2 signal is defective.

## Archive readiness and control admission

`archive_readiness.py` classifies the real shot-30420 evidence as:

- **analysis evidence eligible:** yes;
- **control evidence eligible:** no.

Current control blockers include:

- upstream quality is `Not Checked`;
- no uncertainty metadata was observed;
- real plasma-state estimation has not been validated;
- real machine control has not been validated.

`control_admission.py` enforces this distinction. Supplying an ad-hoc uncertainty or manually flipping a `control_evidence_eligible` flag is insufficient to admit the source. The additional validation blockers must also be resolved explicitly.

## Offline diagnostic fault campaign

The standard campaign verifies safe failure for:

- dropped paired sample;
- excessive timestamp skew;
- shot mismatch;
- missing provenance;
- non-finite value;
- explicit invalid-sensor flag.

These are data-integrity invariants, not plasma-physics anomaly thresholds.

## CI validation

Branch-scoped GitHub Actions uses:

- `actions/checkout@v7`;
- `actions/setup-python@v7`;
- CPython 3.11;
- pinned `pytest==9.1.1`;
- `contents: read` permissions;
- explicit Python compile gate.

At commit `a5d8f3825dc28af06d43f7c4ec3f8cfd2962b270`, the complete targeted suite reported:

```text
50 passed in 0.14s
```

The suite covers simulator control, FAIR-MAST adapter/manifest/probe, deterministic replay, SARA audit mapping, fault injection, estimator consensus, archive readiness, external-observer admission, and archive-to-control admission.

## Claims state

### IMPLEMENTED IN SOFTWARE + CI VALIDATED

- provenance-bearing simulator data contract;
- demonstration optical estimator;
- virtual controller;
- independent PRIME-style gate;
- hash-chained audit ledger;
- read-only FAIR-MAST adapters/probes;
- deterministic replay/fingerprinting;
- non-mutating SARA audit bridge;
- six-case diagnostic fault campaign;
- estimator-consensus gate;
- external-observer adapter;
- archive readiness classifier;
- archive-to-control admission gate.

### EXTERNALLY VERIFIED ARCHIVE EVIDENCE

- real FAIR-MAST shot-30420 Level-1 AMC metadata retrieved and hashed;
- real time/plasma-current chunks retrieved and decoded transiently;
- archive content hashes and statistics persisted without raw sample persistence;
- time and plasma-current arrays each contain 30,000 finite samples in this probe.

### REQUIRES FURTHER DATA/PARTNER VALIDATION

- calibration/quality interpretation beyond the archive's `Not Checked` label;
- a defensible uncertainty model supplied by source metadata, calibration evidence, or validated methodology;
- a genuine independent state estimator/observer supplied by a qualified external method or implemented and validated separately;
- comparison against authoritative plasma-state/equilibrium reconstruction;
- real state-estimation accuracy and latency validation.

### REQUIRES LAB/PARTNER VALIDATION

Any claim that Worldshepherd estimates or controls real plasma position, improves stability/confinement, suppresses ELMs, reduces heat loads, or safely commands a fusion machine.

### NOT CURRENTLY CLAIMED

- control of a real tokamak;
- improved fusion performance;
- net fusion power;
- propulsion from these effects;
- plasma shielding or unsupported macroscopic protective effects.

## Next gates

1. Obtain authoritative calibration/uncertainty/quality information for selected FAIR-MAST diagnostics instead of inventing uncertainty.
2. Attach a genuinely independent equilibrium/state observer through `ExternalObserverAdapter` and exercise disagreement handling against the demonstration estimator.
3. Extend fault injection to duplicated, delayed, contradictory, reordered, and metadata-corrupted streams.
4. Build analysis-only replay for selected real public signals where the physics mapping is justified; keep control admission closed until validation requirements are actually met.
5. Only after these gates pass, evaluate a **non-actuating, read-only EPICS-compatible telemetry adapter**.
