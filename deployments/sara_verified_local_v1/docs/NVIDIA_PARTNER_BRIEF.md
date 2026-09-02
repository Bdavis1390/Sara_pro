# Worldshepherd × NVIDIA — Partner Technical Brief

## Executive proposition

Worldshepherd is building an evidence-governed control and validation layer for physical AI: the layer between simulation, autonomous/agentic decisions, edge execution, and operational evidence.

The NVIDIA-facing question is narrow:

> Can Worldshepherd provide a reusable governance, provenance, authorization, degraded-state testing, and evidence layer around NVIDIA physical-AI workflows without constraining the underlying NVIDIA runtime?

WS-NV-01 is the current proof package. The software contracts are implemented and repository-tested. NVIDIA runtimes and hardware are deliberately **not** claimed as validated yet.

## Why NVIDIA

Current NVIDIA public material aligns directly with the workstream:

- NVIDIA Inception supports startups building on the NVIDIA ecosystem, including companies that are not yet using NVIDIA GPUs or SDKs; formal membership requires official incorporation and other published eligibility criteria.
- NVIDIA Federal positions Omniverse for training/simulation and digital twins, and Jetson for autonomous machines at the tactical edge.
- NVIDIA's physical-AI stack spans Omniverse, Isaac, Jetson, Cosmos, accelerated computing, and partner ecosystems.

Official references:

- https://www.nvidia.com/en-us/startups/
- https://www.nvidia.com/en-us/industries/government/federal/
- https://nvidianews.nvidia.com/news/japans-robotics-and-manufacturing-leaders-build-on-nvidia-cosmos-to-advance-physical-ai-frontier

## What is implemented today

Repository: https://github.com/Bdavis1390/Sara_pro

Review package: https://github.com/Bdavis1390/Sara_pro/pull/12

### WS-NV-01 through WS-NV-01G

1. **Integration manifest and claims gates** — declares Omniverse Kit, Isaac Sim/ROS 2, Jetson Platform Services, and CUDA boundaries.
2. **Authenticated status endpoint** — read-only SARA status surface with no NVIDIA calls and no application-audit mutation.
3. **Configuration-digested evidence envelopes** — deterministic SHA-256 digests without retaining raw runtime configuration.
4. **Omniverse proof-of-interface contract** — versioned headless-service request/response and offline parser.
5. **Isaac Sim ROS 2 observation contract** — captures bridge version, ROS distribution, simulation state, topics/services, and correlation.
6. **Jetson Platform Services observation contract** — captures service identity, JetPack/JPS versions, API operations, status, and correlation.
7. **CUDA compute observation contract** — captures driver/toolkit/device/compute-capability metadata plus workload/result digests.
8. **Promotion-readiness gate** — complete evidence can become ready for human review, but software cannot auto-promote a capability to VALIDATED.

The branch is covered by the existing SARA compile/test/Compose/deployment gate. Passing that gate validates the Worldshepherd software boundary only.

## Current claims state

| Surface | Worldshepherd software contract | NVIDIA runtime/hardware state |
|---|---|---|
| Omniverse Kit | IMPLEMENTED IN SOFTWARE | REQUIRES PARTNER VALIDATION |
| Isaac Sim ROS 2 | IMPLEMENTED IN SOFTWARE | REQUIRES LAB VALIDATION |
| Jetson Platform Services | IMPLEMENTED IN SOFTWARE | REQUIRES LAB VALIDATION |
| CUDA acceleration | IMPLEMENTED IN SOFTWARE | REQUIRES LAB VALIDATION |

No outbound NVIDIA client, vendor credential, GPU control path, ROS client, Jetson hardware claim, or Omniverse runtime claim is hidden inside the current implementation.

## Three bounded demonstrations

### NV-D1 — Simulation to Evidence

Omniverse/Isaac event → bounded integration contract → SARA authorization/workflow → telemetry and decision provenance → evidence envelope → human review gate.

**Partner ask:** approved Omniverse/Isaac environment plus a technical reviewer for the interface contract.

### NV-D2 — Governed Edge Autonomy

Jetson Platform Service event → local policy gate → telemetry/provenance → degraded-state exercise → operator override/recovery evidence.

**Partner ask:** approved Jetson test environment and guidance on the most appropriate Platform Service for a first bounded demonstration.

### NV-D3 — Accelerated Evidence Workload

Small deterministic CUDA workload → runtime/device inventory → workload digest → execution → result digest → repeatability comparison → evidence package.

**Partner ask:** approved GPU/CUDA environment and confirmation that the selected workload is a useful minimal integration proof.

## Runtime validation packages already opened

- LAB-NV-01 — Omniverse + Isaac runtime validation: https://github.com/Bdavis1390/Sara_pro/issues/13
- LAB-NV-02 — Jetson + CUDA hardware validation: https://github.com/Bdavis1390/Sara_pro/issues/14

## What we are asking NVIDIA for

The preferred first engagement is technical routing, not investment:

1. Identify the best technical owner for an Omniverse/physical-AI integration review.
2. Confirm whether the WS-NV-01 contract boundaries are sensible for NVIDIA's current platform direction.
3. Select one bounded runtime demonstration and an approved environment.
4. Review the resulting evidence package before any capability claim is promoted.

If the technical fit is established, subsequent discussions can address ecosystem participation, public-sector alignment, Inception eligibility after incorporation requirements are met, and broader partnership opportunities.

## Governance boundary

Worldshepherd follows a simple operational rule:

**AI proposes → human approves → automation remains bounded → actions and evidence are logged.**

For NVIDIA integration specifically:

**Software completeness is not runtime validation. Runtime evidence is not claim promotion. Claim promotion requires explicit human review.**
