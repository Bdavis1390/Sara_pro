# Keylime #1909 — cumulative attestation failure counter review

Date: 2026-09-12

Claims state: **SOURCE-REVIEWED CONTRIBUTION CANDIDATE / NOT UPSTREAM ACCEPTED**

Upstream issues: `keylime/keylime#1909`, with architectural interaction from `keylime/keylime#1880`.

## Executive finding

Issue #1909 is a strong, bounded Worldshepherd trust/observability contribution candidate: Keylime exposes cumulative successful attestations and the current consecutive failure streak, but not a cumulative lifetime failure count. After recovery, the failure streak resets, so monitoring systems lose the ability to calculate failure history without maintaining external state.

No open pull request matching #1909 was found during this review.

However, the implementation must account for Keylime's current dual verifier ORM mappings. Issue #1880 documents that `verifiermain` and related state are represented by both the legacy `keylime.db.verifier_db` mapping and the newer `keylime.models.verifier` framework, with stale/no-op behavior possible when both touch the same rows. A naïve #1909 patch that updates only one mapping or relies on stale in-memory state could create exactly the kind of semantic-health falsehood Worldshepherd is trying to eliminate.

## Current source evidence

Current Keylime source contains `consecutive_attestation_failures` in at least these persistence/model surfaces:

- legacy SQLAlchemy model: `keylime/db/verifier_db.py`;
- newer verifier-agent model framework: `keylime/models/verifier/verifier_agent.py`;
- Alembic migration history for the consecutive counter;
- attestation engine logic and verifier status/recovery paths;
- tests for TPM-engine, verifier-common, attestation-controller, and Tornado verifier behavior.

This confirms that a new persistent counter is a cross-surface state change, not an isolated field addition.

## Required semantics

The proposed `total_attestation_failures` should have an explicit invariant:

> For a verifier agent, `total_attestation_failures` is a monotonically non-decreasing count of completed attestation evaluations that Keylime classified as failed. It does not reset when a later attestation succeeds.

That definition should be distinguished from:

- transport attempts that never reached an attestation evaluation;
- timeouts, if Keylime models timeout as a separate state rather than a failed attestation;
- policy rejection versus infrastructure failure, if those are represented separately;
- `consecutive_attestation_failures`, which is intentionally reset by recovery logic.

Without this boundary, different code paths may increment the counter for different notions of "failure" and make the metric unusable.

## Recommended implementation surface

If maintainers accept the feature, a correct patch should update the complete persistence/API contract in one change:

1. Add `total_attestation_failures` to the canonical verifier-agent database schema with a non-null/default-zero migration appropriate to existing rows.
2. Add the field to **both currently active ORM/model representations** while dual mapping exists.
3. Increment it at the single authoritative point where an attestation changes from evaluation to failure, not at every retry/backoff layer.
4. Never reset it on successful attestation or automatic recovery.
5. Expose it through single-agent and bulk status serialization wherever `attestation_count` is exposed.
6. Add migration, success/failure/recovery, API serialization, and backward-database tests.

## Interaction with #1880

#1880 is architecturally important because it reports stale state and silently dropped updates when the legacy and new ORM models operate on the same verifier tables.

Two acceptable upstream strategies exist:

- **Preferred long-term:** resolve/consolidate #1880 first and implement #1909 only in the canonical mapping.
- **Bounded near-term:** add the field symmetrically to both mappings and write tests that reload state from the database before asserting the cumulative counter, so a no-op update cannot masquerade as persistence.

Worldshepherd should not claim the counter is reliable merely because an in-memory object increments during a unit test.

## Regression matrix

Minimum cases:

| Sequence | Expected total failures | Expected consecutive failures |
| --- | ---: | ---: |
| new agent | 0 | 0/null per existing semantics |
| fail | 1 | 1 |
| fail, fail | 2 | 2 |
| fail, success | 1 | 0 |
| fail, success, fail | 2 | 1 |
| process/verifier restart after failures | preserved | preserved/reset only per existing contract |
| bulk API read | equals DB value | equals DB value |

Additional tests should distinguish a failed attestation from a communication retry if those paths do not represent the same event.

## Observability value

A persistent total enables stateless external calculations such as:

- lifetime failure ratio = failures / (successes + failures);
- failure-rate deltas between scrape intervals;
- recovered-but-flaky agent detection;
- fleet SLO/SLA dashboards without reconstructing history from logs.

It should remain a raw event counter, not a derived "reliability score" inside Keylime. Derived scoring belongs in monitoring/policy layers where assumptions can be explicit.

## Contribution decision

**Classification: P1 / BOUNDED IMPLEMENTATION CANDIDATE WITH DUAL-ORM GATE.**

Internal screening score: **90/100**.

This is a good Worldshepherd contribution because it directly improves semantic observability and provenance of trust decisions. Before drafting an upstream patch, verify the exact authoritative failure transition and decide whether #1880 must be resolved first or whether symmetric dual-mapping support is acceptable to maintainers.
