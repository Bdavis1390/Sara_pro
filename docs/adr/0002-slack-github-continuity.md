# ADR-0002 — Slack / GitHub Operational Continuity

- **Status:** Proposed
- **Date:** 2026-09-15
- **Owner:** Worldshepherd
- **Decision class:** Operations / evidence custody / resilience

## Context

Worldshepherd uses Slack for rapid coordination and GitHub for implementation, documentation, evidence, and review. A transient Slack connector failure can interrupt coordination, but it must not suspend engineering, capture, validation, or durable project state.

Slack messages are also not a sufficient long-term source of truth for technical maturity, architecture, code, test evidence, partner commitment, or public claim state.

## Decision

GitHub is the durable source of truth for consequential Worldshepherd technical and governance state.

Slack remains the coordination surface for rapid discussion, routing, outreach status, and short operating summaries.

When Slack is unavailable or a connector call returns no usable result:

1. stop retry loops after one retry;
2. continue the active task in GitHub or another durable project source;
3. preserve the last known successful Slack action when available;
4. never represent an unsent Slack action as completed;
5. reconcile back to Slack with one summary once connectivity returns.

Consequential Slack threads should resolve to a GitHub issue, PR, canonical document, test/evidence artifact, or other durable record when they affect architecture, readiness, opportunity posture, partner state, external claims, or public release.

## Consequences

### Positive

- Slack outages no longer become a single point of operational failure.
- Technical claims and readiness changes remain reviewable and version-controlled.
- External communication state can be reconciled without confusing draft/sent/replied states.
- Evidence and negative results remain anchored to repository history.

### Costs

- Some high-value Slack discussions require explicit GitHub reconciliation.
- Contributors must distinguish coordination context from durable evidence.
- Cross-links must be maintained for important work items.

## Related documents

- `docs/WORLDSHEPHERD_OPERATING_MODEL.md`
- `docs/SLACK_GITHUB_CONTINUITY.md`
- `docs/CLAIMS_AND_EVIDENCE_POLICY.md`
- `docs/operations/FRESHNESS_POLICY.md`
- `.github/pull_request_template.md`
