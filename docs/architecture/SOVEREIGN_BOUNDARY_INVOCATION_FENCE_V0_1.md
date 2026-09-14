# Worldshepherd Sovereign Boundary Invocation Fence v0.1

Status: **IMPLEMENTED IN SOFTWARE on feature branch; current-head repository CI remains pending**

## 1. Problem closed by this gate

A durable one-time authorization claim is necessary but not sufficient to prevent duplicate physical effects.

The unsafe pattern is:

```text
process A reads CLAIMED ----+
                            +--> both believe execution is permitted
process B reads CLAIMED ----+

process A -> executor
process B -> executor
```

If the authorization read and external executor invocation are separated without a process-shared serialization primitive, two independent processes can race through the same `CLAIMED` state.

SBK therefore uses two nested serialization layers:

1. `threading.RLock` for callers inside one Python process; and
2. POSIX `fcntl.flock` on a secured `.registry.lock` file for cooperating `DurableStore` instances in independent processes sharing one local data directory.

The invocation state itself remains persisted in `registry.json` using the existing atomic replace + fsync path.

## 2. Authority lifecycle

The physical-effect authorization lifecycle is:

```text
VERIFIED
   |
   | exact envelope/action binding + unexpired authority
   v
CLAIMED
   |
   | cross-process serialized invocation fence
   v
INVOKING
   |\
   | \
   |  +---- uncertain external outcome ----> INDETERMINATE
   |
   +------- explicit executor result ------> CONSUMED
                                              + pending ECHO event
```

`CLAIMED -> INVOKING` is the point at which Worldshepherd treats the external-effect boundary as potentially crossed.

Once an authorization reaches `INVOKING`, it is never automatically returned to `CLAIMED` or `VERIFIED`.

## 3. Central invariant

> **Among cooperating Worldshepherd processes on one POSIX host that share the same authoritative `DurableStore` data directory, a physical executor may be called only by the process that successfully persists the matching `CLAIMED -> INVOKING` transition.**

The transition is performed inside `DurableStore.transact_registry()` while both the in-process lock and the process-shared advisory lock are held.

Therefore two cooperating processes cannot both derive `INVOKING` from the same `CLAIMED` registry snapshot. The winner persists `INVOKING` before external invocation. The loser reads the updated state and fails before its executor callback is called.

## 4. What the fence binds

Before the transition can occur, the ledger revalidates:

- authorization ID;
- execution ID;
- SBK envelope ID;
- exact `action_digest`;
- PRIME authorization reference;
- PRIME execution-claim reference;
- sealed SBK envelope integrity;
- short-lived authorization expiry.

Authorization expiry is intentionally checked again at the invocation boundary. A claim made while authority was valid cannot remain dormant and later be used after that authority has expired.

## 5. Cross-process serialization primitive

`DurableStore` creates a secured `.registry.lock` file beside the registry and opens it with `O_NOFOLLOW` when the platform supports that flag.

Every `patch_registry()` and `transact_registry()` mutation now executes under:

```text
threading.RLock
      +
fcntl.flock(LOCK_EX)
      +
validated registry read
      +
read / derive / write
      +
atomic temp-file replace
      +
fsync(file)
      +
fsync(directory)
```

The advisory lock is released automatically by the OS if the process exits, while the durable `INVOKING` state remains in the registry if the point-of-no-safe-replay boundary had already been crossed.

This is deliberately a **single-host POSIX serialization mechanism**, not a distributed-consensus mechanism.

## 6. Crash semantics

The conservative crash model is deliberate.

### Crash before `INVOKING` is committed

The central PEP has not crossed its durable invocation fence. The record remains `CLAIMED`.

Operational recovery policy may still choose to mark the claim `INDETERMINATE` when process history is incomplete rather than blindly retrying.

### Crash after `INVOKING` is committed

The system cannot prove whether the executor was entered or whether an external device acted.

The authorization must therefore be treated as unresolved and must not be automatically replayed.

The safe resolution is:

```text
INVOKING -> INDETERMINATE -> human/operator reconciliation -> fresh authority if needed
```

### Executor raises after invocation

The central PEP moves the authorization to `INDETERMINATE` best-effort and raises a fail-closed error.

The same authorization is not retried.

## 7. Known-result finalization

When the executor returns an explicit `PhysicalEffectResult`, SBK records the terminal envelope and performs one local registry transaction that combines:

```text
INVOKING -> CONSUMED
       +
SARA/ECHO outbox event -> PENDING
```

This couples local authorization consumption to evidence production as tightly as the current store permits.

It does **not** make an external physical device and the local filesystem one distributed transaction.

## 8. Adversarial proofs

Two distinct software tests exercise the process-shared guarantee.

### Registry lost-update proof

`test_storage_cross_process.py` launches two independent POSIX processes against the same data directory. Both intentionally widen the read/derive/write race window. The final registry must contain both increments, proving that the transaction critical section is serialized across the two processes.

### Physical-PEP cross-process proof

`test_sovereign_boundary_pep_cross_process.py` launches process A and process B against the same one-time physical authorization:

1. A acquires `CLAIMED -> INVOKING`;
2. A enters a deliberately blocked benign de-energized executor callback;
3. while A remains inside the callback, B attempts the same authorization/execution ID from an independent process;
4. B cannot acquire the invocation fence and fails before its executor callback emits an `entered` event;
5. the durable ledger remains `INVOKING` while A owns the boundary;
6. A is released and completes;
7. the ledger ends in `CONSUMED`.

The same broader PEP suite verifies runtime action mutation, authorization expiry at invocation time, executor ambiguity, and non-retryable `INDETERMINATE` state.

## 9. Security boundary

The process-shared fence establishes a software invariant only for cooperating processes that:

- use `DurableStore`;
- point to the same local authoritative data directory;
- run on a POSIX filesystem with supported `flock` semantics; and
- route physical effects through the Worldshepherd PEP.

It does not prevent:

- a separate program from bypassing `DurableStore` and mutating the registry directly;
- a program from bypassing the PEP and driving hardware directly;
- compromised firmware from ignoring the host-side interlock;
- a second host maintaining an independent authority store;
- network/distributed-filesystem locking anomalies;
- malicious physical access; or
- actuator behavior that cannot provide trustworthy outcome evidence.

Those are deployment, firmware, distributed-systems, key-custody, and hardware-interlock assurance problems.

## 10. Hardware implication

The next physical assurance experiment should not test advanced propulsion, RF, or autonomous performance.

It should test the **authority boundary itself** using a benign de-energized or low-energy fixture:

```text
unauthorized command --------------------> hardware refuses
changed parameters after policy ---------> hardware refuses
expired authorization -------------------> hardware refuses
second process / same authorization -----> hardware refuses
valid complete chain --------------------> observable benign state transition
```

The eventual hardware adapter should expose a device-side interlock interface that accepts only the currently bound SBK execution identity and rejects replayed or stale execution identities.

## 11. Claims boundary

Subject to repository CI and review, this gate supports an **IMPLEMENTED IN SOFTWARE** claim for a one-way physical invocation fence that serializes cooperating callers across independent processes on one POSIX host sharing one authoritative `DurableStore` data directory.

It does not support claims of distributed consensus, multi-host mutual exclusion, hardware-enforced non-replay, or exactly-once physical actuation. External effects remain outside the local storage transaction, and uncertain outcomes remain explicitly `INDETERMINATE`.
