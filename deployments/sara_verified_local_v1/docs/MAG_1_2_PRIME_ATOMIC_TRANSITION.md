# MAG-1.2 — PRIME Requalification Atomic Transition Boundary

- **Status:** stacked implementation branch / pre-merge review
- **Dependency:** MAG-1.1 (`feature/mag-1-1-prime-echo-binding`)
- **Canonical runtime:** `deployments/sara_verified_local_v1/`
- **Software implementation claim:** `IMPLEMENTED IN SOFTWARE` only after exact-commit canonical CI succeeds
- **Operational effectiveness:** `REQUIRES LAB VALIDATION`

## Purpose

MAG-1.1 proved that a narrow `REQUALIFICATION_RELEASE` authority can be derived from an Ed25519-verified PRIME SENTINEL assertion and represented as MAG-1 authority. It intentionally stopped before the consequential custody transition.

MAG-1.2 moves that control to the actual state-change boundary.

For the PRIME requalification path, one `DurableStore.transact_registry()` callback now derives the decision and, when every gate passes, returns one registry patch containing:

1. one-time PRIME authorization consumption;
2. PRIME custody transition from `QUARANTINED_FOR_REQUALIFICATION` to `READY`;
3. deterministic MAG-1 decision evidence queued through the existing SARA event outbox; and
4. deterministic PRIME transition evidence queued through the same outbox.

If an exception occurs before the callback returns, `transact_registry()` performs no registry write.

## Protected sequence

```text
latest validated registry snapshot
        |
        v
registered custody record must be QUARANTINED_FOR_REQUALIFICATION
        |
        v
verify Ed25519 PRIME assertion
        |
        v
verify recorded authorization is current + VERIFIED + registry-consistent
        |
        v
derive fixed MAG-1 PRIME requalification authority
        |
        v
canonical EXECUTE trajectory action
        |
        v
MAG-1 context + authorization + trajectory + autonomy decision
        |
        +---- HUMAN_REVIEW / DENY / PAUSE ----> queue decision evidence only
        |
        v AUTO_ELIGIBLE
verify signed target environment == mission-pack target
        |
        v
bind signed authorization identity to custody release fields
        |
        v
existing custody release gate validates mission-pack evidence
        |
        v
build deterministic transition identity
        |
        v
consume one-time PRIME authorization
        |
        v
persist READY custody state
        |
        v
queue MAG-1 evidence + transition evidence
        |
        v
single validated registry replacement
```

## Canonical action classification

The caller does not choose the side-effect classification for the final custody transition.

MAG-1.2 constructs the transition action internally as:

- action: `REQUALIFICATION_RELEASE`;
- side effect: `EXECUTE`;
- destination: none; and
- authorization initially unverified until the cryptographic bridge proves it.

The candidate action ID must equal the trajectory action ID. This prevents a caller from obtaining a decision for one action identity and applying it to another.

## PRIME custody registry namespace

MAG-1.2 introduces:

`PRIME_CONFIGURATION_CUSTODY`

The namespace stores serialized `PrimeConfigurationCustodyRecord` objects by `prime_id`. Registry lookup revalidates the record model and rejects an identity mismatch between the map key and the embedded PRIME identity.

This makes custody state part of the same registry transaction as PRIME authorization state and outbox state for this path.

## Authorization binding rule

Existing custody release authorization fields may be empty or must already match the newly verified signed PRIME authority exactly.

MAG-1.2 refuses to silently overwrite a conflicting:

- authorization ID;
- target environment; or
- PRIME key ID.

This prevents a stale or different custody authorization from being replaced merely because another valid assertion exists.

## Transition identity

A successful transition receives a deterministic `PRIME-MAG1-TRANSITION-*` identifier derived from canonical JSON containing:

- schema ID;
- verified authorization ID;
- signed PRIME identity;
- signed target environment;
- verified key ID;
- pre-transition custody SHA-256;
- mission-pack evidence object;
- trajectory ID;
- action ID; and
- active MAG-1 policy-bundle SHA-256.

The consumed PRIME authorization is bound to this transition ID.

The transition evidence event receives a deterministic event ID derived from the transition ID.

## Evidence produced

A successful transaction queues two independently named, stable-ID events:

### `mag1_decision`

Carries the MAG-1 dispositions, cumulative risk, policy hash, authorization reference, and authority lineage digest according to `WS-MAG1-EVIDENCE-V1`.

### `prime_requalification_transition`

Carries `WS-PRIME-MAG1-TRANSITION-V1` evidence including:

- transition ID;
- PRIME ID;
- authorization ID;
- target environment;
- mission-pack ID;
- before/after custody hashes;
- active policy-bundle hash;
- trajectory/action IDs;
- linked MAG-1 evidence event ID;
- SHA-256 of the MAG-1 evidence payload; and
- SHA-256 of release reasons.

Raw credentials, signatures, model text, candidate payload contents, and raw release reasoning are not copied into transition evidence.

