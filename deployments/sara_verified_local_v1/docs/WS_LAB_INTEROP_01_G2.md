# WS-LAB-INTEROP-01 G2 — Protocol/Adapter Robustness

Status: IMPLEMENTATION UNDER REVIEW / SIMULATED_ONLY

Base: current protected `main` at branch creation time.

## Purpose

Advance WS-LAB-INTEROP-01 beyond deterministic device doubles into bounded protocol-stack emulation without claiming physical laboratory-device integration or standards conformance.

## Implemented fault classes

- profile/version skew;
- one-shot timeout with bounded retry;
- adapter restart followed by explicit state resynchronization;
- malformed packet rejection;
- connection churn with fail-safe termination;
- semantic dictionary/unit drift;
- duplicate/replayed command rejection.

## Evidence

Each case records the input packet, protocol profiles, attempts, disposition, recovery state, semantic integrity state, replay disposition, and SHA-256 configuration/evidence digests.

## Gate

G2 passes only when:
1. nominal protocol execution succeeds;
2. timeout and restart faults recover only through bounded documented paths;
3. unsafe or ambiguous version/schema/connection/semantic states fail closed;
4. replay is rejected;
5. evidence remains reconstructable and hash-bound.

## Claims boundary

A passing G2 establishes only software/protocol-emulator evidence for the exact harness.

It does not establish:
- physical-device interoperability;
- OPC UA LADS conformance;
- SiLA 2 conformance;
- production security;
- laboratory safety certification;
- partner/government validation;
- external blind replication.

G3 remains the first physical/HIL gate.
