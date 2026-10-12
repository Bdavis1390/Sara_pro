# WS-LAB-INTEROP-01 G3-R0 — Physical/HIL Readiness Package

Status: PRE-PHYSICAL / HIL READINESS ONLY

This gate prepares a controlled physical bench. It does **not** claim that physical-device testing has occurred.

## Why this exists

G1 establishes bounded synthetic command/semantic/evidence behavior. G2 adds protocol/emulator robustness. G3 is the first gate that may use real hardware I/O, so the bench must be frozen before energizing devices.

The readiness model follows the current NIST digital-twin emphasis on interoperability, verification, validation, uncertainty quantification (VVUQ), traceability, and trustworthy lifecycle evidence. It also adopts the practical lesson from interoperable process analytical technology: connection alone is insufficient; data meaning, timing, calibration, model use, and control context must remain traceable.

## Mandatory pre-run manifest

Each physical/HIL run must freeze:

- two or more distinct device identities;
- channel IDs and direction;
- interface/adapter identity and version;
- measured/commanded quantity and unit;
- allowed range and safe default;
- calibration identifier and validity;
- clock source;
- uncertainty budget;
- human emergency-stop path;
- fail-safe default;
- raw and normalized measurement retention;
- configuration and evidence digests.

## VVUQ minimum

The first uncertainty budget records at least:

1. instrument accuracy;
2. repeatability;
3. quantization;
4. timing-equivalent error.

The reference implementation combines these by root-sum-square for a bounded scalar measurement. More complete physical benches may require correlated uncertainties or Monte Carlo propagation; this R0 model does not claim otherwise.

## Readiness fault injections

A physical run must be blocked when any of the following is true:

- expired/invalid calibration;
- missing emergency stop;
- missing clock provenance;
- raw measurement retention disabled;
- unsafe default command/state.

Additional G3 execution faults, once hardware is present, should include:

- sensor disconnect;
- actuator stuck-on/stuck-off;
- command saturation;
- measurement bias;
- timestamp drift;
- communications loss during partial execution;
- adapter restart;
- power interruption;
- unit/semantic mismatch.

Faults that could damage equipment or create unsafe conditions must be emulated rather than physically injected.

## G3 execution evidence

A future physical run must retain:

- pre-run manifest and configuration digest;
- operator/authorization identity;
- calibration evidence;
- raw command and normalized command;
- raw measurement and normalized measurement;
- uncertainty terms;
- state transitions;
- alarms;
- abort/recovery events;
- emergency-stop test result;
- post-run evidence digest;
- exact hardware and software versions.

## Promotion rule

G3_READY_FOR_PHYSICAL_BENCH means only that the bench contract is sufficiently complete to begin controlled hardware/HIL work.

Only an actually executed physical/HIL run can produce bounded physical evidence for the tested configuration.

No G3 readiness result establishes:
- OPC UA LADS conformance;
- SiLA 2 conformance;
- production security;
- laboratory safety certification;
- device-agnostic interoperability;
- external replication;
- partner/government acceptance.
