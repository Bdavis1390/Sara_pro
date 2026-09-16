# ADR-0004 — Discord Post-Audit Event Projection

- **Status:** Proposed
- **Date:** 2026-09-16
- **Owner:** Worldshepherd
- **Decision class:** Integration / provenance / notification delivery

## Context

SARA already has a durable event outbox with stable event IDs and `AT_LEAST_ONCE` audit-delivery semantics. The authoritative path appends the audit record before persisting the outbox transition from `PENDING` to `DELIVERED`. A failure between those operations may replay the same stable event ID, and downstream consumers are expected to deduplicate on that ID.

Discord is a non-authoritative live coordination surface. Connecting it directly to event creation, registry mutation, or approval logic would create a second state path and could allow a messaging outage to interfere with SARA evidence custody.

## Decision

Discord event projection occurs only **after** the authoritative SARA event is already audited and retained as a valid `DELIVERED` outbox record.

The projector:

- never marks an authoritative outbox event `DELIVERED`;
- never appends or edits the original SARA audit record;
- projects only an explicit allowlist of event families;
- requires a matching recent audit record carrying the stable `_outbox_event_id` and `AT_LEAST_ONCE` delivery metadata before projection;
- does not provide a fallback mapping for unknown events;
- transforms approved events into minimal Discord notifications rather than forwarding raw payloads;
- records successful live notifications in a separate compact receipt namespace keyed by stable SARA event ID;
- uses those receipts only for notification deduplication, never as technical evidence or authoritative workflow state;
- writes no receipt during dry-run;
- writes no receipt after a failed Discord delivery;
- permits replay under the same stable event ID if Discord delivery succeeds but receipt persistence fails.

The first allowlisted event families are:

1. `prime_custody_provenance` → `EVIDENCE_STATUS` notification containing only bounded identity/state-transition fields and the transition ID; and
2. `prime_sentinel_authorization_rejected` → `SYSTEM_ALERT` notification containing only the PRIME identifier and a direction to inspect the durable audit record.

Raw evidence references, arbitrary `details`, rejection reasons, authorization context, credentials, and other unrestricted payload fields are not forwarded.

## Delivery semantics

The Discord projection layer is **at least once**, not exactly once.

A stable SARA event ID is included in every projected notification. Under the normal single-dispatcher operating model, a persisted receipt prevents repeat notification. Concurrent dispatchers or a successful external post followed by local receipt-write failure may produce a duplicate Discord message. Such duplicates are reconciled by the stable event ID.

No implementation or operational document may claim exactly-once Discord delivery unless a separately reviewed protocol establishes and validates that property.

## Retention and cadence

The SARA event outbox intentionally retains only a bounded number of delivered records. Therefore Discord projection is an operational notification side effect, not an archival export service. Operators should run the projector frequently enough that eligible retained events are examined before normal outbox pruning removes old delivered entries.

If notification completeness over longer horizons becomes a requirement, introduce a separately reviewed durable notification cursor/queue rather than weakening the authoritative SARA outbox or reclassifying Discord as evidence storage.

## Failure behavior

- Malformed authoritative outbox state: fail closed.
- Malformed Discord receipt state: fail closed.
- Mapped `DELIVERED` event without matching recent audit confirmation: fail closed.
- Unknown event family: skip without disclosure.
- Discord delivery failure: retain no notification receipt; authoritative SARA state is unchanged.
- Receipt persistence failure after successful Discord delivery: report failure and permit stable-ID replay.
- Discord outage: does not block SARA audit, registry, PRIME custody, GitHub, or evidence workflows.

## Consequences

### Positive

- Discord cannot become an alternate authorization or evidence path.
- Only already-audited events are eligible for notification.
- Raw sensitive event payloads are not blindly fanned out to a third-party collaboration surface.
- Stable event IDs provide deterministic duplicate reconciliation.
- The projector is testable without a live Discord credential through dry-run and injected connector transports.

### Costs / limitations

- Delivery is intentionally not exactly once.
- A bounded recent-audit confirmation window means very delayed projection can fail closed rather than infer audit state.
- A bounded delivered-event retention window means the projector must run at an appropriate operational cadence.
- The receipt namespace affects notification deduplication only and does not substitute for an evidence package.
- Live Discord delivery remains separately unvalidated until a controlled external test is completed.

## Claim boundary

After exact-head repository tests pass, the projector may be described as `IMPLEMENTED IN SOFTWARE` and, where supported by those tests, `PROVEN INTERNALLY` for software behavior only.

Do not claim live Discord delivery, exactly-once semantics, Discord reliability, external adoption, partner validation, physical readiness, or inbound Discord control from this decision.

## Related documents

- `docs/adr/0003-discord-outbound-notification-boundary.md`
- `docs/DISCORD_INTEGRATION_RUNBOOK.md`
- `docs/DISCORD_GITHUB_CONTINUITY.md`
- `deployments/sara_verified_local_v1/worldshepherd_sara/event_outbox.py`
- `deployments/sara_verified_local_v1/worldshepherd_sara/discord_event_projection.py`
