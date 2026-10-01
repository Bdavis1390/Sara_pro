# WS-SOE v0.1C External Reconciliation Gate

## Scope

WS-SOE v0.1C extends the merged v0.1B durable-execution demonstration across the first intentionally non-transactional boundary: a harmless mock external service that owns a **separate SQLite database** from the local Worldshepherd coordinator.

The purpose is not to claim that external side effects are atomic. The purpose is to prove a narrower and more useful recovery invariant:

> **UNCERTAIN is not FAILED. An ambiguous external result must be reconciled before any retry.**

The only supported action remains harmless:

```text
demo.external.counter.increment
```

The mock external counter begins at `41` and the only accepted request applies `{"delta": 1}`.

## Why v0.1C exists

v0.1B could make the demo state mutation and replay record atomic because both lived inside one SQLite transaction. A real operating-system command, network request, container action, robot command, manufacturing operation, or physical action cannot generally join that same transaction.

The dangerous interval is therefore:

```text
local durable intent
      ↓
external dispatch
      ↓
external effect commits
      ↓
ACK lost / coordinator crashes
      ↓
local side cannot tell whether effect happened
```

Treating that interval as ordinary failure and automatically retrying can duplicate an external side effect. v0.1C instead persists ambiguity and reconciles against the external system's durable idempotency ledger.

## State machine

```text
PREPARED
   ↓
DISPATCHING
   ├── ACK received ────────────────┐
   │                                ↓
   │                         EFFECT_OBSERVED
   │                                ↓
   │                           RECONCILED
   │                                ↓
   │                              SEALED
   │
   ├── ACK lost ──► UNCERTAIN ──► reconcile by idempotency key
   │                                ├── effect found ─► EFFECT_OBSERVED → RECONCILED → SEALED
   │                                └── no effect ───► NO_EFFECT_CONFIRMED
   │                                                       ↓
   │                                              explicit redispatch only
   │                                                       ↓
   └── crash while DISPATCHING ───────────────────── reconcile first
```

A stale `DISPATCHING` record after restart is treated as potentially ambiguous. It is not silently retried.

## Deterministic idempotency binding

The coordinator derives a deterministic external idempotency key from the canonical SHA-256 digest of the exact v0.1A `Intent`.

The mock external service stores:

- the idempotency key;
- the canonical external-request hash;
- the canonical request JSON;
- before and after counter values;
- the durable commit timestamp.

An identical redelivery under the same key returns the first durable effect without incrementing again. Reuse of the same key for different request bytes is rejected.

This demonstrates a required **service-side idempotency contract**. It does not prove that an arbitrary real external service provides such a contract.

## Local coordinator evidence

The local v0.1C ledger stores:

- exact intent hash and ID;
- canonical signed decision JSON and hash;
- canonical authority-signature JSON and hash;
- canonical external-request JSON and hash;
- deterministic idempotency key;
- current coordinator state;
- canonical observation JSON and hash once reconciled;
- durable state-transition history.

The executor still receives only the configured Ed25519 public verification key. The authority private key remains outside the coordinator/executor API boundary inherited from v0.1B.

## Fault-injection acceptance cases

The v0.1C tests exercise four externally relevant failure windows:

1. **normal acknowledgement** — external effect is observed and sealed;
2. **external commit before acknowledgement loss** — local state becomes `UNCERTAIN`; restart and reconciliation find the durable external effect without duplicating it;
3. **external acknowledgement before local observation persistence** — restart finds stale `DISPATCHING`, reconciliation discovers the already-committed external effect, and no duplicate occurs;
4. **coordinator crash before the external call** — reconciliation confirms no effect, moves to `NO_EFFECT_CONFIRMED`, and only then permits explicit redispatch.

Additional adversarial tests cover replay after seal, duplicate idempotent delivery, idempotency-key/request substitution, forged authority signatures, post-signature decision mutation, database ownership/mode checks, and relative-path rejection.

## Claims boundary

When the v0.1C tests and repository gates pass, the implementation may claim only that the bounded software demonstration shows:

- durable distinction between `DISPATCHING`, `UNCERTAIN`, `NO_EFFECT_CONFIRMED`, reconciled, and sealed outcomes;
- no blind automatic retry from an ambiguous external outcome;
- explicit external lookup by deterministic idempotency key before retry;
- idempotent duplicate suppression in the mock external service;
- request-byte binding for each mock-service idempotency key;
- recovery after coordinator restart in the tested crash windows;
- preservation of v0.1B public-key-only decision verification before preparing an external operation.

v0.1C does **not** establish:

- distributed transactions or general exactly-once semantics;
- correctness of arbitrary third-party idempotency APIs;
- production HTTP/gRPC/QUIC transport behavior;
- crash consistency across arbitrary filesystems, databases, clusters, or replicas;
- Byzantine fault tolerance, consensus, quorum authorization, or distributed locking;
- HSM/TPM custody, measured boot, remote attestation, PKI lifecycle, or certificate rotation;
- safety for live operating-system, network, container, robotics, vehicle, manufacturing, weapon, medical, financial, or other consequential actions;
- certification, accreditation, CMMC/NIST compliance, or legal status.

## Promotion rule

A real SARA/PRIME action adapter remains blocked.

The next gate must move from the in-process mock service to a **real transport boundary while preserving the same ambiguity semantics**. The promotion criterion is not merely successful RPC. It is evidence that transport timeout, process restart, duplicate delivery, stale acknowledgement, and reconciliation are handled without collapsing `UNCERTAIN` into `FAILED` or blindly repeating an effect.

Until that gate passes, the rule remains:

> **No reconciliation, no retry. No evidence, no governed execution.**
