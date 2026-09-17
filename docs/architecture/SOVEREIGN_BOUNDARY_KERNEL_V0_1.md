# Worldshepherd Sovereign Boundary Kernel (SBK) v0.1

Status: **IMPLEMENTED IN SOFTWARE on feature branch; pending current-head repository CI and review**

The Sovereign Boundary Kernel is Worldshepherd's domain-neutral governed-effect contract. It composes exact-action hashing, evidence maturity, policy, human approval, purpose-bound PRIME authority, one-time execution state, same-host POSIX process serialization, ECHO provenance, and replay.

## Core invariants

1. **Authorization never upgrades evidence maturity.** `SIMULATED_ONLY` cannot be relabeled into physical authority, and lab execution does not self-promote a capability to `PROVEN_INTERNALLY`.
2. **Authority is conjunctive.** Policy, evidence scope, human approval, PRIME authority, action identity, and execution state must all agree.
3. **`INVOKING` is the point of no safe automatic replay.** Physical authority moves `VERIFIED -> CLAIMED -> INVOKING -> CONSUMED`, with uncertain outcomes moving to `INDETERMINATE`.
4. **The exact action is immutable across the authority boundary.** The policy-evaluated action is SHA-256 bound; post-policy mutation fails closed.
5. **One local authority store has one serialized invocation winner.** Cooperating processes on one POSIX host sharing one `DurableStore` directory serialize registry transitions with `threading.RLock + fcntl.flock`.

## Authority transaction

```text
proposal
  -> capability/evidence classification
  -> exact action digest
  -> OPA-compatible policy decision
  -> SBK envelope
  -> required human approval
  -> Ed25519 PRIME effect authorization
  -> durable VERIFIED
  -> one-time CLAIMED execution ID
  -> expiry + exact-action recheck
  -> process-shared CLAIMED -> INVOKING fence
  -> physical PEP/executor
  -> CONSUMED or INDETERMINATE
  -> SARA AT_LEAST_ONCE outbox
  -> ECHO persistence/deduplication/reconciliation
  -> replay/evidence graph
```

## Same-host cross-process boundary

`DurableStore` uses a secured `.registry.lock` file and POSIX `fcntl.flock(LOCK_EX)` around registry read/derive/write transactions. This closes the local multi-process lost-update race for cooperating Worldshepherd processes using one authoritative data directory.

The guarantee is intentionally bounded. It does not establish distributed consensus, multi-host mutual exclusion, safety against direct registry mutation by bypass code, or device-side enforcement.

## Adversarial proofs on the branch

The branch contains software tests for exact-action binding, tamper detection, simulation-to-physical maturity refusal, human and PRIME authority requirements, one-time execution claims, expiry-at-invocation, ambiguous-outcome handling, same-process duplicate invocation refusal, cross-process registry serialization, and cross-process PEP duplicate-invocation refusal.

The cross-process PEP proof holds process A inside a benign de-energized executor after `INVOKING` is persisted, then starts process B with the same authorization/execution identity. B must fail before its executor callback is entered; A then completes and the ledger ends `CONSUMED`.

## Evidence boundary

Routine ECHO/outbox events exclude raw action parameters. They retain digests and the minimum authority/provenance references needed to reconstruct which exact action was governed. Delivery remains `AT_LEAST_ONCE`; no exactly-once transport or actuation claim is made.

## First cross-domain adapter

The programmable-boundary benchmark enters SBK only as `SIMULATED_ONLY + SIMULATION`. Promotion to PHYSICAL by relabeling fails closed. This remains an architecture proof, not a physical RF/EM capability claim.

## Current claims boundary

Subject to current-head CI and review, the branch supports an **IMPLEMENTED IN SOFTWARE** claim for the governed-effect contract and same-host POSIX cross-process invocation serialization.

It does **not** establish physical safety certification, flightworthiness, RF/EM performance, propulsion performance, DoD/ATO/FedRAMP/CMMC/IL5/IL6 authorization, classified suitability, multi-host consensus, hardware-enforced non-replay, legal admissibility of evidence, exactly-once event delivery, or exactly-once physical actuation.

## Next assurance gates

1. bind software-release and configuration-custody digests into physical-effect authority;
2. add DDIL preauthorization, expiry, revocation, and rejoin reconciliation;
3. emit a machine-readable CI qualification bundle for the complete governed-effect transaction;
4. add a device-side challenge/grant interlock protocol so a device can reject stale, replayed, or mismatched host commands independently of the ordinary host execution path;
5. demonstrate that interlock first with a benign de-energized or low-energy fixture;
6. treat multi-host authority as a separate distributed-systems problem requiring a single-writer service, transactional database/CAS, or equivalent consensus-capable design.

## Product implication

The reusable Worldshepherd product boundary is increasingly clear:

> **a common policy, human-authority, cryptographic-authority, maturity-control, one-time invocation, exact-action binding, provenance, and replay kernel for heterogeneous software and physical systems.**

Domain intelligence and actuators remain replaceable adapters. Claims remain tied to evidence rather than authorization.
