# ADR-0004 — Power-Beaming Assurance Boundary

- **Status:** Proposed
- **Date:** 2026-10-01
- **Owner:** Worldshepherd
- **Decision class:** Mission assurance / cyber-physical authorization / evidence custody
- **Claim state:** `IMPLEMENTED IN SOFTWARE` for the G1 reference logic; physical-system performance remains `REQUIRES LAB VALIDATION` / `REQUIRES PARTNER VALIDATION`.

## Context

Worldshepherd needs a reusable assurance pattern for heterogeneous wireless-energy systems without coupling SARA to any one transmitter technology, tracking implementation, receiver design, or spacecraft controller.

A secure communications link establishes message authenticity and confidentiality. It does not establish that a requested physical energy-delivery action is authorized under current mission policy, configuration, identity, navigation, tracking, freshness, and safety conditions.

## Decision

Worldshepherd will maintain WS-PBA as a **permission and assurance layer**, not as a beam-control or targeting subsystem.

PRIME owns bounded mission authorization. SARA owns governed workflow and state custody. ECHO records decision provenance. OVERWATCH exposes operator state. Partner adapters normalize observations and bounded requests but do not grant authority.

The G1 state model enforces that `DELIVERY_AUTHORIZED` is reachable only from `VERIFY_ONLY`. Identity, configuration, attestation, navigation, tracking, freshness, critical disagreement, and independent safety-veto conditions are checked before delivery authorization is permitted.

A configuration change invalidates the authorization context. A safety veto or loss of identity/configuration/attestation during operation produces a latched fault disposition. Navigation/tracking/freshness degradation produces a controlled ramp-down disposition.

## Consequences

### Positive

- vendor-neutral assurance semantics;
- separation of secure transport from physical-action authority;
- explicit fail-closed transition rules;
- configuration-bound authorization;
- reproducible decision evidence;
- easier software-in-the-loop and hardware-in-the-loop testing without claiming control of partner hardware.

### Costs

- partner integrations require a normalization adapter;
- mission-specific freshness and physical safety limits remain external inputs;
- G1 does not verify authorization signatures or provide replay-resistant issuance semantics;
- physical safety cannot be established by this software layer alone.

## Explicit non-goals

WS-PBA does not specify or implement beam wavelength, waveform, aperture, RF tile control, laser drive, pointing law, orbital guidance, destructive intensity, receiver design, or physical targeting algorithms.

## Validation gates

- **G1:** bounded state machine, semantic authorization checks, hash-chained evidence, negative-transition and single-fault tests.
- **G2:** cryptographic authorization verification, replay resistance, monotonic sequence policy, adapter contract, adversarial event-sequence generation.
- **G3:** software-in-the-loop compound-fault campaign and evidence completeness metrics.
- **G4:** benign low-power hardware-in-the-loop surrogate.
- **G5:** partner integration / independent physical validation.

No higher gate is implied by completion of a lower gate.
