# WS-SDA G7 — DDIL Release-Journal Rejoin + Replay Baseline

Status: **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH — EXACT-HEAD CI REQUIRED**
Date: 2026-09-18
Branch: `feature/ws-sda-g7-ddil-rejoin-20260918`
Parent stack: G1/G2 -> G3 -> G4 -> G5 -> G6

## 1. Objective

G7 connects the G6 human-bound analytic release receipt to deterministic
disconnected-operation storage, rejoin reconciliation, ECHO evidence transport, and
mission replay.

The key invariant is:

> Loss of connectivity must not create new authority, erase receipt conflicts, or
> silently reinterpret one authorization as another.

G7 stores evidence about an already-consumed G6 authorization. It cannot extend,
renew, replace, or manufacture release authority.

## 2. Durable disconnected journal

`worldshepherd_sara/sda_ddil_release.py` adds a bounded SQLite release journal.

Controls include:

- absolute service-owned data directory;
- real-directory / regular-database enforcement;
- data-directory mode 0700;
- database mode 0600;
- SQLite `synchronous=FULL`;
- bounded record count;
- authorization ID as the immutable semantic key;
- receipt digest stored beside canonical record JSON;
- exact receipt replay deduplication;
- differing receipt semantics for the same authorization ID rejected as conflict;
- conflict count retained for health evidence;
- SQLite quick-check and semantic revalidation during health inspection.

This is durable reference software storage, not tactical-link qualification.

## 3. Rejoin semantics

For two disconnected journal windows:

- identical receipt semantics on both sides -> `MATCHED`;
- unique left receipt -> `LEFT_ONLY`;
- unique right receipt -> `RIGHT_ONLY`;
- same authorization ID with different receipt digest -> `CONFLICT`.

For a conflict, no candidate is selected.

Logical clock and authority may choose a deterministic representative **only when the
underlying G6 receipt digest is already identical**. A newer clock or higher local
authority cannot overwrite different receipt semantics for one authorization ID.

## 4. ECHO binding

Each node emits a stable ECHO event identity derived from:

```text
authorization_id || origin_node
```

This gives:

- exact retransmission from one origin -> ECHO deduplication;
- semantic mutation from that same origin -> ECHO conflict;
- the same receipt replicated by another node -> independent node evidence rather
  than a false same-event collision.

The payload declares `AT_LEAST_ONCE` delivery. G7 does not claim globally
exactly-once delivery.

## 5. Mission replay binding

Reconciled release receipts can be converted deterministically into
`MissionEvent` records ordered by G6 consumption time, authorization ID, and origin
node.

Replay preserves:

- authorization ID;
- receipt digest;
- hypothesis-set digest;
- payload digest;
- policy-revision digest;
- destination;
- releasability tags;
- human approval identity.

The replay event explicitly states that it is evidence only and cannot authorize a
second release.

## 6. Executable negative gates

The G7 suite covers:

1. persistence across journal restart;
2. exact deduplication;
3. same-authorization semantic mutation rejection;
4. bounded journal capacity;
5. database/semantic tamper detection;
6. deterministic matched/left-only/right-only rejoin;
7. conflict with no automatic winner even when one side has higher clock/authority;
8. conflicting duplicates inside one reconciliation input rejected;
9. ECHO exact retransmission deduplication;
10. ECHO same-origin semantic-mutation conflict;
11. distinct ECHO identities for honest replica nodes;
12. deterministic mission-replay ordering;
13. replay evidence that cannot be interpreted as new release authority.

## 7. Claims boundary

A passing G7 reference suite will establish bounded software behavior for synthetic
or reference analytic-release receipts.

It will **not** establish:

- RF, satellite, tactical-network, or operational DDIL performance;
- distributed consensus;
- external recipient acknowledgement;
- globally exactly-once delivery;
- operational orbit/track correctness;
- targeting, weapon cueing, or actuation;
- fielded store-and-forward hardware;
- classified-network approval;
- independent or government validation.

## 8. Next gate

G8 freezes a reproducible adversarial/fault corpus across G1-G7. Every security
property already driven to zero becomes a non-regression invariant; faults with a
non-zero residual rate receive a frozen baseline for G9 10x measurement.
