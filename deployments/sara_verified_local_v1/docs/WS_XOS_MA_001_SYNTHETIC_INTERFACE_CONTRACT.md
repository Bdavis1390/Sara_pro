# WS-XOS-MA-001 Synthetic Interface Contract

## Status

**Claims state:** SIMULATED ONLY / INTERNAL SOFTWARE EVIDENCE.

This document defines a Worldshepherd-owned, vendor-neutral preparation harness for a possible future XTEND Certified technical evaluation. It is **not** an XTEND/XOS API contract, ICD, connector specification, certification artifact, partner validation, or evidence of platform interoperability.

No content in this contract is derived from non-public XTEND technical documentation. Partner-specific mappings remain blocked until the applicable NDA, export-control declaration, authoritative interface documentation, and partner validation gates are complete.

## Objective

Prepare SARA / PRIME SENTINEL / ECHO SENTINEL LINK / OVERWATCH integration behavior against a neutral event envelope so that later partner-approved mappings can be scoped without redesigning Worldshepherd's governance and evidence model.

The harness is deliberately **read-only from the robotic-platform perspective**. It has no HTTP client, socket transport, platform command method, or partner-specific field mapping.

## Neutral event envelope

Schema identifier: `ws-neutral-mission-event/1`

Required envelope fields:

- `event_id` — stable source-event identity used for idempotence.
- `mission_id` — mission/session correlation identity.
- `source_system` — source-system identity in the synthetic test environment.
- `event_type` — event semantic selected by the synthetic interface contract.
- `observed_utc` — timezone-aware observation time.
- `sequence` — non-negative source sequence value.
- `payload` — event-specific data restricted by the synthetic contract.

The event digest is canonical SHA-256 over the complete neutral envelope. The idempotency key is separately derived from schema version, source system, mission ID, and event ID so an identical retransmission produces the same acceptance identity. Reuse of that identity with a different event digest is treated as a collision/replay conflict and fails closed.

## Synthetic D1 non-kinetic ISR profile

The initial internal fixture uses only these message types:

1. `MISSION_STATE` — required payload field: `state`.
2. `ENTITY_OBSERVATION` — required fields: `entity_id`, `classification`, `confidence`.
3. `LINK_STATE` — required fields: `state`, `latency_ms`.
4. `HEARTBEAT` — required field: `stream`.

The fixture contains no weapon employment, targeting, payload-release, kinetic-action, or partner-control semantics.

## Adapter invariants

### I-01 — Contract-bounded ingestion / default deny

`required_message_types` is an explicit allowlist. Only event types listed by the active Worldshepherd synthetic `InterfaceContract` are accepted; an empty allowlist accepts no event types. Required payload fields are checked before evidence acceptance. Unlisted or unconfigured event semantics fail closed.

### I-02 — Idempotence and collision detection

A previously accepted event with the same neutral idempotency identity and the same event digest is marked duplicate and not accepted a second time. If the same idempotency identity is reused with different event content, the adapter rejects the event as an idempotency collision instead of silently treating it as a valid duplicate.

### I-03 — Provenance

Every synthetically accepted event produces a deterministic evidence record containing the event digest, contract digest, mission/source/event identity, observation time, `SIMULATION` evidence scope, and `SIMULATED_ONLY` capability status.

### I-04 — No external command transport

Adapter observations and supervisory evaluations contain `external_command_emitted = false`. The synthetic adapter exposes no platform-command transport API.

### I-05 — Human authority / bounded automation

Supervisory requests reuse the existing Worldshepherd `AutonomyPolicy` gate. A request may be `AUTO_ELIGIBLE`, `HUMAN_REVIEW_REQUIRED`, or `DENIED`; policy evaluation alone never emits a platform command.

### I-06 — Fail-independent boundary

The synthetic adapter is not a dependency of any partner platform. Validation failure, process exit, malformed input, or loss of the Worldshepherd adapter cannot command or halt an external platform because no external platform connection exists in this harness.

### I-07 — External activation gate

Any future external interface activation metadata must include:

- authoritative specification reference;
- SHA-256 digest of the authoritative specification; and
- partner-validation reference.

