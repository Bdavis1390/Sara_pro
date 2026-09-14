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
   | durable atomic invocation fence
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

> **A physical executor may be called only by the caller that successfully persists `CLAIMED -> INVOKING` for the matching authorization and execution ID.**

The transition is performed inside `DurableStore.transact_registry()`.

Because that operation derives and writes the protected registry state under one lock, two callers using the same authoritative store cannot both derive `INVOKING` from the same `CLAIMED` record.

The winner persists `INVOKING` before external invocation. The loser observes a state other than `CLAIMED` and fails before its executor callback is called.

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

`test_sovereign_boundary_pep.py` includes an adversarial two-caller test:

1. caller A acquires `CLAIMED -> INVOKING`;
2. caller A enters a deliberately blocked benign executor;
3. while A is still inside the executor, caller B attempts the identical effect;
4. caller B fails to acquire the invocation fence;
5. caller B's executor is never called;
6. caller A is released and completes;
7. the ledger ends in `CONSUMED`.

The same suite also verifies that:

- runtime action mutation fails before the fence;
- authorization expiry is rechecked before the fence;
- executor exceptions resolve to `INDETERMINATE`;
- a consumed or indeterminate authorization cannot cross the fence again.

## 8. Security boundary

This mechanism establishes a software invariant only for effectors routed through the Worldshepherd PEP and the same authoritative durable store.

It does not prevent:

- a separate program from bypassing the PEP and driving hardware directly;
- compromised firmware from ignoring the host-side interlock;
- a second independent authority store from issuing conflicting commands;
- a malicious operator with direct physical control;
- actuator behavior that cannot provide trustworthy outcome evidence.

Those are hardware, deployment, key-custody, systems-integration, and operational-control problems.

## 9. Hardware implication

The next physical assurance experiment should not test advanced propulsion, RF, or autonomous capability.

It should test the **authority boundary itself** using a benign de-energized or low-energy fixture:

```text
unauthorized command --------------------> hardware refuses
changed parameters after policy ---------> hardware refuses
expired authorization -------------------> hardware refuses
second concurrent invocation ------------> hardware refuses
valid complete chain --------------------> observable benign state transition
```

The hardware adapter should expose an interlock interface that accepts only commands carrying the currently bound SBK execution identity. The first purpose of that fixture is to prove refusal behavior, not performance.

## 10. Claims boundary

This gate supports, subject to repository CI and review, an **IMPLEMENTED IN SOFTWARE** claim for a durable one-way invocation fence that prevents two compliant concurrent PEP callers from both invoking the same one-time physical authorization.

It does not support a claim of exactly-once physical actuation. External effects remain outside the local storage transaction, and uncertain outcomes are explicitly represented as `INDETERMINATE`.
