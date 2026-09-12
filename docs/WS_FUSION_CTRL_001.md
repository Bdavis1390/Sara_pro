# WS-FUSION-CTRL-001 — Simulator-Only Fusion Control Demonstrator

## Purpose

Establish an auditable Worldshepherd control pattern for fusion research without creating any live hardware command path.

The demonstrator exercises:

1. diagnostic sample validation and provenance;
2. state estimation from paired optical signals;
3. a model-generated virtual-actuator proposal;
4. an independent deterministic safety gate;
5. append-only hash-chained audit/replay evidence.

## Safety boundary

This branch intentionally contains **no**:

- EPICS client;
- CODAC/RTF machine-control integration;
- magnet power-supply driver;
- gas injection command interface;
- neutral-beam or RF-heating command interface;
- plasma-facing hardware actuator transport.

The only actuator name enabled by the default demo is `virtual_vertical_balance`, measured in arbitrary simulator units.

## Data contract

Every sensor sample carries:

- timestamp;
- shot identifier;
- diagnostic identifier;
- value and unit;
- uncertainty;
- validity flag;
- quality label;
- provenance identifier.

Every state estimate carries the estimator identity, confidence, and source diagnostics.
Every control proposal carries its model identity, confidence, rationale, target virtual actuator, and requested value.

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

## Current estimator

`DifferentialOpticalEstimator` uses a normalized difference between upper and lower synthetic optical-emission channels. It exists only to exercise the control/data architecture. It is **not** represented as a validated plasma-position estimator.

## Current controller

`ProportionalVirtualActuatorController` generates a bounded virtual correction from the simulated vertical displacement. It has no hardware semantics.

## Audit and replay

`FusionAuditLedger` creates a sequence-numbered SHA-256 hash chain over sensor, state, proposal, and gate-decision events. The v0.1 goal is deterministic replay evidence, not cryptographic non-repudiation.

## Run

From the repository root on this branch:

```bash
PYTHONPATH=. python scripts/run_fusion_control_demo.py
```

Expected result: one accepted or rejected virtual-actuator decision plus `ledger_ok: true` when the chain is intact.

## Test

```bash
PYTHONPATH=. pytest -q tests/test_fusion_control.py
```

The tests cover:

- valid bounded command acceptance;
- invalid-sensor rejection;
- out-of-bounds command rejection;
- low-confidence rejection;
- unknown-actuator rejection;
- audit-chain tamper detection.

## External interoperability target

The next data-side adapter should ingest public FAIR-MAST metadata and diagnostic arrays into the same `SensorSample` contract while preserving source, quality, and uncertainty metadata. Public FAIR-MAST currently exposes historical MAST campaigns through a JSON API and Zarr/S3 diagnostic storage; MAST-U live-machine control is outside this demonstrator.

## Claims state

- **IMPLEMENTED IN SOFTWARE:** simulator data contract, differential demonstration estimator, virtual controller, deterministic safety gate, hash-chained audit ledger, unit tests.
- **REQUIRES EXECUTION VALIDATION:** test results on this new branch until CI/local execution is confirmed.
- **SUPPORTED BY LITERATURE / EXTERNAL DEMONSTRATION:** machine-learning-assisted plasma control, diagnostics, and real-time control patterns used as architectural references.
- **REQUIRES LAB VALIDATION:** any Worldshepherd plasma-control claim involving actual fusion hardware.
- **NOT CURRENTLY CLAIMED:** improved confinement, ELM suppression, net fusion power, propulsion, shielding, or safe control of a real tokamak.

## Next gates

1. Execute tests and capture results.
2. Add FAIR-MAST read-only ingestion adapter and data-quality checks.
3. Add deterministic replay from recorded public data.
4. Integrate audit events with the existing SARA audit schema without weakening the existing admin/operator separation.
5. Only after those gates pass, evaluate a non-actuating EPICS-compatible telemetry adapter.
