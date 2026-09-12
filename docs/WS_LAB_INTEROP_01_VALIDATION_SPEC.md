# WS-LAB-INTEROP-01 — Laboratory Interoperability Validation Specification

Status: PRE-PHYSICAL / IMPLEMENTATION SPECIFICATION

Base branch SHA: `4dbddaa148f9fa5cb98abf2cbf316002e69ca4c3`

## Purpose

Define a bounded, claims-controlled validation path for connecting SARA/PRIME/ECHO/OVERWATCH to heterogeneous laboratory devices through standards-oriented adapters. This document does not claim a live OPC UA LADS, SiLA 2, physical-device, production-security, certification, or partner integration.

## Core distinction

Interoperability is scored as three independent properties:

1. `I_C` — Command interoperability: authorized commands reach the intended device/function and state transition.
2. `I_S` — Semantic interoperability: units, identities, state, calibration context, timestamps, and result meaning remain consistent across interfaces.
3. `I_E` — Evidence interoperability: an independent reviewer can reconstruct who/what issued a command, which configuration/version executed, what device state changed, what result/alarm occurred, and how recovery or abort proceeded.

A pass in one dimension cannot substitute for another.

## Minimum architecture

`SARA -> PRIME -> adapter -> device -> adapter -> ECHO -> OVERWATCH`

Minimum bench/synthetic topology:
- two logically distinct devices;
- at least two different interface/adapter profiles;
- one standards-oriented path using OPC UA LADS and/or SiLA 2 where technically practical;
- immutable configuration/version identifiers;
- time-stamped command, state-transition, result, alarm, and recovery records;
- explicit human override/abort path.

Synthetic device doubles are allowed for the first implementation gate, but must be labeled `SIMULATED_ONLY` and cannot satisfy the physical-device gate.

## Required fault-injection set

F1. interface version drift
F2. dropped telemetry
F3. stale device state
F4. malformed command
F5. sensor/result disagreement
F6. device unavailable/offline
F7. unit mismatch or incompatible semantic dictionary
F8. timestamp skew/reordering
F9. duplicate/replayed command
F10. partial execution followed by communication loss

## Required observations

For each run retain:
- run ID and qualification version;
- actor/role and authorization decision;
- source command and normalized command;
- adapter/protocol/profile version;
- device identity and function identity;
- pre-state and post-state;
- timestamps and clock source where known;
- units and semantic dictionary/version;
- raw result plus normalized result;
- alarm/error class;
- abort/recovery decision;
- recovery outcome;
- configuration and evidence digests;
- missing-data markers rather than silent omission.

## Metrics

### Command interoperability
- command success rate under valid conditions;
- wrong-target/wrong-function rate;
- authorization enforcement rate;
- duplicate/replay rejection rate;
- median and tail command latency.

### Semantic interoperability
- unit/context preservation rate;
- semantic mismatch detection rate;
- stale-state detection rate;
- timestamp-ordering correctness;
- normalization/reconstruction error where numeric transformations occur.

### Evidence interoperability
- provenance completeness;
- state-transition reconstruction completeness;
- alarm/failure attribution completeness;
- configuration/version traceability;
- independent-review reconstruction success.

### Safety/recovery
- fail-safe halt rate for unsafe/ambiguous conditions;
- autonomous recovery success rate for bounded recoverable faults;
- false recovery rate;
- time-to-safe-state;
- human override success rate.

## Initial gates

### G0 — Contract readiness
Pass only when command/state/result schemas, units, versions, authorization roles, abort rules, and evidence fields are frozen for the test version.

### G1 — Synthetic two-device execution
Use two deterministic device doubles through distinct adapters. Pass requires correct command routing, semantic preservation, evidence reconstruction, and fail-closed behavior for F1–F10. Capability remains `SIMULATED_ONLY`.

### G2 — Protocol/adapter robustness
Introduce real protocol stacks or validated protocol emulators, version skew, retries, timeout behavior, and adapter restart. Pass does not establish physical-device behavior.

### G3 — Physical bench
Connect at least two non-safety-critical physical laboratory devices or instrument simulators with hardware I/O. Repeat the fixed protocol and fault suite where safe. This can establish bounded `REQUIRES LAB VALIDATION` evidence only for the tested devices/configuration.

### G4 — External blind execution
An evaluator outside the development process runs the frozen protocol using evaluator-controlled configuration and records mandatory assertions.

## Claims boundary

Allowed before G3:
- `laboratory interoperability architecture implemented/tested in software` if actually implemented and reproduced;
- `simulated command/semantic/evidence interoperability` for the exact G1/G2 harness.

Prohibited before physical evidence:
- `validated laboratory integration`;
- `device-agnostic interoperability`;
- `OPC UA/SiLA compliant` without applicable conformance evidence;
- `production secure`;
- `safe autonomous laboratory`;
- `certified`, `NIST compliant`, or partner/government validated.

## Failure disposition

Any failure must be classified as one or more of:
- authorization failure;
- command-routing failure;
- protocol/transport failure;
- semantic/units failure;
- device-state failure;
- timing/order failure;
- evidence/provenance failure;
- recovery/abort failure;
- test-harness defect.

Unknown failures remain `UNRESOLVED`; they are not automatically attributed to the device or adapter.

## Promotion rule

A higher interoperability claim is allowed only when the corresponding `I_C`, `I_S`, and `I_E` evidence all meet the declared gate for the exact tested configuration. Overall interoperability maturity is limited by the weakest of the three dimensions.

`I_overall = min(I_C, I_S, I_E)`

This is a Worldshepherd governance rule, not an external standard.
