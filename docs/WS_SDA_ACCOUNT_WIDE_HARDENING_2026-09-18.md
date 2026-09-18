# WS-SDA Account-Wide Hardening Synthesis — 2026-09-18

Status: **IMPLEMENTATION UPDATE FROM ACCOUNT-WIDE WORK, PAST WEEK**
Scope: Worldshepherd / SARA Pro work developed across the account during 2026-09-11 through 2026-09-18.

## Purpose

This update imports the strongest reusable controls from parallel Worldshepherd work
into the WS-SDA trust fabric rather than treating SDA as an isolated project.

The governing rule remains:

> AI proposes -> evidence supports -> PRIME bounds authority -> SARA executes bounded
> workflow -> ECHO preserves provenance -> OVERWATCH exposes state -> identified
> human authority remains decisive.

No cross-project idea is promoted merely because it appeared elsewhere. Controls are
carried over only when their semantics are useful to SDA and their claims boundary
remains explicit.

## 1. Durable side-effect fencing imported from bounded-action work

Recent bounded-action work established a stronger transaction model:

```text
VERIFIED -> CLAIMED -> INVOKING -> CONSUMED
                                -> INDETERMINATE
```

The important security lesson is not the labels themselves. It is that an ambiguous
external outcome must not be silently retried.

WS-SDA now imports that rule in `sda_release_fence.py`.

Properties:

- persistent SQLite transaction boundary;
- `BEGIN IMMEDIATE` serialization across processes sharing the database;
- exact candidate digest bound before claim;
- exact candidate rechecked before invocation;
- claim-owner and claim-token binding;
- short claim lease only before invocation;
- durable `INVOKING` transition before the caller performs the external side effect;
- acknowledgement-loss / ambiguous outcome becomes `INDETERMINATE`;
- `INDETERMINATE` and `CONSUMED` cannot be automatically reclaimed or retried;
- restart persistence;
- semantic-integrity health checks;
- transition history.

This closes the earlier G6 caveat that one-time behavior was only as strong as the
caller's in-memory transaction boundary.

It still does **not** establish distributed consensus, external delivery, or a
globally exactly-once network effect.

## 2. Connector-control lessons carried into SDA identity and release paths

Parallel connector-control work emphasized:

- default-deny policy;
- one-time, short-lived authorization;
- context/action binding;
- role/data-class ceilings;
- no ambient authority;
- evidence receipts without raw secrets;
- ambiguous outcome handling.

WS-SDA already uses these principles in G2 workload/transport identity and G6 signed
release authorization. The durable release fence now extends them across the
side-effect boundary so authorization cannot silently turn into duplicate execution.

## 3. ECHO / QCRYPTO delivery-recovery lessons carried into G7

Parallel SARA->ECHO and QCRYPTO work hardened:

- replay-safe delivery;
- partial-delivery recovery;
- acknowledgement-loss handling;
- deduplication;
- retained-history reconciliation;
- signed checkpoints;
- explicit separation between classical Ed25519 integrity and post-quantum claims.

WS-SDA G7 therefore treats DDIL/rejoin evidence as **at-least-once evidence
transport**, not globally exactly-once delivery.

Same-origin semantic mutation remains visible as conflict. Rejoin disagreement is
not overwritten by local clock/authority preference.

## 4. Signer isolation and trust-root rollback lessons carried into G10

Recent ECHO/PRIME hardening separated signing from general application authority and
added rollback protection around trust roots.

G10 adopts the same security posture:

- evaluator signature validity is distinct from evaluator identity;
- evaluator key fingerprint is bound into the assertion;
- exact source/artifact digests are signed;
- a cryptographically valid Worldshepherd-controlled self-run cannot count as
  independent reproduction;
- trust/key identity must remain separately evidenced.

Hardware-backed or independently administered external evaluator key custody is
still a separate validation target and is not claimed here.

## 5. Non-compensatory assurance from autonomy-promotion and qualification work

Parallel autonomy-promotion and qualification work repeatedly established that
critical assurance dimensions should not be averaged into a single score.

WS-SDA imports that directly:

- G8 mandatory false-negative budget = 0;
- G9 requires every mandatory security dimension to pass independently;
- baseline-zero properties remain zero-invariants;
- one failed security dimension blocks the 10x result;
- one failed mandatory utility dimension also blocks the result;
- intentionally weak/reference baselines cannot create claim eligibility;
- G10 requires independent reproduction rather than score aggregation.

This is the same underlying discipline used elsewhere in Worldshepherd for
PASS/FAIL/HOLD-INDETERMINATE decisions and evidence-maturity promotion.

## 6. Evaluator-portability lessons carried into G9/G10

Recent exact-SHA evaluator work exposed a real portability defect, which was useful
because it demonstrated why a benchmark must be executable outside its authoring
environment.

WS-SDA therefore binds G9/G10 to:

- exact source commit;
- exact frozen workload digest;
- exact protocol digest;
- explicit environment identity;
- raw evidence references;
- independent execution for G10.

A benchmark that works only in the originating environment is not sufficient for the
external-reproduction gate.

## 7. DARC/BMC3I capture lessons carried into the partner evidence package

Recent DARC/BMC3I work converged on a practical demonstration package that shows not
only success, but governed failure behavior.

For an SDA partner/customer demonstration, the evidence package should include:

```text
successful bounded analytic flow
denied unauthorized action
degraded/stale-data handling
conflicting-source handling
audit/evidence replay
release-authorization replay rejection
ambiguous-outcome / no-auto-retry demonstration
SBOM evidence
vulnerability/advisory evidence
secret-isolation evidence
backup/restore evidence
interface-control note
claims matrix
exact source commit
exact test-workload digest
```

This positions Worldshepherd as the governed integration/evidence layer rather than
claiming to replace partner radar, RF, EO, orbital-analysis, APNT, or other sensing
hardware.

## 8. Physical/scientific claims discipline carried into SDA

The same claims-control discipline used in QMAT, BAROS, programmable materials,
PQC, and other Worldshepherd lanes applies here:

- software does not prove hardware;
- simulation does not prove operational performance;
- literature does not prove a deployed capability;
- internal CI does not equal partner validation;
- signed evidence does not equal certification;
- external outreach does not equal customer acceptance;
- prediction does not upgrade maturity;
- negative evidence is retained.

Consequently, WS-SDA does not currently claim:

- operational orbit determination;
- fielded sensor fusion;
- certified PNT/APNT;
- classified-network authorization;
- government accreditation;
- universal 10x security;
- external independent reproduction.

## 9. Updated SDA assurance ladder

```text
G1   canonical provenance-bound observation
G2   workload + transport identity
G3   adapter/process/container isolation
G4   bounded CCSDS interoperability
G5   conflict-preserving multi-hypothesis analysis
G6   signed human-bound analytic release
G6B  durable cross-process release execution fence
G7   DDIL/rejoin/ECHO/replay
G8   frozen adversarial/fault corpus
G9   historical-baseline 10x measurement protocol
G10  externally signed independent reproduction
```

G6B is the principal new implementation created from the account-wide synthesis.

## 10. Evidence boundary

This document is an architecture/control synthesis. Each imported control retains
its original evidence maturity.

The existence of a control in another Worldshepherd lane does not automatically make
the SDA implementation proven. SDA-specific code must pass its exact-head tests and
protected integration gates before promotion.

External replication, partner validation, hardware validation, accreditation and
certification remain separate gates.
