# WS-NV-01 — NVIDIA Physical-AI Integration Contract

Status: **IMPLEMENTED IN SOFTWARE — CONTRACT + STATUS/EVIDENCE + OMNIVERSE INTERFACE PRIMITIVES**  
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

NVIDIA documents Omniverse Kit as a modular SDK that can support headless microservices as well as full applications. The current Omniverse services stack uses Kit and exposes standards-oriented service primitives around FastAPI/OpenAPI and Pydantic. Isaac Sim exposes a ROS 2 bridge for robotics integration. Jetson Platform Services provides modular API-driven services for edge AI. Those interfaces allow SARA governance, authorization, telemetry provenance, and evidence capture to remain separate from vendor-specific runtime execution.

Official references:

- https://docs.omniverse.nvidia.com/dev-guide/latest/kit-architecture.html
- https://docs.omniverse.nvidia.com/services/latest/core/index.html
- https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/ros2_landing_page.html
- https://developer.nvidia.com/embedded/jetpack/jetson-platform-services-get-started

## Implemented increments

### WS-NV-01A — Authenticated read-only status

SARA exposes `GET /v1/integrations/nvidia/status` behind existing bearer-token authentication. Relay and admin roles can read the endpoint. The endpoint performs no NVIDIA calls and does not append to the application audit store.

The returned status includes:

- integration and architecture version;
- explicit `runtime_verified: false` and `network_calls_enabled: false` values;
- current claim status for each NVIDIA surface;
- deterministic SHA-256 digest of the integration contract;
- evidence-envelope schema version.

### WS-NV-01B — Configuration-digested evidence envelopes

The integration package can create evidence envelopes for declared NVIDIA surfaces. An envelope records the integration ID, surface, inherited claim state, evidence references, optional operator-authorization reference, timestamp, and deterministic SHA-256 digest of a JSON-compatible configuration.

The raw configuration is deliberately not stored in the envelope. Creating an envelope does not validate a runtime and cannot silently promote a surface claim.

**Current limitation:** envelopes are configuration-digested but not cryptographically signed. Signing remains a future custody/integrity increment and must not be claimed as implemented.

### WS-NV-01C — Omniverse headless proof-of-interface

Worldshepherd now defines a versioned request/response contract for a future headless Omniverse Kit service. The contract specifies:

- a bounded `interface_probe` request with correlation ID and requested capabilities;
- a structured response with service identity, Kit version, service state, extension versions, and observed capabilities;
- offline parsing and correlation checks;
- creation of a configuration-digested evidence envelope after parsing;
- explicit preservation of `REQUIRES_PARTNER_VALIDATION` even when a captured response parses successfully.

No SARA network client is implemented in this increment. No Omniverse service is implemented in this repository. A conforming captured JSON payload therefore proves only interface compatibility, not provenance or a functioning NVIDIA runtime.

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

- WS-NV-01D: create an Isaac Sim ROS 2 bridge proof-of-interface.
- WS-NV-01E: create a Jetson Platform Services proof-of-interface on approved hardware.
- WS-NV-01F: add evidence-envelope signing and verification with explicit key-custody rules.
- WS-NV-01G: implement an outbound Omniverse service client only after endpoint authentication, transport security, allowlisting, failure semantics, and operator approval are defined.

Until runtime-specific increments are executed against an actual NVIDIA runtime and reproducible evidence is captured, NVIDIA capability remains unverified even though the Worldshepherd integration contract, authenticated status surface, evidence-envelope primitives, and Omniverse wire contract are implemented in software.
