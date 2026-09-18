# WS-SARA G9A — CROSS-PROCESS REGISTRY SERIALIZATION

Status: **IMPLEMENTED ON STACKED BRANCH / PENDING G8 + EXACT-HEAD QUALIFICATION**

## Purpose

G9A is the first prerequisite for external monotonic rollback witnessing.

G8 protects PRIME trust-root state inside one SARA persistence domain. Before a checkpoint journal or witness can be trusted, cooperating SARA processes must not race registry initialization or read/derive/write transactions.

G9A adds one process-visible advisory lock file:

`registry.lock`

and serializes registry initialization, reads, patches, and transactions across POSIX processes.

## Implemented boundary

- secure `registry.lock` inode created before registry initialization;
- mode forced to 0600;
- symbolic-link following rejected where `O_NOFOLLOW` exists;
- shared process lock for registry reads;
- exclusive process lock for registry initialization and mutation;
- existing in-process `threading.RLock` retained;
- explicit runtime flag reports whether POSIX cross-process locking is available;
- readiness verifies the lock file remains secured;
- no caller-controlled lock bypass on `patch_registry` or `transact_registry`.

## Qualification

The focused regression suite uses Python multiprocessing with the `spawn` context so workers do not inherit parent lock descriptors or in-memory lock state.

Required cases:

1. lock file is private and runtime support is explicit;
2. four independent workers contending on one read/derive/write counter commit 1..4 with no lost update;
3. repeated three-worker contention rounds preserve exact count and round identity;
4. a symlinked lock file is rejected where no-follow support exists.

## Claims boundary

A PASS establishes **local cooperating-process serialization on POSIX runtimes where advisory flock semantics are honored**.

It does not establish:

- distributed consensus;
- coordination across hosts;
- mandatory-kernel locking against a privileged process that ignores the advisory protocol;
- NFS or other network-filesystem lock semantics;
- crash-atomic multi-file transactions;
- registry rollback resistance;
- external witnessing;
- WORM retention;
- independent administration.

## Dependency role

G9B may layer a hash-chained registry checkpoint journal on top of this process lock.

G9C may then bind checkpoint generation/state-root/commit coordinates to a signed monotonic witness.

This layering keeps each assurance claim separately testable instead of treating one large MAG stack as a single undifferentiated control.
