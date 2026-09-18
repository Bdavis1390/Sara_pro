# WS-SARA G9E — FAIL-CLOSED STARTUP WITNESS ADMISSION

Status: **IMPLEMENTED ON STACKED BRANCH / PENDING G8 + G9A-D + EXACT-HEAD QUALIFICATION**

## Objective

G9E turns the G9D remote monotonic witness from an operator tool into an optional SARA startup admission control.

When enabled, SARA must prove that its exact current registry checkpoint matches a pinned-key, signed `REMOTE_WITNESS` head before it constructs the PRIME verifier or replays pending governed events.

## Admission order

High-assurance startup order is:

1. validate SARA runtime secrets;
2. open and locally verify durable registry/checkpoint storage;
3. run the G8 PRIME trust-root guard;
4. verify the required G9D remote witness head;
5. construct the PRIME verification-only runtime;
6. replay pending governed outbox events;
7. emit service-start evidence.

A witness rejection stops the sequence at step 4.

## No automatic witness advancement

SARA startup performs **check only**.

It never calls witness advancement automatically.

If local state is newer than the signed witness head, startup fails with bounded reason:

`WITNESS_ADVANCE_REQUIRED`.

The explicit operator flow is:

1. inspect the current checkpoint;
2. review the intended local change;
3. run `ws-registry-witness advance --data-dir <SARA_DATA_DIR>`;
4. verify the signed witness now covers the exact checkpoint;
5. restart SARA.

This asymmetry prevents an older or attacker-crafted local state from blessing itself merely because SARA can reach the witness service.

## Fail-closed reasons

The startup gate emits bounded reason codes rather than copying remote exception text into audit evidence:

- `WITNESS_REQUIREMENT_INVALID`;
- `WITNESS_CONFIGURATION_INVALID`;
- `LOCAL_REGISTRY_ROLLBACK_DETECTED`;
- `REGISTRY_WITNESS_CONFLICT`;
- `REGISTRY_WITNESS_UNAVAILABLE`;
- `WITNESS_VERIFICATION_FAILED`;
- `WITNESS_ADVANCE_REQUIRED`;
- `WITNESS_MODE_INVALID`;
- `WITNESS_SIGNATURE_UNVERIFIED`;
- `WITNESS_MONOTONIC_MISMATCH`.

## Required witness semantics

A passing startup witness must have:

- status `PASS`;
- mode `REMOTE_WITNESS`;
- pinned-key signature verified;
- exact monotonic match to the local checkpoint.

The test-only in-process witness can never satisfy required startup admission.

## Qualification

Unit tests prove:

- disabled mode does not even load a witness client;
- exact remote witness passes;
- locally newer state requires explicit advance and never auto-advances;
- newer remote head maps to local rollback rejection;
- test-only witness mode fails;
- malformed requirement values fail closed;
- cryptographic/protocol failures map to bounded reason codes;
- startup order is G8 guard -> G9E witness -> PRIME verifier -> replay;
- witness rejection prevents verifier construction and replay.

The dedicated G9D/G9E qualification additionally exercises the actual SARA lifespan against the TLS witness container:

1. witness initial registry generation 0;
2. start SARA successfully with required witnessing;
3. mutate local registry to generation 1;
4. prove restart fails with `WITNESS_ADVANCE_REQUIRED`;
5. explicitly advance the witness;
6. prove restart succeeds at generation 1.

## Claims boundary

A G9E PASS can establish **internally verified fail-closed startup enforcement against a configured signed remote witness**.

It does not, by itself, establish that the witness is independently administered, in a separate backup/rollback domain, WORM-retained, highly available, hardware-key-backed, FIPS validated, or third-party operated.

Those are deployment-evidence requirements.

`external_witnessed` and `independence_verified` remain false in same-runner CI.