## Failure atomicity

The relevant existing storage primitive is `DurableStore.transact_registry()`:

- it holds the store instance's re-entrant lock across read/derive/write;
- callback exceptions abort before a registry write;
- the resulting registry is validated before persistence; and
- persistence uses a temporary secured file, `fsync`, `os.replace`, and directory `fsync`.

MAG-1.2 uses this primitive directly rather than assembling independent `patch_registry()` calls.

The regression suite includes an outbox-capacity fault that occurs **after** authorization consumption and custody release have been derived in memory but **before** the transaction can commit. The expected result is no authorization consumption, no custody release, and no partial outbox mutation in durable registry state.

## Same-store concurrency property

The test suite runs two concurrent requalification attempts through the same `DurableStore` instance. Because `transact_registry()` holds that instance's lock, exactly one attempt may apply the transition; the second observes the new custody/authorization state and cannot apply the release again.

This is an important but bounded property.

## Explicit concurrency boundary

MAG-1.2 does **not** establish cross-process or distributed linearizability.

`DurableStore` currently uses `threading.RLock`, which serializes threads sharing one store instance. It is not a process-wide filesystem lock, database transaction, compare-and-swap service, or distributed consensus mechanism.

Two independent processes opening the same registry path are therefore outside the property established by this branch. Before multi-process deployment, the next storage gate should add and test one of:

- an OS-level advisory/exclusive file-lock discipline held across read/derive/write;
- a transactional database with row/version constraints;
- explicit compare-and-swap on a monotonic registry revision; or
- another persistence mechanism providing an equivalent single-writer/linearizable guarantee.

Do not describe MAG-1.2 as globally atomic until that property exists and is tested.

## ECHO boundary

MAG-1.2 atomically queues evidence with the protected registry state change. It does **not** make ECHO/audit delivery part of the same filesystem transaction.

The existing event outbox intentionally provides at-least-once delivery: registry state can commit with evidence still `PENDING`, and a later outbox drain emits the audit record. Stable event IDs allow exact replay to be deduplicated downstream.

Therefore the defensible claim is:

> protected PRIME state and the obligation to deliver linked evidence are committed together to the SARA registry.

It is **not**:

> ECHO has already durably ingested the evidence at the exact instant of the custody state change.

## Mission-pack evidence boundary

MAG-1.2 executes the repository's existing `release_from_quarantine()` gate and therefore verifies the structural mission-pack fields that gate already requires.

This branch does not independently establish the provenance or cryptographic authenticity of the upstream mission-pack evidence object. A future mission-pack attestation layer should bind those claims to signed or otherwise independently verifiable evidence.

## Regression coverage

The MAG-1.2 suite exercises:

1. successful all-or-nothing authorization consumption + custody release + two-event outbox commit;
2. preservation of unrelated registry state;
3. MAG-1 human-review outcome with no protected-state transition;
4. unauthenticated mission-pack failure with an unchanged registry;
5. signed-target/mission-pack environment mismatch;
6. refusal to overwrite conflicting custody authorization identity;
7. tampered PRIME signature rejection with no write;
8. action-identity substitution rejection;
9. replay rejection after a successful release;
10. outbox-capacity fault injection proving no partial protected-state commit;
11. same-store concurrent attempts yielding one applied transition; and
12. custody registry serialization/identity round-trip.

## Claims boundary

After exact-commit canonical CI passes, a precise software claim may state:

> Worldshepherd SARA implements a PRIME requalification path in which cryptographically verified PRIME authority, MAG-1 eligibility, one-time authorization consumption, custody release, and queued decision/transition evidence are derived and committed through one validated `DurableStore` registry transaction, with regression coverage for rollback, replay, and same-store thread concurrency.

Do **not** broaden this to claims that:

- Worldshepherd solves AI alignment;
- every model action is covered by MAG-1;
- all authorization paths are cryptographically bound;
- multi-process or distributed transitions are linearizable;
- ECHO ingestion is transactionally atomic with registry persistence;
- mission-pack evidence provenance is cryptographically established;
- trajectory risk weights are calibrated;
- every unauthorized action will be detected or prevented; or
- production, regulatory, mission, flight, weapon, CUI, classified-system, or third-party certification exists.

## Next gate — MAG-1.3

The next consequential gate should target **cross-process persistence authority and active containment** rather than expanding the claims surface:

1. add a cross-process single-writer/CAS transaction mechanism to the canonical registry store;
2. fault-inject process crashes before temp-file `fsync`, before/after `os.replace`, and before/after outbox delivery;
3. add a runtime OVERWATCH pause/containment actuator that can prevent a pending consequential transition rather than merely label it;
4. cryptographically attest mission-pack evidence provenance;
5. bind active policy bundles to signed policy publication/version records; and
6. run repeated model-in-the-loop adversarial trials, reporting prevention, detection, false-positive, rollback, and unresolved-violation rates separately.
