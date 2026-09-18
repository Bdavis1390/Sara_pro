# WS-SARA G9C — SIGNED MONOTONIC REGISTRY WITNESS PROTOCOL

Status: **IMPLEMENTED ON STACKED BRANCH / PENDING G8 + G9A + G9B + EXACT-HEAD QUALIFICATION**

## Purpose

G9C closes the specific local rollback class that G9B intentionally cannot close:

> restoring both `registry.json` and `registry.checkpoints.jsonl` together to an older, internally coherent generation.

A retained newer signed witness provides an out-of-band monotonic reference for:

`generation + state_root_sha256 + commit_hash`.

## Protocol

The generic witness receipt is Ed25519-signed and domain separated.

It binds:

- witness identity;
- witness key ID;
- namespace;
- generation;
- registry state-root SHA-256;
- checkpoint COMMIT hash;
- previous witness-receipt digest;
- witness mode;
- issuance time.

The verifier requires a separately configured pinned witness public key and expected witness identity/namespace.

## Monotonic semantics

- lower generation than witness head -> rollback;
- same generation + different state root or commit hash -> conflict;
- same generation + exact coordinates -> idempotent match;
- local generation newer than witness -> `NEEDS_WITNESS_ADVANCE`;
- unpinned key or invalid signature -> fail closed;
- unavailable required witness head -> fail closed.

## G8 integration proof

The stack contains a dedicated regression:

1. initialize PRIME trust-root epoch 1;
2. retain the epoch-1 registry + checkpoint journal bytes;
3. rotate to epoch 2 with a new key ID and explicit old-key revocation;
4. witness the resulting newer checkpoint;
5. coherently restore both local files to epoch 1;
6. reopen SARA storage and prove G9B accepts the restored self-consistent local history;
7. compare that restored checkpoint to the retained newer signed witness;
8. require `RegistryWitnessRollbackDetected`.

This demonstrates the precise boundary G8 and G9B cannot close alone.

## Test-only transport discipline

The current deterministic witness transport is in-process and marked:

`TEST_ONLY_IN_PROCESS`.

Passing receipts from this transport must keep:

- `external_witnessed=false`;
- `independence_verified=false`.

A signature does not by itself prove deployment independence.

## Claims boundary

A PASS establishes:

**PROVEN INTERNALLY — signed monotonic witness protocol detects older-generation and same-generation conflicting local registry states relative to a retained pinned-key witness receipt.**

It does not establish:

- independently administered witness service;
- external hosting;
- witness availability objective;
- WORM retention;
- independent storage/backup domain;
- HSM/KMS custody of witness signing keys;
- FIPS validation;
- external timestamp authority;
- protection if both SARA and the witness trust root are compromised;
- third-party validation.

## Next gate — G9D

Promote the already-developed remote witness transport/service substrate onto this clean stack:

- durable witness ledger;
- HTTPS transport with authenticated server identity;
- pinned local witness public-key record + independently configured expected fingerprint;
- bearer-authenticated client;
- restart persistence;
- remote rollback/conflict rejection;
- no caller-selectable bypass.

Only a deployment in a genuinely separate administrative and rollback domain can promote `external_witnessed` or `independence_verified`.
