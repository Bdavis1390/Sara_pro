# MAG-1.4 — Cryptographic OVERWATCH Pre-Commit Containment

## Status

**IMPLEMENTED IN SOFTWARE — exact-commit CI and external validation remain required.**

MAG-1.4 changes OVERWATCH from an observability concept into a bounded software containment authority at one concrete consequential boundary: PRIME requalification release.

The core invariant is:

> A current, valid OVERWATCH HOLD observed inside the same protected registry transaction as a PRIME requalification attempt prevents authorization consumption and custody release.

Containment is therefore evaluated **before the consequential state transition**, not reported after it.

## Authority separation

The release path now requires the absence of an independent negative authorization in addition to the existing positive authority chain:

```text
PRIME SENTINEL signed positive authority
                |
                v
MAG-1 purpose/scope/trajectory/autonomy gates
                |
                v
OVERWATCH signed containment state  ---- HOLD ----> STOP
                |
              CLEAR / no directive
                |
                v
PRIME custody release gate
                |
                v
consume one-time PRIME authority + release custody + queue evidence
```

A model-generated summary, candidate payload, trajectory text, or caller-selected flag cannot declare the OVERWATCH state. The consequential transition reads the persisted signed containment chain from the registry snapshot protected by `DurableStore.transact_registry()`.

## Signed containment directives

`overwatch_containment.py` defines `WS-OVERWATCH-CONTAINMENT-V1` directives with:

- Ed25519 signatures;
- a fixed issuer (`OVERWATCH`);
- a fixed consequential action (`REQUALIFICATION_RELEASE`);
- PRIME identity;
- target environment;
- `HOLD` or `CLEAR` state;
- monotonic sequence number;
- predecessor signed-directive SHA-256;
- bounded reason code;
- issuance and expiry timestamps;
- nonce;
- one or more distinct signer key IDs.

The signed canonical message excludes the signatures themselves. A separate signed-directive hash commits to the canonical message plus the complete sorted signature set and becomes the predecessor anchor for the next directive.

## Asymmetric quorum policy

Containment deliberately makes recovery harder than stopping:

- default `HOLD` quorum: **1** configured signer;
- default `CLEAR` quorum: **2 distinct** configured signers.

These quorums are verifier configuration, not fields a caller can lower in a directive.

Environment controls:

- `OVERWATCH_CONTAINMENT_PUBLIC_KEYS_JSON`
- `OVERWATCH_CONTAINMENT_REVOKED_KEY_IDS`
- `OVERWATCH_CONTAINMENT_HOLD_QUORUM`
- `OVERWATCH_CONTAINMENT_CLEAR_QUORUM`

This is a software dual-control primitive. It does not by itself prove that two signatures correspond to two different human beings; key custody and organizational identity remain deployment responsibilities.

## Sequence and replay protection

For a PRIME containment chain:

```text
sequence 1 HOLD
prev = null
hash = H1

sequence 2 CLEAR
prev = H1
hash = H2

sequence 3 HOLD
prev = H2
hash = H3
```

A new directive is accepted only when its sequence is exactly the previous sequence plus one and its predecessor hash matches the currently verified signed directive.

This rejects tested stale replay and predecessor-substitution attempts.

The issuance window is limited to 15 minutes so a signed but never-applied directive cannot be introduced indefinitely later. Once accepted, the containment state persists beyond that issuance window until a new valid chained directive supersedes it. Stored directives are cryptographically revalidated when the consequential transition evaluates them; signature/key revocation failures fail closed.

## Protected containment installation

`apply_overwatch_containment_directive()` verifies and commits a directive through `DurableStore.transact_registry()`.

On supported POSIX deployments with MAG-1.3, a cooperating process installing a HOLD and a cooperating process attempting PRIME release serialize through the same `registry.lock`. The winner of that serialization boundary determines the observed state; there is no independent stale read outside the transaction.

Containment installation intentionally does **not** depend on audit/outbox capacity. An emergency HOLD must not be rejected merely because telemetry storage is full. The complete signed directive remains persisted evidence, and any later consequential action blocked by it queues a dedicated containment-block event.

## PRIME transition behavior

If MAG-1 would otherwise permit automatic execution, the transition evaluates the latest OVERWATCH state before binding custody release authorization.

For an active valid HOLD:

- result disposition becomes `CONTAINED`;
- PRIME authorization remains `VERIFIED`, not `CONSUMED`;
- custody remains `QUARANTINED_FOR_REQUALIFICATION`;
- no transition ID is produced;
- no PRIME transition event is produced;
- MAG-1 decision evidence is queued;
- a deterministic `overwatch_containment_block` event is queued;
- the block event commits to the directive hash, containment snapshot, PRIME authorization ID, trajectory/action identity, and pre-transition custody hash.

For a valid CLEAR or no containment directive, the release path may continue through the existing custody gate. The transition ID and transition evidence include a hash of the exact OVERWATCH snapshot observed inside the protected transaction.

## Fail-closed behavior

Once persisted containment state exists for the PRIME, the consequential path requires an OVERWATCH verifier. The transition fails closed when it encounters:

- missing verifier configuration;
- malformed containment records;
- malformed stored signed directive;
- unknown signing key;
- revoked signing key;
- invalid Ed25519 signature;
- metadata/signature disagreement;
- action mismatch;
- invalid chain sequence or predecessor when applying a new directive.

A fail-closed error occurs before PRIME authorization consumption or custody release.

## Regression coverage

The MAG-1.4 fixtures cover:

- one-signature HOLD acceptance;
- HOLD becoming an actual pre-commit transition veto;
- authorization remaining unconsumed under containment;
- custody remaining quarantined under containment;
- deterministic containment-block evidence;
- two-signature CLEAR requirement;
- successful transition after a valid dual-signed CLEAR;
- exact CLEAR directive hash/sequence binding into transition evidence;
- stale replay rejection;
- predecessor substitution rejection;
- persisted directive tamper detection;
- revoked-key fail-closed behavior;
- missing-verifier fail-closed behavior;
- expired unapplied directive rejection.

## Claims boundary

MAG-1.4 supports a narrow software claim: cryptographically authenticated, sequence-bound OVERWATCH containment can veto the implemented PRIME requalification transition before its protected registry effects commit.

MAG-1.4 does **not** establish:

- a physical emergency-stop circuit;
- hardware interlock certification;
- that every consequential Worldshepherd action is routed through this gate;
- identity proof for the humans controlling signing keys;
- compromise resistance if the required quorum of private keys is stolen;
- protection against deletion or rollback of the entire registry by a privileged host administrator;
- distributed consensus or cross-host atomicity;
- complete AI alignment;
- calibrated trajectory-risk probabilities;
- production or third-party safety certification.

## Next assurance gate

The next major gate should remove the remaining host-local rollback ambiguity by binding protected registry generations and OVERWATCH/PRIME transition state to an append-only cryptographic checkpoint that is externally anchored or independently witnessed.

That would move the assurance question from only:

> “Was this transition authorized at the moment it committed?”

also toward:

> “Can a later privileged rollback make the system forget that the containment or transition ever existed?”
