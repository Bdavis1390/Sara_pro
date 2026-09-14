# Worldshepherd Sovereign Boundary Invocation Fence v0.1

Status: **IMPLEMENTED IN SOFTWARE on feature branch; current-head repository CI remains pending**

## 1. Problem closed by this gate

A durable one-time authorization claim is necessary but not sufficient to prevent duplicate physical effects.

The unsafe pattern is:

```text
caller A reads CLAIMED ----+
                           +--> both believe execution is permitted
caller B reads CLAIMED ----+

caller A -> executor
caller B -> executor
```

If the read-only authorization check and external executor invocation are separate operations, two concurrent callers can both pass the same `CLAIMED` check before either caller finalizes the authorization.

For software reads this may be tolerable. For physical effects it is not.

SBK v0.1 therefore introduces a **durable one-way invocation fence**.

## 2. Authority lifecycle

The physical-effect authorization lifecycle is now:

```text
VERIFIED
   |
   | exact envelope/action binding + unexpired authority
   v
CLAIMED
   |
   | durable invocation fence
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

> **Within one process using the same `DurableStore`, a physical executor may be called only by the caller that successfully persists `CLAIMED -> INVOKING` for the matching authorization and execution ID.**

The transition is performed inside `DurableStore.transact_registry()`.

That primitive is protected by the store's in-process `threading.RLock`. Therefore two concurrent threads/callers sharing the same `DurableStore` cannot both derive `INVOKING` from the same `CLAIMED` record.

The winner persists `INVOKING` before external invocation. The loser observes a state other than `CLAIMED` and fails before its executor callback is called.

**Important scope limit:** v0.1 has not yet established inter-process registry serialization. Two independent OS processes opening the same data directory are not covered by this concurrency proof. Cross-process locking is a separate assurance gate and must be completed before a multi-process hardware PEP deployment is claimed safe from duplicate invocation races.

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

## 5. Crash semantics

The conservative crash model is deliberate.

### Crash before `INVOKING` is committed

The executor has not been entered by the central PEP. The durable record remains `CLAIMED`.

Operational recovery policy may still choose to mark the claim `INDETERMINATE` rather than retrying when process history is incomplete.

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

## 6. Known-result finalization

When the executor returns an explicit `PhysicalEffectResult`, SBK records the terminal envelope and then performs one local registry transaction that combines:

```text
INVOKING -> CONSUMED
       +
SARA/ECHO outbox event -> PENDING
```

This couples local authorization consumption to evidence production as tightly as the existing durable store permits.

It does **not** make an external physical device and the local filesystem one distributed transaction.

## 7. Concurrency proof exercised by tests

`test_sovereign_boundary_pep.py` includes an adversarial same-process two-caller test:

1. caller A acquires `CLAIMED -> INVOKING`;
2. caller A enters a deliberately blocked benign executor;
3. while A is still inside the executor, caller B attempts the identical effect using the same store;
4. caller B fails to acquire the invocation fence;
5. caller B's executor is never called;
6. caller A is released and completes;
7. the ledger ends in `CONSUMED`.

The same suite also verifies that:

- runtime action mutation fails before the fence;
- authorization expiry is rechecked before the fence;
- executor exceptions resolve to `INDETERMINATE`;
- a consumed or indeterminate authorization cannot cross the fence again.

The suite does **not** yet constitute a cross-process concurrency proof.

## 8. Security boundary

This mechanism establishes a software invariant only for effectors routed through the Worldshepherd PEP and concurrent callers serialized by the same in-process `DurableStore` lock.

It does not prevent:

- an independent OS process from racing registry read/derive/write operations before a process-shared lock is implemented;
- a separate program from bypassing the PEP and driving hardware directly;
- compromised firmware from ignoring the host-side interlock;
- a second independent authority store from issuing conflicting commands;
- a malicious operator with direct physical control;
- actuator behavior that cannot provide trustworthy outcome evidence.

Those are process-coordination, hardware, deployment, key-custody, systems-integration, and operational-control problems.

## 9. Next assurance gate: process-shared serialization

Before using the PEP from multiple worker processes, services, or containers that can mutate one registry, Worldshepherd should add a process-shared serialization mechanism and adversarial proof.

Candidate mechanisms include:

- POSIX advisory file locking around registry read/derive/write cycles on Linux;
- a single-writer authority service;
- a transactional database with compare-and-swap / serializable transitions;
- a hardware or device-side monotonic execution token for the final interlock.

The requirement is more important than the implementation choice:

> **The `CLAIMED -> INVOKING` transition must have exactly one authoritative winner across every process capable of commanding the same effector.**

Until that exists, deployment must preserve a single-process/single-writer authority boundary.

## 10. Hardware implication

The first physical assurance experiment should not test advanced propulsion, RF, or autonomous capability.

It should test the **authority boundary itself** using a benign de-energized or low-energy fixture:

```text
unauthorized command --------------------> hardware refuses
changed parameters after policy ---------> hardware refuses
expired authorization -------------------> hardware refuses
second same-process invocation ----------> hardware refuses
valid complete chain --------------------> observable benign state transition
```

The hardware adapter should expose an interlock interface that accepts only commands carrying the currently bound SBK execution identity. The first purpose of that fixture is to prove refusal behavior, not performance.

## 11. Claims boundary

This gate supports, subject to repository CI and review, an **IMPLEMENTED IN SOFTWARE** claim for a durable one-way invocation fence that prevents two compliant concurrent callers **within one process and one authoritative `DurableStore` lock domain** from both invoking the same one-time physical authorization.

It does not support a claim of cross-process mutual exclusion or exactly-once physical actuation. External effects remain outside the local storage transaction, and uncertain outcomes are explicitly represented as `INDETERMINATE`.
