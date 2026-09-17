# MAG-1.3 — POSIX Cross-Process Registry Serialization

## Status

**IMPLEMENTED IN SOFTWARE — validation is exact-commit CI dependent.**

MAG-1.3 extends the SARA durable registry transaction boundary from in-process thread serialization to cooperating-process serialization on POSIX runtimes that provide `fcntl.flock` semantics.

This document defines the property being implemented and, equally importantly, the properties that are **not** claimed.

## Problem closed by MAG-1.3

Before MAG-1.3, `DurableStore.transact_registry()` protected a read/derive/write cycle with a Python `threading.RLock`. That prevents races among threads sharing the same store instance, but independent SARA processes can each hold their own RLock.

Without a process-visible lock, this interleaving is possible:

```text
process A                  process B
---------                  ---------
read registry S0           read registry S0
derive S1                  derive S2
write S1                   write S2

result: one committed update can be lost
```

That is unacceptable for one-time PRIME authorization consumption, custody transitions, containment state, and other protected registry namespaces.

## Implemented transaction boundary

`DurableStore` now creates a private `registry.lock` inode and, on POSIX, acquires an advisory `flock` around registry access:

```text
thread RLock
    |
    v
registry.lock (flock)
    |
    v
read latest validated registry
    |
    v
derive complete transaction
    |
    v
validate complete updated resource
    |
    v
secured temporary write + fsync
    |
    v
atomic os.replace
    |
    v
parent-directory fsync
    |
    v
release flock
```

### Lock modes

- `get_registry()` uses a shared process lock.
- `patch_registry()` uses an exclusive process lock.
- `transact_registry()` uses an exclusive process lock across the complete read/derive/write cycle.
- store initialization also takes the exclusive process lock before registry creation/inspection.

The lock file is opened with no-follow semantics when the platform exposes `O_NOFOLLOW`, is required to be a regular file, and is forced to mode `0600`.

## Regression evidence

`tests/test_storage_process_lock.py` exercises independent Python processes using the `spawn` multiprocessing context so workers do not inherit the parent process's RLock or open lock descriptors.

The central lost-update fixture launches multiple workers against one data directory. Every worker:

1. waits on a common start event;
2. enters `transact_registry()`;
3. reads the same protected counter namespace;
4. intentionally sleeps inside the transaction to enlarge the stale-read race window;
5. increments and commits the counter.

For four concurrent workers the required committed sequence is exactly `1, 2, 3, 4` and the final durable value is exactly `4`. The suite repeats contention rounds and also verifies private lock-file permissions and symlink rejection where `O_NOFOLLOW` is available.

This is deliberately a multi-process test, not merely a second thread or a second `DurableStore` object in one process.

## Security and assurance boundary

MAG-1.3 supports this claim:

> On supported POSIX storage where advisory `flock` semantics are honored, cooperating SARA processes serialize registry read/derive/write transactions through one secured lock file, preventing the tested lost-update race among those processes.

MAG-1.3 does **not** establish any of the following:

- distributed consensus;
- Byzantine fault tolerance;
- linearizability across multiple hosts;
- correct advisory-lock behavior on every network/distributed filesystem;
- protection from a privileged host administrator;
- cross-file atomicity between the registry and audit log;
- crash-recovery semantics stronger than the existing fsync/atomic-replace design;
- database isolation for arbitrary external processes that ignore `registry.lock`;
- complete production or third-party validation.

On runtimes where `fcntl` is unavailable, `registry_cross_process_lock_supported` is false and the code intentionally does not claim the process-visible serialization property.

## Consequence for MAG-1.2

The MAG-1.2 PRIME transition already derives authorization consumption, custody release, MAG-1 evidence, and transition evidence inside `transact_registry()`.

With MAG-1.3 on a supported POSIX deployment, that protected registry transaction is no longer limited to threads sharing one store instance: independent cooperating SARA processes are forced through the same process-visible serialization boundary.

This does not turn MAG-1.2 into a distributed transaction. It removes one specific local multi-process race class.

## Next assurance gate

The next gate should use this process-visible transaction boundary to give OVERWATCH an actual **pre-commit containment authority** for consequential transitions.

The desired invariant is:

> A current, valid OVERWATCH containment directive observed inside the same protected registry transaction prevents PRIME authorization consumption and custody release; containment is an execution veto, not merely telemetry.

The containment path should be independently authenticated, replay-resistant, sequence-bound, fail closed on malformed state, and regression-tested against concurrent containment-versus-release races. Clearing a containment state should require stronger evidence than merely requesting that it disappear.
