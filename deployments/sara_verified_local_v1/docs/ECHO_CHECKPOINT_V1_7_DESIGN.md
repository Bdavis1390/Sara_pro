# ECHO SENTINEL LINK checkpointing v1.7

## Purpose

v1.7 adds cryptographically signed, predecessor-linked checkpoints over the semantic provenance records already accepted by the independently deployed ECHO SENTINEL LINK persistence service. The checkpoint layer is a reference software custody mechanism. It does not convert local SQLite persistence into immutable storage and it does not promote any physical PRIME capability.

## Input identity and ordering

ECHO continues to consume SARA audit deliveries with `payload._outbox_event_id` as the stable event identity and `_delivery_semantics=AT_LEAST_ONCE`. The semantic digest excludes the transport timestamp and covers the stable semantic content (`event`, `actor`, and `payload`), so a legitimate replay can be deduplicated even if its delivery timestamp changes.

A checkpoint includes the current accepted ECHO semantic records sorted strictly by stable event ID. Each membership record contains a contiguous ordinal, event ID, and semantic SHA-256 digest. A Merkle root is calculated over those membership records.

## Monotonic checkpoint chain

Checkpoint sequence begins at 1. Every checkpoint after the first includes the SHA-256 digest of the immediately preceding signed checkpoint manifest. Before a new checkpoint can be created, every event ID/digest present in the predecessor must still be present unchanged. Deletion or substitution of previously checkpointed semantic provenance therefore blocks forward checkpoint creation in the reference service.

This is monotonic local evidence, not rollback-proof storage. A privileged actor able to restore both the database and signing-key state to an earlier valid snapshot is outside this v1.7 guarantee.

## Separate signing identity

Checkpoint signing uses a dedicated Ed25519 ECHO audit/checkpoint key supplied by `ECHO_CHECKPOINT_PRIVATE_KEY_FILE` and identified by `ECHO_CHECKPOINT_KEY_ID`. This key is separate from the PRIME SENTINEL authorization-signing key and from SARA bearer credentials.

The reference container profile mounts the checkpoint private key read-only into ECHO only. SARA and PRIME SENTINEL receive neither the checkpoint key file nor ECHO's persistence volume. The key loader requires an absolute non-symlink regular file, service-UID ownership, no group/other permissions, bounded size, secure open consistency, unencrypted PEM, and Ed25519 key type.

The checkpoint database binds a key ID to its public-key SHA-256 fingerprint and refuses to rebind the same key ID to different key material.

## Portable checkpoint bundle

A checkpoint bundle contains:

- checkpoint schema and sequence;
- checkpoint ID and creation timestamp;
- predecessor checkpoint digest;
- deterministic event membership;
- event count and Merkle root;
- ECHO checkpoint key ID and public-key fingerprint;
- Ed25519 signature over canonical manifest bytes;
- public-key record for portability;
- SHA-256 digest of the canonical manifest.

The private key is never part of the bundle or public service response.

## Independent verification rule

`ws-echo-checkpoint-verify` verifies checkpoint bundles outside the ECHO service. A bundle is **not** trusted solely because its embedded public key validates its signature. The verifier requires a separately supplied expected public-key SHA-256 fingerprint and fails unless the actual public key, bundled fingerprint, manifest fingerprint, and expected fingerprint all match.

The verifier checks schema, signing algorithm, key purpose, key binding, sequence, predecessor digest, event ordering and uniqueness, contiguous ordinals, semantic digest format, Merkle root, manifest digest, Ed25519 signature, contiguous chain sequence, predecessor linkage, and monotonic membership across checkpoints.

## Stored-ledger integrity

ECHO readiness and authenticated status run a local checkpoint-ledger integrity check. The checker verifies SQLite `quick_check`, checkpoint schema metadata, signing-key binding, contiguous stored sequences, stored bundle and manifest consistency, portable signature verification, row-field equivalence, membership-table equivalence, and the complete predecessor chain.

A checkpoint ledger inconsistency makes the reference service not ready and prevents creation of another checkpoint.

## Protected validation gate

The v1.7 integration gate must demonstrate on the exact candidate commit:

1. ECHO ingest token, checkpoint private key, and ECHO data volume are absent from SARA; SARA and ECHO share no Docker network.
2. A real SARA provenance event is ingested into ECHO and an exact semantic replay is deduplicated.
3. Checkpoint 1 is created, ECHO is restarted, and the exported checkpoint is recovered unchanged.
4. Replay after restart with a changed transport timestamp remains a semantic duplicate.
5. A second real SARA provenance event is ingested and checkpoint 2 includes both semantic records while linking to checkpoint 1.
6. The independent CLI verifies the two-checkpoint chain against a fingerprint calculated outside ECHO from the provisioned public key.
7. Deleted, reordered, substituted, bad-signature, bad-predecessor, and key-binding tamper cases are all rejected.
8. Same-stable-ID/different-semantic-content ingestion remains rejected.
9. Window-scoped reconciliation reports the supplied matching event as `MATCHED` and the second stored event outside that supplied window as `ECHO_ONLY`.
10. The normal protected deployment, recovery, release-identity, and release-evidence-index gates still pass.

## Promotion boundary

After protected exact-head CI passes and the reviewed change is merged, the following may be labeled `IMPLEMENTED IN SOFTWARE` for the reference deployment:

- dedicated ECHO checkpoint signing identity and secret isolation;
- deterministic signed semantic checkpoints;
- predecessor-linked monotonic checkpoint chain;
- restart-persistent checkpoint storage;
- local checkpoint-ledger integrity checking;
- portable bundle export;
- independently pinned-key bundle and chain verification;
- tested rejection of the defined deletion, reordering, substitution, signature, predecessor, and key-binding tamper cases.

The following remain **NOT CURRENTLY CLAIMED** by v1.7:

- immutable or WORM retention;
- external timestamping or transparency-log anchoring;
- independent third-party attestation;
- privileged database/key rollback resistance;
- production HSM/KMS or hardware-backed checkpoint-key custody;
- exactly-once transport;
- legal chain-of-custody status;
- customer/government authorization or certification;
- physical PRIME, PUMI, PSDM, AERO, HADAL, SPACE, carrier, launch, orbital, lunar, asteroid, or other hardware qualification.
