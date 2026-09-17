# WS-RESTRICTION-PROVENANCE G1

Status: **IMPLEMENTED IN SOFTWARE / PROVEN INTERNALLY FOR THE TESTED INVARIANTS**

Merged through protected `main` in PR `#360` at commit `401a4d56b85500f405127b69be9261b03d22d29e` after the required `Analyze (python)`, `CodeQL`, and `test-and-build` checks succeeded. The broader SARA Verified Local v1 gate also succeeded through unit/API tests, ephemeral deployment verification, destructive backup/restore, operational snapshot, release identity, and release-evidence indexing.

## Purpose

When an upstream model, policy layer, connector, or other processor restricts, redacts, transforms, or escalates generated content, Worldshepherd must not treat the result as missing data and must not attempt to reconstruct or bypass the restriction.

G1 converts the restriction itself into governed evidence:

```text
restricted generation attempt
        |
        v
PRIME policy outcome
        |
        +--> raw content: DO NOT PERSIST
        |
        v
keyed content fingerprints + safe process metadata
        |
        v
SARA at-least-once event outbox
        |
        v
ECHO semantic-hash persistence / conflict detection
        |
        v
OVERWATCH restriction/remediation status
```

## Security contract

The implementation in `restriction_provenance.py` accepts raw input/candidate output only transiently to compute domain-separated HMAC-SHA256 fingerprints. The returned evidence object contains no raw input, generated restricted text, or safe replacement text.

The fingerprint key is deployment-only secret material. It is never written into the restriction record. A deployment helper requires `RESTRICTION_FINGERPRINT_KEY` to contain at least 32 bytes, and `capture_restriction()` independently fails closed if a weak key is supplied even when no raw content is present.

This design uses keyed fingerprints instead of plain content hashes because restricted text may be low entropy. A plain digest can permit dictionary guessing; an HMAC fingerprint remains useful for equality/integrity binding without publishing an unkeyed content hash.

The metadata envelope rejects obvious raw-content and credential-bearing fields such as `raw_content`, `prompt`, `completion`, `token`, `password`, and `api_key`, including occurrences nested inside arbitrary JSON-style sequences. All metadata also passes the existing SARA bounded-JSON resource limits.

## Provenance fields

Each event records only bounded, non-content evidence:

- restriction ID and timestamp;
- action: `BLOCK`, `REDACT`, `TRANSFORM`, or `ESCALATE`;
- reason code and policy reference;
- source system, processor, and process version;
- correlation / parent-event lineage IDs;
- keyed input, generated-output, and safe-output fingerprints when those values existed;
- an explicitly safe summary, if supplied;
- sanitized metadata;
- explicit `raw_content_persisted: false` assertion.

The restriction ID is computed from the canonical safe evidence envelope. Re-delivery of the same evidence therefore keeps a stable SARA outbox event ID, while a semantic change produces a different ID.

## SARA / ECHO integration

`queue_restriction_event()` routes the evidence through the existing SARA event outbox rather than creating a second persistence path. The outbox already supplies stable event IDs and `AT_LEAST_ONCE` delivery semantics. ECHO subsequently hashes the semantic audit record and rejects replay of the same stable ID with different content.

This preserves the existing architecture:

```text
PRIME decides -> SARA routes -> ECHO persists/reconciles -> OVERWATCH reports
```

The end-to-end regression path exercises the real persistence chain: a restriction is queued into `DurableStore`, drained into the SARA audit log, reconstructed as an `AuditRecord`, ingested twice into `EchoEventStore` to prove store/deduplicate behavior, reconciled as `MATCHED`, and then checked at both serialized-audit and SQLite-byte levels to prove the raw input, raw generated candidate, and safe replacement text were never persisted.

## Bounded remediation

A remediation directive may request only:

- `NO_ACTION`
- `SAFE_TRANSFORM`
- `HUMAN_REVIEW`
- `REDUCE_SCOPE`

The API fails closed for unknown actions and explicitly rejects `REPLAY_RAW`, `RESTORE_RAW`, `BYPASS_POLICY`, `DISABLE_FILTER`, and `FORCE_RELEASE`.

A remediation contains only the restriction/event IDs, content fingerprints, and an optional identifier-only `rationale_code`. Free-form remediation rationale is intentionally not accepted, eliminating a secondary text channel that could be misused to copy restricted payloads back into persistence.

## G1 acceptance tests

The regression suite proves:

1. raw restricted input/output and safe-output text are absent from serialized evidence;
2. keyed fingerprints are stable, domain-separated, content-bound, and key-bound;
3. nested raw/secret metadata keys are rejected through mapping and sequence containers;
4. a safe summary cannot simply equal the raw input or generated restricted candidate;
5. restriction evidence enters the normal SARA outbox contract;
6. the real SARA outbox -> audit -> ECHO persistence/replay/reconciliation path retains the evidence while raw content remains absent from both audit serialization and the ECHO SQLite file;
7. allowed remediation is cryptographically bound to the restriction fingerprints;
8. remediation rationale is identifier-only, not free-form text;
9. raw replay and policy-bypass remediations fail closed;
10. unknown remediation actions fail closed;
11. malformed reason codes and naive timestamps fail closed;
12. weak content-fingerprint keys are rejected even when no content value is supplied;
13. deployment-key changes produce different content fingerprints.

## Claims boundary

G1 does **not** recover, reveal, reconstruct, classify, or bypass restricted material. It does not assert access to a provider's internal moderation rationale, hidden chain-of-thought, or proprietary safety systems. It records only the reason/category and process metadata actually supplied to Worldshepherd by the calling integration.

The metadata-key denylist prevents common accidental leakage paths but cannot semantically prove that arbitrary caller-supplied strings are safe. Integrations remain responsible for supplying only policy-approved metadata and safe summaries. Production deployments should pair this envelope with provider-specific allowlists where the metadata schema is known.

The internal proof applies only to the tested software invariants. It does **not** establish production secret-management adequacy, secure memory erasure of transient Python strings, external policy-provider interoperability, provider-specific metadata safety, or adversarial red-team validation. Those remain separate gates.
