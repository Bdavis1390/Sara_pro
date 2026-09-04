# WS-HMAA v0.4 — Public Lattice Contract Harness

Status: IMPLEMENTED IN SOFTWARE / PUBLIC-CONTRACT SYNTHETIC VALIDATION ONLY

## Objective

WS-HMAA v0.4 creates a credentials-free interoperability preparation layer around the public Lattice REST streaming contract. It does not connect to a Lattice deployment and does not add publish, task-create, task-status, manual-control, or vehicle-control operations.

The purpose is to make external sandbox validation a narrow evidence exercise instead of a first-time integration effort.

## Public contract basis

The implementation is based on public Lattice documentation current as of 2026-09-04:

- `POST /api/v1/entities/stream` is a one-way SSE stream that returns entity or heartbeat messages and supports `heartbeatIntervalMS`, `preExistingOnly`, `componentsToInclude`, and optional filtering.
- `POST /api/v1/tasks/stream` is an SSE task-update stream that returns task-event or heartbeat messages. Its public request contract includes `heartbeatIntervalMs`, `rateLimit`, `excludePreexistingTasks`, and optional filters.
- A nonzero task `rateLimit` must be at least 250 ms.
- `parentTaskId` is mutually exclusive with `updateStartTime`, `assignee`, `statusFilter`, and `taskType`.
- Lattice Sandboxes is documented as a secure isolated simulated-data environment for development and testing.

References:

- https://developer.anduril.com/reference/rest/entities/stream-entities
- https://developer.anduril.com/reference/rest/tasks/stream-tasks
- https://developer.anduril.com/guides/developer-tools/sandboxes

## Added software boundary

`hmaa_lattice_contract.py` adds:

- request-contract validation for the public entity and task stream fields used by WS-HMAA;
- one-of envelope validation for heartbeat/entity and heartbeat/task-event responses;
- deterministic SHA-256 source-event identities so replay detection survives reconnects;
- normalization into the existing `HMAAEvent` evidence model;
- a runtime-checkable `LatticeReadTransport` protocol containing only `stream_entities` and `stream_tasks`.

There is deliberately no concrete HTTP client and no credential handling in v0.4.

## Interoperability evidence replay

`hmaa_interop.py` replays public-contract-shaped synthetic messages through:

1. contract parsing;
2. HMAA replay/chronology assurance state;
3. SHA-256 event sealing;
4. evidence-bundle verification;
5. an interoperability manifest.

The manifest records:

- the public contract version;
- a source label;
- fixture SHA-256;
- event/disposition counts;
- final evidence-chain hash;
- `live_environment_validated=false`.

That last field is intentional and must remain false until an authorized external environment is actually exercised.

## Acceptance boundary

Passing v0.4 demonstrates that Worldshepherd can validate and normalize synthetic messages shaped to the documented public stream contract. It does **not** demonstrate:

- possession of Lattice credentials;
- access to Lattice Sandboxes;
- successful authentication;
- live SSE/gRPC connectivity;
- production Lattice interoperability;
- Hermeus Quarterhorse integration;
- flight-control, task-execution, or weapons authority.

The next evidence tier is an authorized Lattice Sandbox read-only connection using separately provisioned credentials and captured interoperability evidence. No production claim is permitted before that test is repeatable.
