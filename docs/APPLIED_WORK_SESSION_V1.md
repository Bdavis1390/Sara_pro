# Worldshepherd Applied Work Session v1

## Purpose

Applied Work Accounting v1 defines what may be measured and how non-equivalent quantities may be related. Applied Work Session v1 adds custody for those measurements.

A session binds prospective work evidence to:

- an exact 40-character Git source commit;
- a build/run identity;
- a collector identity;
- timezone-aware start/end timestamps;
- hashed evidence artifacts;
- native work quantities and explicit cross-kind models;
- an append-only event hash chain; and
- a deterministic session seal digest.

## Strong-evidence rule

A quantity or model classified as `MEASURED` or `BENCHMARKED` cannot be recorded in a session unless it references at least one registered evidence artifact carrying a SHA-256 digest.

This does not prove that the instrument or benchmark was correct. It prevents strong evidence labels from existing inside the session with no hashed evidence object behind them.

## Event chain

Each session event records:

- sequence number;
- event type;
- subject ID;
- canonical payload SHA-256;
- predecessor event SHA-256; and
- event-envelope SHA-256.

The supported event types currently include:

- `EVIDENCE_RECORDED`;
- `QUANTITY_RECORDED`;
- `MODEL_RECORDED`; and
- `QUANTITY_DERIVED`.

Reordering, deleting, or modifying an event without resealing breaks verification.

## Semantic work accounting

The session layer does not create a universal work scalar.

The underlying ledger still preserves compute, energy, resource-time, duration, labor-time, data, cost, mass, output, emissions, and quality as distinct quantity kinds. Same-kind/same-basis unit conversion remains separate from evidence-bearing transformation models.

## Seal

A sealed session hashes:

- session identity and subject;
- exact source commit;
- build/collector identity;
- time window;
- event count and chain tip;
- evidence/model/quantity counts; and
- the native ledger vector.

After sealing, the in-memory session refuses mutation.

## Verification

`verify_manifest()` recomputes the event payload hashes, event chain, timestamp rules, strong-evidence references, and session seal. It also **replays events into a new typed ledger**, checking canonical quantity/model payloads, chronological evidence registration, duplicate identifiers, model-derived quantities, and exact equality between the replayed ledger/evidence maps and their exported summaries.

A PASS means the supplied manifest is internally self-consistent under the recorded hash chain, seal, and semantic replay. A valid hash chain with a mismatched ledger vector, unregistered evidence reference, or impossible derived quantity is rejected. Noncanonical manifest/event fields, changes to the required claims boundary, and malformed JSON field types also fail closed, rather than being accepted as release/approval metadata. This still does **not** independently establish the origin, accuracy, or immutable custody of the record.

**Security boundary:** the session seal is a deterministic digest, **not** a digital signature, authority approval, external notarization, or production-release authorization. External signature/anchoring and trusted evidence-custody validation require separate controls.

It does **not** establish:

- independent time custody;
- external notarization;
- instrument calibration;
- production performance;
- truthful human-entered metadata; or
- immutable history if an attacker can replace both the manifest and its external reference.

For independent custody, preserve or attest the resulting seal/manifest through the established Worldshepherd custody path (for example Sigstore, RFC 3161 timestamping, and provider-separated archive storage).

## Historical boundary

This feature is prospective.

It must not be used to back-fill historical CPU-hours, kWh, labor-hours, resource-hours, data processed, or cost where contemporaneous telemetry was not recorded. Existing QCRYPTO historical resource fields remain `NOT_RECORDED` unless direct evidence exists.
