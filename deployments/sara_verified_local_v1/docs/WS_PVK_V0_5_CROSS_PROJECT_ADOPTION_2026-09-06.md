# Worldshepherd PVK v0.5 Cross-Project Adoption

**Status:** implementation candidate on a controlled branch; not merged or runtime-verified.

## Purpose

PVK v0.5 converts WS-PHYS.1.0 / WS-PHYS-REG.1.0 / WS-PHYS-SARA.1.0 into executable, backward-compatible software primitives. It does not elevate technical maturity, authorize hazardous testing, or convert speculative physics into operational claims.

## Core integration

- **SARA:** owns `PhysicsVerificationRecord`, deterministic evidence scoring, claims lint, and audit-ready outputs.
- **PRIME SENTINEL:** consumes PVK hard-gate results before external release or hardware authorization.
- **ECHO SENTINEL LINK:** supplies source, calibration, timing, environment, raw-data digest, and provenance records.
- **OVERWATCH:** should display validation state, replication state, unresolved confounders, convergence state, blocked claims, and pending independent review.

## Cross-project application matrix

The machine-readable matrix in `fixtures/worldshepherd_physics_project_matrix_v1.json` applies PVK controls to SARA, PRIME SENTINEL, OVERWATCH, ECHO SENTINEL LINK, WS-AlTi, adaptive metasurfaces, TIDELENS/Specular MIST, AEROSHEPHERD, HELIOS-LINK, ion propulsion, resonance research, energy storage, BAROS, Stegriage, WS-LAB/Boone, and the Revenue Engine.

## Invariants

1. A high evidence score never means “new physics confirmed.”
2. P4 / beyond-Standard-Model records must explicitly account for energy and momentum conservation and remain blocked from release without independent replication and governance approval.
3. Simulation claims require equations/model identity, boundary conditions, solver/version, convergence metadata, digests, and uncertainty or sensitivity treatment.
4. Physical-test claims require setup identity, calibrated instrumentation when applicable, raw-data digests, environment, operator, and failure/off-nominal review.
5. Independent-validation claims require completed independent review, independent evidence reference, and CRE1AWS approval.
6. Claims above C3 require an evidence package, audit event, and CRE1AWS approval.
7. Existing non-physics records remain valid; this patch is additive and does not silently upgrade historical maturity.

## PVK v0.5 hypothesis competition

The v0.5 operating model preserves multiple candidate explanations and chooses future tests by discriminatory value rather than by how strongly a test appears likely to support the favored hypothesis. Initial hard gates prioritize conventional-force, thermal, electromagnetic, mechanical, sensor, calibration, and provenance explanations before P4 escalation.

## Implementation boundary

This branch is a code-level implementation candidate only. Merge, live migration, runtime endpoint wiring, persistent-store migration, OVERWATCH UI integration, and any maturity increase remain separate acceptance gates. The existing pre-change backup/restore and runtime-verification requirements remain controlling.
