# Worldshepherd Economic Authorization Gate v0.1

**Status:** DRY-RUN SOFTWARE GATE + G1 DURABLE LEDGER + G2 PRIME SIGNATURE BINDING IMPLEMENTED ON FEATURE BRANCH
**Primary umbrella:** ACTIVE 1/3 — Platform & Assurance (#281)
**Secondary dependency:** ACTIVE 3/3 — Growth & Externalization (#283)

## Purpose

This gate adds a protocol-neutral authorization layer for agent-initiated economic actions without enabling real-money execution.

The implementation is deliberately bounded:

- represent an economic intent independently of a payment rail;
- bind the intent to a bounded session and a canonical policy digest;
- enforce protocol, network, asset, payee, per-transaction, cumulative-budget, expiry, and human-approval controls;
- persist intent, policy, decision, authorization, failure, consumption, and receipt-reference state;
- serialize budget decisions so concurrent decisions cannot silently oversubscribe one policy budget;
- reject consumed-intent and nonce replay;
- maintain a hash-linked local economic event chain for tamper detection;
- fail closed for every `LIVE` payment request;
- perform no wallet access, signing, facilitator call, token transfer, card action, or settlement.

## Architectural boundary

```text
Human authority
      |
      v
PRIME SENTINEL
  policy / authorization
      |
      v
SARA
  intent/workflow
      |
      v
WS Economic Authorization Gate
  pure policy evaluator
      |
      v
G1 Durable Economic Ledger
  replay + policy binding + budget reservation
      |
      +--> x402 adapter       (future)
      +--> AP2 adapter        (future)
      +--> MPP adapter        (future)
      +--> other rails        (future)
      |
      v
ECHO SENTINEL LINK
  semantic evidence/provenance
      |
      v
OVERWATCH
  anomaly/state/financial COP
```

The current implementation stops before every payment adapter.

## Implemented evaluator controls

`worldshepherd_sara/economic_authorization.py` implements:

1. explicit session binding;
2. policy and intent expiry;
3. fail-closed rejection of future-dated intent;
4. explicit protocol allowlist;
5. explicit network allowlist;
6. explicit asset allowlist;
7. explicit payee allowlist;
8. per-transaction amount ceiling;
9. cumulative session-budget ceiling;
10. human-approval requirement;
11. deterministic SHA-256 intent digest;
12. deterministic SHA-256 policy digest with sorted allowlists;
13. unconditional denial of `LIVE` execution.

The evaluator itself has no external side effects.

## G1 — durable replay and budget ledger

`worldshepherd_sara/economic_ledger.py` adds durable SQLite state using the same fail-closed design family already used elsewhere in the verified-local SARA package.

G1 implements:

- unique `intent_id`;
- unique nonce;
- unique intent digest;
- canonical policy digest binding;
- durable decision state;
- durable authorization-result state;
- durable failure state;
- explicit `UNCONSUMED` versus `DRY_RUN_CONSUMED` state;
- optional adapter receipt reference;
- restart-safe idempotency before consumption;
- fail-closed replay after consumption;
- fail-closed nonce reuse across intents;
- policy-ID rebinding detection;
- `BEGIN IMMEDIATE` serialization of decision writes;
- budget reservation from previously allowed intents under the exact same session/policy digest;
- hash-linked local event records with payload-integrity checks;
- symlink/ownership/permissions protections aligned with existing local ledgers.

A dry-run decision that is `ALLOWED` reserves its amount against the bounded session budget. This prevents two concurrently evaluated intents from both relying on the same stale caller-supplied `spent_so_far` value.

`DRY_RUN_CONSUMED` is simulation state only. It does not imply payment, settlement, wallet access, or external provider execution.

## G2 — PRIME SENTINEL signature binding

`worldshepherd_sara/economic_prime_authorization.py` now implements a public-key-only verification boundary for a separate economic authorization assertion.

The signed assertion is bound to:

- authorization ID and one-time authorization nonce;
- intent ID and canonical intent digest;
- policy ID and canonical policy digest;
- session ID;
- protocol, network, asset, and payee;
- exact authorized amount;
- human-approval reference;
- issuance and expiry times;
- PRIME SENTINEL key ID.

The verifier uses the existing PRIME SENTINEL Ed25519 public-key verifier. It has no private signing key and cannot issue an authorization.

The G2 integration helper re-checks the verified intent digest, policy binding, session, and durable `ALLOWED` decision before writing `PRIME_VERIFIED` into the G1 ledger. The ledger then enforces one-time binding of the authorization reference, signed-record digest, and authorization nonce across intents.

A valid signature is necessary but not sufficient: a correctly signed assertion that changes the amount, policy digest, payee, asset, protocol, network, session, intent digest, or approval reference fails closed.

## G3 — ECHO semantic provenance

Emit downstream semantic evidence for:

- intent received;
- policy evaluated;
- decision;
- PRIME assertion verified/rejected;
- adapter request created;
- provider response;
- settlement/denial result;
- artifact or service delivered;
- reconciliation result.

Negative evidence and failed actions must be retained.

## G4 — sandbox adapter

Implement exactly one external sandbox/testnet adapter. The first adapter must:

- contain no production credential;
- use a zero-value or test-only asset;
- prohibit mainnet/production destinations;
- be kill-switchable;
- produce deterministic evidence;
- demonstrate denial on policy mismatch, replay, expired authorization, destination mutation, and amount escalation.

## G5 — cross-protocol conformance

Exercise the same Worldshepherd economic intent against at least two independent rails and prove that Worldshepherd's policy/evidence semantics remain invariant even when the transport/payment representation differs.

The target semantic sequence is:

`INTENT → POLICY → AUTHORITY → EXECUTION → RECEIPT → RECONCILIATION → PROVENANCE`

## Claims boundary

Current feature-branch claim:

**IMPLEMENTED IN SOFTWARE:** protocol-neutral dry-run economic-intent evaluation, canonical policy binding, durable replay protection, serialized session-budget reservation, dry-run consumption state, local hash-linked event evidence, and public-key verification plus durable binding of PRIME economic authorization assertions.

Not currently claimed:

- production payment execution;
- wallet custody;
- production PRIME economic authorization issuance/service deployment;
- x402/AP2/MPP conformance;
- financial-services compliance;
- PCI, SOC, FedRAMP, CMMC, RMF, banking, money-transmitter, or other regulatory certification;
- partner validation;
- production security accreditation.

Those require separate evidence.
