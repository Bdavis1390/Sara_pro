# WS-NV-01 — NVIDIA Physical-AI Integration Contract

Status: **IMPLEMENTED IN SOFTWARE — CONTRACT + STATUS/EVIDENCE + VENDOR INTERFACE PRIMITIVES**  
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

NVIDIA documents Omniverse Kit as a modular SDK that can support headless microservices as well as full applications. The current Omniverse services stack uses Kit and exposes standards-oriented service primitives around FastAPI/OpenAPI and Pydantic. Isaac Sim exposes a ROS 2 bridge for robotics integration, with publishers, subscribers, and services active during simulation playback. Jetson Platform Services provides modular, API-driven services for edge AI, including REST-based AI-service operations. Those interfaces allow SARA governance, authorization, telemetry provenance, and evidence capture to remain separate from vendor-specific runtime execution.

Official references:

- https://docs.omniverse.nvidia.com/dev-guide/latest/kit-architecture.html
- https://docs.omniverse.nvidia.com/services/latest/core/index.html
- https://docs.isaacsim.omniverse.nvidia.com/latest/py/source/extensions/isaacsim.ros2.bridge/docs/index.html
- https://developer.nvidia.com/embedded/jetpack/jetson-platform-services-get-started
- https://docs.nvidia.com/moj/inference-services/overview.html

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

Worldshepherd defines a versioned request/response contract for a future headless Omniverse Kit service. It includes a bounded `interface_probe` request, structured response metadata, offline parsing and correlation checks, and evidence-envelope creation. A captured response that parses successfully remains `REQUIRES_PARTNER_VALIDATION`; no SARA network client or Omniverse service is implemented by this increment.

### WS-NV-01D — Isaac Sim ROS 2 proof-of-interface

Worldshepherd defines a captured-observation contract for the Isaac Sim ROS 2 bridge. The record includes bridge version, ROS distribution, simulation state, observed topics, observed services, and correlation ID. The assessment only marks bridge activity as observed when simulation state is `playing` and at least one topic or service is present. It still returns `runtime_validated: false` and retains `REQUIRES_LAB_VALIDATION`.

No ROS client is implemented and no Isaac Sim runtime is claimed present.

### WS-NV-01E — Jetson Platform Services proof-of-interface

Worldshepherd defines an offline observation contract for a future Jetson Platform Services integration. The record captures service identity/type, JetPack version, Platform Services version, containerization state, service status, observed API operations, and correlation ID. Captured API metadata can be parsed and wrapped in a configuration-digested evidence envelope, but this does not validate Jetson hardware or software.

No outbound REST client is implemented and no Jetson device is claimed present. Hardware-backed proof remains required before the Jetson surface can move beyond `REQUIRES_LAB_VALIDATION`.

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

- WS-NV-01F: add evidence-envelope signing and verification with explicit key-custody rules.
- WS-NV-01G: define a CUDA compute-backend proof contract without importing CUDA or claiming GPU availability.
- WS-NV-01H: implement outbound vendor clients only after endpoint authentication, transport security, allowlisting, bounded failure semantics, and operator approval are defined.
- LAB-NV-01: execute the contracts against approved Omniverse/Isaac and Jetson environments and collect reproducible evidence.

Until runtime-specific increments are executed against actual NVIDIA runtimes and reproducible evidence is captured, NVIDIA capability remains unverified even though the Worldshepherd integration contracts, authenticated status surface, evidence-envelope primitives, and vendor wire contracts are implemented in software.
