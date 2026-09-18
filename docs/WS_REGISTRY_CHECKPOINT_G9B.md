# WS-SARA G9B — HASH-CHAINED REGISTRY CHECKPOINT JOURNAL

Status: **IMPLEMENTED ON STACKED BRANCH / PENDING G8 + G9A + EXACT-HEAD QUALIFICATION**

## Purpose

G9B makes SARA registry writes crash-recoverable and locally rollback-detectable before introducing an external witness.

It layers on G9A's cross-process registry serialization.

## Storage protocol

The store maintains:

- `registry.json`;
- `registry.lock`;
- `registry.checkpoints.jsonl`.

The registry carries storage-owned checkpoint metadata:

- generation;
- current state-root SHA-256;
- last committed checkpoint-record hash.

The journal is an append-only hash chain of:

- `GENESIS`;
- `PREPARE`;
- `COMMIT`;
- `ABORT`.

## Transaction ordering

For a registry mutation:

1. verify current registry against the checkpoint journal;
2. derive the next state root and deterministic checkpoint records;
3. fsync `PREPARE`;
4. atomically replace `registry.json` with metadata bound to the expected `COMMIT`;
5. fsync `COMMIT`.

On restart or protected access, an incomplete `PREPARE` is deterministically classified:

- old registry still present -> append `ABORT`;
- new registry already replaced -> append the deterministic `COMMIT`;
- any other state -> fail closed.

## Security invariants

- checkpoint metadata is storage-owned and cannot be supplied through registry patch/transaction callbacks;
- journal records are canonical JSON and SHA-256 hash chained;
- sequence/generation/predecessor continuity is verified;
- registry state root must match committed journal state;
- journal line and total-size limits are bounded;
- symlinked journal paths fail secure where no-follow semantics are available;
- reads may complete deterministic recovery while holding G9A's exclusive process lock.

## Focused qualification

The required regression suite covers:

1. generation commit and older-registry rollback detection;
2. recovery of PREPARE-before-registry-replacement as ABORT;
3. recovery of registry-replaced-before-COMMIT-append as COMMIT;
4. record tamper / broken hash chain;
5. every store write receiving a checkpoint generation;
6. rejection of caller-written storage metadata;
7. restoring an older registry while retaining the newer journal;
8. deleting the journal from a checkpointed registry;
9. symlinked journal rejection.

## Claims boundary

A PASS establishes **local hash-chained registry integrity and deterministic crash recovery inside one persistence domain**.

It does not establish:

- resistance to coherent rollback of both `registry.json` and `registry.checkpoints.jsonl`;
- external timestamping;
- external or independent witnessing;
- WORM retention;
- distributed consensus;
- protection from deletion/restoration of the entire local persistence volume;
- hardware-backed monotonic counters.

## Next gate

G9C binds the checkpoint tuple:

`generation + state_root_sha256 + commit_hash`

to a pinned-key signed monotonic witness.

The explicit G9C negative control is coherent rollback of both local registry and local journal: G9B alone accepts that restored coherent history; the retained newer witness must reject it.
