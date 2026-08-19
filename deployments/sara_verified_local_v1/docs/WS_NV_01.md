# WS-NV-01 — NVIDIA Physical-AI Integration Contract

Status: **IMPLEMENTED IN SOFTWARE — CONTRACT ONLY**  
NVIDIA runtime status: **NOT VERIFIED**  
External network execution: **DISABLED BY DEFAULT**

## Purpose

WS-NV-01 defines the evidence-governed boundary between Worldshepherd SARA and selected NVIDIA physical-AI surfaces. It intentionally does not claim that CUDA, Jetson, Isaac Sim, Omniverse, or NVIDIA hardware is installed, connected, benchmarked, or validated.

The initial contract maps four integration surfaces:

| Surface | Boundary | Intended use | Current claim |
|---|---|---|---|
| Omniverse Kit | headless app / microservice | digital twins and simulation events | REQUIRES PARTNER VALIDATION |
| Isaac Sim | ROS 2 bridge | robotics simulation, synthetic data, control-loop exchange | REQUIRES LAB VALIDATION |
| Jetson Platform Services | API services | edge-AI orchestration and telemetry | REQUIRES LAB VALIDATION |
| CUDA | future compute backend | approved accelerated workloads | REQUIRES LAB VALIDATION |

## Why these boundaries

NVIDIA documents Omniverse Kit as a modular SDK that can support headless microservices as well as full applications. Isaac Sim exposes a ROS 2 bridge for robotics integration. Jetson Platform Services provides modular API-driven services for edge AI. Those interfaces allow SARA governance, authorization, telemetry provenance, and evidence capture to remain separate from vendor-specific runtime execution.

Official references:

- https://docs.omniverse.nvidia.com/dev-guide/latest/kit-architecture.html
- https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/ros2_landing_page.html
- https://developer.nvidia.com/embedded/jetpack/jetson-platform-services-get-started

## Promotion gate

No NVIDIA capability is promoted to VALIDATED until the evidence package contains, at minimum:

1. Runtime and SDK version inventory.
2. Reproducible configuration digest.
3. Successful bounded interface test.
4. Telemetry and decision-provenance capture.
5. Failure and degraded-state behavior.
6. Operator authorization record.

## Planned demonstrations

### NV-D1 — Simulation-to-Evidence

Omniverse/Isaac simulation event -> bounded adapter -> SARA workflow -> authorization -> provenance -> evidence record.

### NV-D2 — Governed Edge Autonomy

Jetson service event -> local policy gate -> telemetry/provenance -> degraded-state test -> operator override/recovery evidence.

### NV-D3 — Mission Digital Twin

Distributed simulated sensors/autonomous nodes -> digital-twin state -> decision-support workflow -> configuration custody -> after-action evidence.

## Next implementation increments

- WS-NV-01A: expose a read-only SARA integration-status endpoint.
- WS-NV-01B: add signed/config-digested evidence envelopes for simulation events.
- WS-NV-01C: create an Omniverse Kit headless adapter proof-of-interface.
- WS-NV-01D: create an Isaac Sim ROS 2 bridge proof-of-interface.
- WS-NV-01E: create a Jetson Platform Services proof-of-interface on approved hardware.

Until those increments are executed and verified, the integration remains a contract scaffold rather than a demonstrated NVIDIA runtime capability.
