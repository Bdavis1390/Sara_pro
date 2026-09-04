# WS-HMAA v0.1 — High-Mach Autonomy Assurance

Status: IMPLEMENTED IN SOFTWARE (synthetic-data assurance core only)

## Purpose

WS-HMAA is a non-flight-control assurance sidecar for autonomy integrations. It is designed to observe entity/task streams, preserve provenance, evaluate assurance exceptions, and generate verifiable evidence bundles without issuing safety-critical flight commands.

The initial target is a Lattice-compatible software-in-the-loop demonstrator using simulated data. No Quarterhorse, Hermeus, Anduril proprietary, CUI, ITAR-controlled, or classified data is required for v0.1.

## System boundary

Data flow:

1. External autonomy environment emits entity, task, heartbeat, and object-integrity events.
2. `hmaa_adapter.py` normalizes external payloads into `HMAAEvent` records.
3. `hmaa.py` seals each event into a SHA-256 hash chain.
4. Assurance evaluation returns one of: `ALLOW`, `WARN`, `REVIEW`, or `INDETERMINATE`.
5. Evidence bundles are emitted only after the event chain verifies.

WS-HMAA MUST NOT:

- command flight-control surfaces;
- replace vehicle safety logic;
- infer approval when the policy engine is unavailable;
- treat a missing heartbeat as proof of vehicle failure;
- silently accept checksum failures or chronology corruption;
- publish ITAR, classified, or mission-sensitive schemas to public or non-rated registries.

## Lattice-facing integration assumptions

The public Lattice SDK documentation describes:

- streaming entity events and heartbeat events through `StreamEntities`;
- real-time task streaming through `StreamTasks`;
- simulated-data development in Lattice Sandboxes;
- SHA-256 checksums for Objects integrity;
- custom Protobuf task definitions through the Lattice Schema Registry.

WS-HMAA v0.1 intentionally avoids importing a proprietary SDK package. The adapter accepts mapping/dictionary payloads so the assurance core can be unit-tested independently and wired to REST, SSE, or gRPC clients in a later integration layer.

## Evidence schema

Primary schema identifier:

`worldshepherd.hmaa.evidence.v0.1`

Each sealed event includes:

- event and mission identifiers;
- optional entity/task identifiers;
- source and ingest timestamps;
- source payload;
- previous event hash;
- current SHA-256 event hash.

A bundle is accepted only when every event hash and chain pointer verifies and all events match the bundle mission identifier.

## Assurance semantics

| Condition | Result |
| --- | --- |
| No detected exception | `ALLOW` |
| Degraded heartbeat / duplicate requiring deduplication | `WARN` |
| Checksum failure / chronology anomaly | `REVIEW` |
| Policy engine unavailable | `INDETERMINATE` |

`INDETERMINATE` is explicitly non-approval. This preserves the Worldshepherd doctrine that failure of an assurance service must not become implicit authorization.

## SIL acceptance tests

v0.1 includes automated tests for:

1. valid chained evidence;
2. tamper detection;
3. policy-engine outage fail-closed behavior;
4. checksum failure escalation;
5. degraded-heartbeat warning;
6. entity/task normalization;
7. cross-mission evidence rejection;
8. invalid reconnect-attempt rejection.

## Next increment

WS-HMAA v0.2 should add:

- a sandbox client abstraction for entity/task streams;
- persistent local evidence storage using the existing SARA durable-store conventions;
- replay-safe deduplication keys;
- monotonic chronology checks with explicit clock-skew tolerance;
- object-checksum verification hooks;
- `/v1/hmaa/*` read-only assurance endpoints;
- fixture-driven link-loss and reconnect simulation;
- CI evidence artifact generation.

No claim of Hermeus/Anduril production integration is permitted until the sandbox integration is executed against an authorized environment and repeat-tested.

## Public technical references

- https://developer.anduril.com/guides/entities/watch
- https://developer.anduril.com/guides/tasks/integrate-an-agent
- https://developer.anduril.com/guides/developer-tools/sandboxes
- https://developer.anduril.com/guides/objects/overview
- https://developer.anduril.com/changelog/2026/7/23
