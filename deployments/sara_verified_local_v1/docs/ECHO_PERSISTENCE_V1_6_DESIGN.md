# ECHO SENTINEL LINK Persistence v1.6

## Purpose

v1.6 closes the reference-software gap between SARA's durable AT_LEAST_ONCE event outbox and a separately persisted downstream provenance consumer. It does not change the custody state machine, PRIME SENTINEL authorization semantics, or any physical-system maturity.

## Source contract

SARA remains the authority that creates the stable outbox event ID. Delivery to the SARA audit log embeds that ID in `payload._outbox_event_id` and declares `payload._delivery_semantics = AT_LEAST_ONCE`.

An outbox retry may create a new audit transport timestamp for the same semantic event. ECHO therefore defines semantic identity as:

- stable `_outbox_event_id`;
- `event`;
- `actor`;
- canonical JSON `payload`.

The audit transport `timestamp` is intentionally excluded from the semantic hash. This permits legitimate AT_LEAST_ONCE replay while still detecting same-ID/different-content conflicts.

## Service boundary

ECHO runs as a separate optional Compose service with:

- its own `/var/lib/echo` named volume;
- read-only root filesystem;
- dedicated loopback-only host port;
- dedicated Docker bridge not shared with SARA;
- an independent bearer credential supplied only through a mode-restricted read-only secret file;
- no SARA admin or relay credential;
- no SARA data mount;
- no PRIME SENTINEL private key, signer token, or signer data mount.

The reference integration harness mediates transfer from SARA's authenticated audit API to ECHO. ECHO does not receive a SARA credential merely to prove persistence.

## Durable deduplication

The reference store uses SQLite with `synchronous = FULL`, transaction serialization through `BEGIN IMMEDIATE`, a mode-0700 service-owned data directory, and a mode-0600 database.

For a new stable event ID, ECHO stores one semantic record containing the canonical semantic SHA-256, event, actor, payload, first/last audit timestamps, first/last ingestion timestamps, and delivery count.

For an existing stable event ID:

- same semantic hash: increment delivery count and update last-seen metadata; return `DEDUPLICATED`;
- different semantic hash: preserve the original record, record the rejected conflict, and return HTTP 409.

The implementation is bounded to 4,096 semantic events in this reference profile. Hitting capacity fails closed rather than silently discarding provenance.

## Integrity and readiness

Readiness requires SQLite `quick_check` plus semantic-row integrity recomputation. Every stored record is reconstructed as an audit record and its stable event ID and semantic SHA-256 are recomputed. A mismatch makes readiness fail.

Recorded rejected conflicts are observable but do not themselves corrupt or overwrite accepted semantic state.

This is local integrity checking. It is not immutable/WORM storage, authenticated timestamping, remote notarization, or third-party attestation.

## Reconciliation

The reconciliation endpoint compares a caller-supplied SARA audit window to durable ECHO state and classifies stable event IDs as:

- `MATCHED`;
- `SARA_ONLY`;
- `ECHO_ONLY`;
- `PAYLOAD_MISMATCH`.

Reconciliation is explicitly `PROVIDED_SARA_AUDIT_WINDOW` scoped. SARA audit queries and retained outbox entries are bounded, so a window comparison is not evidence of globally complete historical delivery.

## Protected integration gate

The v1.6 deployment gate must prove on the exact protected CI head:

1. SARA and ECHO are separate containers, networks, credentials, and persistent volumes.
2. SARA produces a real governed PRIME custody provenance event and delivers it to the audit log with a stable outbox ID.
3. ECHO stores the event once.
4. Exact replay is deduplicated.
5. ECHO restart preserves the stored semantic event.
6. Replay after restart with a different transport timestamp is still deduplicated.
7. Same stable event ID with mutated semantic content is rejected with HTTP 409 and does not replace the accepted event.
8. Window-scoped SARA/ECHO reconciliation classifies the accepted event as `MATCHED`.
9. An evidence record is included in the normal deployment-evidence bundle.

## Claims boundary

A passing v1.6 gate may support `IMPLEMENTED IN SOFTWARE` for the reference separately deployed ECHO persistence service, stable-event-ID semantic deduplication, restart persistence, local integrity checks, and bounded SARA/ECHO reconciliation.

It does **not** establish exactly-once transport, immutable/WORM retention, independent external attestation, production security certification, customer/government authorization, or any physical PRIME, PUMI, PSDM, AERO, HADAL, SPACE, carrier, launch, orbital, lunar, asteroid, or other hardware qualification.
