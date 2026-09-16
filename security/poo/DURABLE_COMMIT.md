# Worldshepherd PoO Durable Internal Technical Commit

## Purpose

This layer implements the fifth step of the Worldshepherd Proof of Ownership technical-state ladder:

```text
Evidence Ready
  -> Local State Candidate
  -> Lineage-Governed Candidate
  -> CAS Registry Commit Candidate
  -> Durable Internal Technical Commit
```

The fifth step persists an **internal technical ownership state** in SARA. It does not transfer legal title, move value, rotate credentials, adjudicate a dispute, or create government-registry authority.

## Two admissible pre-commit paths

### Genesis/bootstrap

An empty installation has no active lineage tip, so genesis is governed separately by:

- `WS-POO-BOOTSTRAP-GOVERNANCE-V1`; and
- `WS-POO-BOOTSTRAP-COMMIT-DECISION-V1`.

Bootstrap requires:

1. an empty technical registry;
2. a PoO-valid genesis claim;
3. an exact COC digest bound into that PoO claim;
4. a valid genesis COC with no COC predecessor;
5. a valid local bootstrap state candidate;
6. an expected registry digest equal to the deterministic empty-registry digest; and
7. a matching optimistic-concurrency snapshot.

After any durable technical state exists, a distinct second bootstrap is rejected. Exact retries of the same already-committed bootstrap remain idempotent.

### Post-genesis supersession

Transfer and recovery commits require `WS-POO-GOVERNANCE-DECISION-V3` in the exact ready state produced by the full lineage + optimistic-concurrency path.

A ready candidate must carry:

- checked/valid PoO lineage;
- checked/valid COC lineage;
- valid generation continuity;
- one active technical tip;
- no fork/cycle conflict;
- predecessor equal to the active tip;
- checked optimistic concurrency;
- expected registry digest equal to the current registry digest; and
- candidate registry and candidate state digests.

## SARA durable registry

The deployment namespace is:

`POO_TECHNICAL_REGISTRY`

It is protected from generic `/admin/registry` PATCH operations and can be changed only through the dedicated governed PoO API.

SARA independently recomputes technical-state and registry digests and independently checks durable structural invariants:

- globally unique PoO digests;
- one genesis per asset;
- genesis event type `CLAIM`;
- genesis generation zero;
- no genesis COC predecessor;
- every non-genesis PoO predecessor exists;
- every COC predecessor equals the parent active COC digest;
- every generation advances its parent by exactly one;
- no post-genesis `CLAIM` event;
- no parent has more than one child;
- no cycle or disconnected component; and
- no duplicate active COC digest inside one asset lineage.

The durable adapter therefore does not rely on an upstream projection alone for registry-structure safety.

## Extension-only commit

A new commit must preserve every existing technical state and append exactly one governed candidate state.

```text
candidate_states = current_states UNION {governed_candidate}
```

Existing technical states cannot be silently changed or removed.

## Human approval boundary

`POST /admin/poo/registry/commit` requires the authenticated SARA `admin` role plus the literal intent:

`COMMIT_INTERNAL_TECHNICAL_STATE`

The request also carries an explicit `approval_reference`, which is bound into the durable commit record and audit evidence.

This is authenticated operator approval. It is **not** a cryptographic claim that CRE1AWS personally signed the commit. The existing PRIME SENTINEL authorization schema is intentionally not reused because its current action is specifically `REQUALIFICATION_RELEASE`. A future signed PoO approval must use its own action/schema.

## Atomic state + audit intent

The PoO namespace update and a stable audit-outbox event are prepared in one `DurableStore.transact_registry()` operation.

If outbox validation or capacity fails, the transaction raises before the registry write, so the technical state is not committed without durable audit intent.

The outbox subsequently delivers:

`poo_technical_registry_committed`

with `AT_LEAST_ONCE` delivery semantics and a deterministic event ID derived from the deterministic commit ID. Consumers deduplicate by the stable outbox event ID.

## Idempotency

The commit ID binds:

- projection digest;
- source decision digest;
- candidate registry digest; and
- candidate state digest.

An exact retry returns `ALREADY_COMMITTED` rather than appending another state. The same historical commit remains recognizable even after later valid commits advance the active registry, provided its candidate state remains in the extension-only state history.

## Claims boundary

A successful durable commit may report:

`durable_internal_state_committed = true`

It always reports or preserves false for:

```text
legal_title_changed
live_value_moved
credential_rotated
external_transfer_executed
```

It does **not** establish:

- legal ownership;
- legal custody;
- government registry status;
- external transfer execution;
- credential/key rotation;
- live-value movement;
- external certification or validation;
- automatic dispute resolution; or
- conflict-winner selection.

The durable PoO registry is an internal evidence/state-control system, not a legal-title registry.