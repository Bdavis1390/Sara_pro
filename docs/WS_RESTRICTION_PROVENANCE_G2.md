# WS-RESTRICTION-PROVENANCE G2 — ADMIN OBSERVABILITY

Status: **IMPLEMENTED IN SOFTWARE ON BRANCH / PENDING INTERNAL VALIDATION**

## Objective

G2 makes the G1 restriction evidence operationally visible to OVERWATCH/SARA administrators without creating a new content-ingestion or content-retrieval path.

The design is deliberately read-only:

```text
G1 safe restriction event
        |
        v
SARA audit log
        |
        v
strict restriction validator
        |
        +--> malformed restriction-shaped records counted, not silently dropped
        |
        v
whitelist projection
        |
        v
admin-only status/recent endpoints
```

No G2 endpoint accepts restricted content, raw prompts, candidate completions, safe replacement text, arbitrary metadata, or remediation text.

## API surface

Two administrator-only endpoints are added:

- `GET /admin/restrictions/status`
- `GET /admin/restrictions/recent?limit=50`

Both use the existing bearer-role mechanism and require `Role.ADMIN`. Relay credentials receive `403`; missing or invalid credentials receive the existing `401` behavior.

The public `/health` response exposes only the endpoint paths. It does not expose restriction counts, reason codes, source systems, fingerprints, or record details.

## Bounded window

Observability is explicitly scoped to the bounded SARA audit window:

- maximum scanned audit records: `500`;
- maximum recent projected restriction records: `100`;
- default status audit window: `500`;
- default recent result limit: `50`.

The helper itself rejects a caller-supplied audit list larger than the configured maximum, so the bound is not dependent solely on FastAPI query validation.

The response states that bounded audit retention does not establish global lifetime counts or complete provider-side restriction history.

## Strict validation

A record is counted as valid restriction evidence only when all of the following hold:

- the audit event is `content_restriction_recorded`;
- audit timestamp is timezone-aware;
- payload schema is `WS-RESTRICTION-PROVENANCE-V1`;
- no unknown payload keys are present;
- `raw_content_persisted` is exactly `false`;
- restriction ID is 32 lowercase hexadecimal characters;
- stable event ID is exactly `SARA-EVENT-RESTRICTION-{restriction_id}`;
- delivery semantics are `AT_LEAST_ONCE`;
- action is one of `BLOCK`, `REDACT`, `TRANSFORM`, `ESCALATE`;
- reason code and component identifiers meet the G1 bounded identifier forms;
- timestamps are timezone-aware;
- content fingerprints are absent or 64 lowercase hexadecimal characters.

Restriction-shaped records that fail validation increment `malformed_restriction_events` and set the observability status `ok=false`. They are not returned in the recent-record projection.

## Whitelist projection

The recent endpoint returns only structural provenance fields:

- restriction ID;
- stable event ID;
- audit timestamp;
- restriction occurrence timestamp;
- action;
- reason code;
- source system;
- processor;
- process version;
- policy reference;
- correlation ID;
- parent event ID;
- keyed input/generated/safe-output fingerprints;
- `raw_content_persisted=false`.

The projection intentionally omits:

- `safe_summary`;
- the metadata object;
- arbitrary audit payload fields;
- raw input;
- generated restricted content;
- safe replacement text.

This is stricter than simply returning the G1 safe evidence object. G2 minimizes data exposure even to administrators by returning only what is needed for operational diagnosis and correlation.

## Status aggregation

The status response provides window-scoped counts by:

- action;
- reason code;
- source system;
- processor.

It also reports scanned audit records, restriction events seen, valid and malformed restriction counts, and the last valid restriction occurrence observed in the audit order.

These counts are diagnostic, not global metrics or provider truth.

## Acceptance tests

The G2 regression path verifies:

1. strict projections omit `safe_summary`, metadata, raw input, raw generated output, and safe replacement text;
2. status counts valid restriction events correctly;
3. malformed restriction-shaped events produce `ok=false` and are not projected;
4. missing credentials receive `401`;
5. relay credentials receive `403`;
6. administrator credentials can read status and recent projections;
7. responses inherit `Cache-Control: no-store`;
8. recent-result bounds reject `0` and values above `100`;
9. unknown restriction payload fields fail validation rather than being silently accepted;
10. helper-level audit windows larger than `500` fail closed.

## Claims boundary

G2 is **IMPLEMENTED IN SOFTWARE / PENDING INTERNAL VALIDATION** until its exact-head required CI, broader verified-local gate, and protected merge complete.

G2 does not create a restricted-content submission endpoint and does not provide raw-content recovery, reconstruction, replay, bypass, or disclosure. It does not establish global lifetime restriction counts, provider-side completeness, production authorization hardening, or external policy-provider interoperability.
