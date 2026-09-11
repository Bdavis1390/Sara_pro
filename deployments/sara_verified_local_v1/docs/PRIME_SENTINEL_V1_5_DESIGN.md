# PRIME SENTINEL v1.5 — signer-side durable issuance provenance

Status: DESIGN GATE / IMPLEMENTATION IN PROGRESS

v1.5 closes the issuance-side durability gap left intentionally after v1.4. SARA already records accepted/verified/consumed authorization state; the independent PRIME SENTINEL signer must now persist issuance intent and signed assertions independently before returning them to a caller.

## Required semantics

- Caller supplies a bounded opaque request ID for idempotency.
- PRIME SENTINEL durably stores a PREPARED record before signing.
- PREPARED includes stable authorization ID, nonce, issue/expiry times, PRIME ID, target environment, key ID, and request parameters.
- Ed25519 signing uses that already-persisted canonical message.
- PRIME SENTINEL durably promotes the same record to SIGNED before returning an assertion.
- Retrying the same request ID with the same request returns the same signed assertion.
- Reusing a request ID with different parameters is rejected.
- A crash after PREPARED but before SIGNED recovers the same authorization identity rather than minting a second authorization.
- Persistence failure is fail-closed: no newly issued assertion is returned unless its SIGNED state is durable.
- The signer ledger contains no private-key or bearer-token material.

## Reference persistence

The reference localhost/container profile uses a signer-owned SQLite database on a separate persistent volume. Transactions use SQLite durability primitives and are independent of SARA's registry/audit files. An integrity-checkable event chain records issuance lifecycle transitions, but it is not represented as immutable, WORM, externally attested, or resistant to an attacker with full signer-host write authority.

## Reconciliation

A reconciliation utility compares signer SIGNED records with SARA authorization state and classifies each authorization as ISSUED_NOT_PRESENTED, VERIFIED, CONSUMED, SUPERSEDED, or inconsistent. Reconciliation is observational; the signer must not mutate SARA state to make records agree.

## Validation gates

Tests must cover durable restart recovery, same-request deterministic retry, conflicting idempotency reuse, PREPARED-write failure, SIGNED-write failure, crash-window recovery, malformed/corrupt persistence, bounded retention, event-chain verification, absence of secrets from the ledger, and two-container reconciliation against SARA.

Claims boundary: passing v1.5 can support IMPLEMENTED IN SOFTWARE status for signer-side durable issuance provenance and reconciliation in the reference deployment. It cannot establish HSM/KMS custody, hardware-backed non-exportability, dual-control/M-of-N approval, immutable external audit, regulatory certification, customer/government acceptance, or any physical PRIME qualification.