Even with those fields populated, the **synthetic adapter itself refuses external activation**. A future partner-specific adapter must be separately implemented and reviewed after the applicable legal, export-control, security, and partner-interface gates.

### I-08 — Optional durable restart reconciliation

When configured with SARA's local secured `DurableStore`, accepted idempotency identities and their evidence records are persisted under the synthetic interface-contract digest. Reconstructing the adapter against the same store reloads that state. An identical retransmission after reconstruction remains a duplicate; mutated reuse of the same identity remains a fail-closed collision and is written to the local audit log.

Reload is also fail-closed on malformed digest keys, event/contract digest mismatches, or an evidence identifier that does not recompute from the persisted event digest and active contract digest. This prevents syntactically valid but internally inconsistent persisted evidence from being silently trusted.

The persistence uses SARA's bounded local registry and is intended for controlled synthetic evidence, not an unbounded mission-event journal. It is **local single-store persistence only** and does not establish distributed exactly-once processing, multi-process linearizability, partner acknowledgement semantics, XOS replay behavior, or platform-level restart safety.

## D1 acceptance criteria

The internal synthetic test suite must demonstrate:

- all contracted fixture events are accepted once;
- an empty message-type allowlist accepts nothing and fails closed;
- identical retransmission is idempotently rejected as a duplicate;
- reuse of the same event identity with mutated content fails closed as an idempotency collision;
- required-field omissions fail closed;
- uncontracted event types fail closed;
- evidence remains `SIMULATION` / `SIMULATED_ONLY`;
- no adapter result reports external command emission;
- an allowlisted, reversible, authority-zero annotation may be `AUTO_ELIGIBLE` under the synthetic policy;
- a non-allowlisted supervisory action requires human review;
- an explicitly denied route-override action is denied; and
- external activation without authoritative/partner evidence is rejected, while the synthetic adapter rejects external activation even when such metadata is supplied.

## D2 local restart/rejoin acceptance criteria

With a temporary Worldshepherd-owned `DurableStore`, the internal test suite must demonstrate:

- an accepted event is persisted with its contract digest, idempotency identity, event digest, and evidence record;
- constructing a new adapter instance against the same durable store reloads the accepted-event state;
- replaying the identical event after adapter reconstruction is rejected as a duplicate and returns the original evidence identity;
- replaying the same event identity with changed content after reconstruction fails closed as an idempotency collision;
- the collision creates a local audit record;
- tampering with a persisted evidence identifier causes reload to fail closed; and
- no persistence or restart path creates an external command transport or upgrades evidence beyond `SIMULATION` / `SIMULATED_ONLY`.

D2 does **not** validate partner-platform restart/rejoin semantics, network partition reconciliation, distributed concurrent writers, acknowledgement ordering, monotonic sequence enforcement, unbounded event retention, or XOS-specific replay behavior. Those remain partner/interface requirements.

## Requirement delta for any future XTEND mapping

The following remain **REQUIRES PARTNER VALIDATION / REQUIRES LEGAL OR EXPORT-CONTROL REVIEW** as applicable:

- actual XOS message and object types;
- XOS field names and data types;
- authentication/authorization method;
- transport protocol and endpoint behavior;
- sequence, replay, acknowledgement, and retry semantics;
- platform timing and latency requirements;
- allowed supervisory outputs;
- error/fault codes;
- data classification and export-control boundary;
- deployment/container constraints;
- partner test environment and success criteria; and
- any certification or marketplace requirements.

These items must not be reverse engineered or inferred from the synthetic schema.

## Evidence locations

- Module: `worldshepherd_sara/physical_ai_synthetic_adapter.py`
- Fixture: `fixtures/physical_ai_nonkinetic_isr_synthetic_v1.json`
- Tests: `tests/test_physical_ai_synthetic_adapter.py`

## Claim boundary

Passing this test suite would establish only that the Worldshepherd-owned synthetic adapter behavior passed the stated internal software tests on the tested commit. It would **not** establish XTEND/XOS interoperability, XTEND Certified status, platform safety, field performance, government acceptance, external certification, export classification, distributed exactly-once processing, unbounded event-retention suitability, or partnership.
