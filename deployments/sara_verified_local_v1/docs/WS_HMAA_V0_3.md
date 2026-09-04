# WS-HMAA v0.3 — Replay, Chronology, and Persistent Evidence Controls

Status: IMPLEMENTED IN SOFTWARE / LOCAL SYNTHETIC VALIDATION ONLY

## Increment objective

WS-HMAA v0.3 hardens the v0.2 synthetic assurance sidecar against replay ambiguity, source-clock disorder, and volatile evidence loss. The controls remain observational and non-flight-control.

## Added controls

### Replay-safe identity

Each source event receives a stable SHA-256 identity key derived from:

- mission identifier;
- source-system identifier;
- source event identifier.

A separate source fingerprint excludes local ingest time and hash-chain placement. This lets WS-HMAA distinguish an exact replay from reuse of the same identity with conflicting source content.

- exact replay -> `WARN`;
- conflicting replay -> `REVIEW`.

### Clock-skew-aware chronology

Chronology is tracked per mission/source/subject scope. Source timestamps may arrive slightly out of order within an explicit tolerance. Events older than the latest source timestamp by more than the configured tolerance are escalated to `REVIEW`.

The default synthetic tolerance is 2.0 seconds. This is a test parameter, not a production flight-system timing requirement.

### Secured append-only evidence persistence

`HMAAEvidenceStore` writes sealed assurance records to `hmaa_evidence.jsonl` under the existing SARA data directory conventions.

The store:

- requires a valid event seal;
- requires mission-chain continuity;
- writes append-only JSONL records;
- fsyncs each accepted record;
- enforces `0700` on the data directory and `0600` on the evidence file;
- rejects malformed or oversized evidence lines instead of silently accepting them.

No write API is exposed by this increment.

### Read-only assurance API

Two authenticated administrator endpoints expose the local assurance view:

- `GET /v1/hmaa/status`
- `GET /v1/hmaa/evidence?mission_id=<id>&limit=<n>`

These endpoints do not ingest events, modify evidence, or issue vehicle-control commands.

## Claims boundary

v0.3 does not establish production interoperability with Anduril Lattice, Hermeus Quarterhorse, or any operational mission system. It demonstrates deterministic local assurance behavior with synthetic events and durable local evidence.

The next external validation tier remains an authorized Lattice Sandbox or equivalent controlled interoperability environment.
