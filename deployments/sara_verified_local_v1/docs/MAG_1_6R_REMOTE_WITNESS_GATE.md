# MAG-1.6R Remote Registry Witness Gate

Status: **IMPLEMENTED IN SOFTWARE / REQUIRES DEPLOYMENT VALIDATION**

MAG-1.6R extends the MAG-1.5 local registry checkpoint journal and the MAG-1.6 signed monotonic witness protocol. Its purpose is to make a consequential PRIME requalification release depend on an exact signed witness of the registry security state from which that release is authorized.

## Threat being addressed

MAG-1.5 detects rollback when either `registry.json` or `registry.checkpoints.jsonl` is restored independently. A privileged actor able to restore both local artifacts coherently can erase the local evidence that a newer generation existed. MAG-1.6 defines a signed monotonic witness receipt that can retain a newer generation outside those two artifacts. MAG-1.6R adds a durable service boundary, authenticated transport, and a transaction precondition that binds the witnessed state to a consequential release.

## Protocol

The witnessed coordinates are:

```text
generation
state_root_sha256
commit_hash
```

The witness signs those coordinates with Ed25519 and chains receipts through `previous_receipt_sha256`. For one namespace, the durable witness ledger enforces:

```text
new generation > head generation       -> advance
new generation == head + same state    -> idempotent
new generation == head + conflict      -> reject
new generation < head                   -> reject as rollback
```

The client pins the expected witness identity, namespace, and signing key. A valid signature alone is insufficient: the receipt must match the exact local generation, state root, and commit hash.

## Consequential-action precondition

MAG-1.6R deliberately avoids remote network I/O while SARA holds the protected registry transaction lock.

```text
1. Read locally verified checkpoint status.
2. Read remote witness head and verify signature + exact coordinates.
3. Construct immutable RegistryWitnessPrecondition.
4. Enter the protected registry transaction.
5. Re-read storage-owned checkpoint metadata under the lock.
6. Exact-compare generation + state root + commit hash against the precondition.
7. If anything changed, fail closed.
8. Only then may PRIME authorization be consumed and custody be released.
```

This closes the time-of-check/time-of-use window for cooperating writers: an intervening registry mutation makes the witness precondition stale rather than silently allowing release from a state that was never witnessed.

The witness receipt hash and a digest of the full witness precondition are bound into the PRIME transition evidence. The transition event also records that witness independence is not established and that the post-transition checkpoint is not yet covered.

## Service boundary

`registry_witness_service.py` provides a durable witness ledger and FastAPI service with:

- service-specific bearer authentication;
- a service-specific Ed25519 signing key;
- persistent SQLite monotonic state;
- restart-stable witness heads;
- signing-key fingerprint binding in ledger metadata;
- authenticated `GET /v1/head`;
- authenticated `POST /v1/witness`;
- structured rollback and conflict responses;
- a public-key identity endpoint; and
- a health endpoint that explicitly reports `independence_verified: false`.

`registry_witness_http.py` requires HTTPS in production. Plain HTTP is accepted only when explicitly enabled for loopback qualification. Responses are bounded and malformed/unexpected responses fail closed.

## What MAG-1.6R proves when its tests pass

It can support the narrow statement:

> Worldshepherd implements a durable signed monotonic registry-witness protocol and can require an exact witnessed pre-transition registry checkpoint before a consequential PRIME requalification release. The protected transaction rejects stale witness preconditions before authorization consumption or custody release.

This is a software/protocol claim. It is not an infrastructure-independence claim.

## What MAG-1.6R does not prove

Do **not** set `external_witnessed=true` or claim independent rollback resistance merely because the witness service is running. The following require separate deployment evidence:

- different administrative control from the SARA host;
- storage outside the SARA rollback/backup domain;
- network-path authenticity and production TLS configuration;
- independent witness-key custody;
- protection of witness signing authority from SARA-host compromise;
- WORM/append-only retention at the infrastructure layer;
- backup and disaster-recovery behavior for the witness ledger;
- availability objectives and outage handling;
- third-party attestation, if claimed; and
- legal chain of custody, if claimed.

A container on the same host, a second process under the same administrator, a second volume included in the same rollback snapshot, or a signed receipt copied back into the same compromise domain does not establish independence.

## Remaining stronger boundary: post-transition witness finalization

MAG-1.6R witnesses the state immediately **before** the protected PRIME release. The registry changes when authorization is consumed, custody becomes READY, and transition evidence is queued. Therefore the resulting generation is not automatically witnessed by the precondition.

The next stronger protocol should make release a two-phase state transition:

```text
QUARANTINED_FOR_REQUALIFICATION
        |
        | verified PRIME + MAG-1 + OVERWATCH + witnessed pre-state
        v
READY_PENDING_WITNESS
        |
        | commit new registry generation
        | obtain signed witness for that exact resulting checkpoint
        | re-verify signed receipt
        v
READY
```

Any external operational effect that depends on READY should remain disabled while the state is `READY_PENDING_WITNESS`. Witness unavailability, signature failure, rollback detection, coordinate conflict, or stale state must leave the system non-finalized and externally inert.

That two-phase post-state finalization is the recommended MAG-1.7 boundary.