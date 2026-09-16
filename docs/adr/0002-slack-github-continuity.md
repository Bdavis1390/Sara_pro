# ADR-0002 — Discord / GitHub Operational Continuity

- **Status:** Proposed
- **Date:** 2026-09-16
- **Owner:** Worldshepherd
- **Decision class:** Operations / evidence custody / resilience

## Context

Worldshepherd requires a fast collaboration surface for coordination and a durable source of truth for implementation, documentation, evidence, opportunity capture, partner state, and review.

Slack was previously selected as the live coordination layer, but connector instability demonstrated that a messaging platform must never become a single point of operational failure. The live coordination role is now assigned to Discord. Slack is retained only as a legacy/fallback migration surface.

Messaging history is not sufficient as the long-term source of truth for technical maturity, architecture, code, test evidence, partner commitment, public claim state, or approval history.

## Decision

GitHub is the durable source of truth for consequential Worldshepherd technical and governance state.

Discord is the primary coordination surface for rapid discussion, routing, outreach status, alerts, handoffs, and short operating summaries.

When Discord is unavailable, a bot/webhook fails, or a connector call returns no usable result:

1. stop retry loops after one failed retry;
2. continue the active task in GitHub or another durable project source;
3. preserve the last known successful Discord action when available;
4. never represent an unsent Discord action as completed;
5. reconcile back to Discord with one summary once connectivity returns.

Consequential Discord threads should resolve to a GitHub issue, PR, canonical document, test/evidence artifact, or other durable record when they affect architecture, readiness, opportunity posture, partner state, external claims, or public release.

Slack may be used temporarily for migration or fallback but is not authoritative and must not become a dependency for continuity.

## Security decision

Discord bots and webhooks use dedicated service identities and least privilege. Human credentials are not reused for automation. Broad administrative permissions are prohibited by default. External commitments, destructive actions, privilege changes, public-release actions, and technical claim-state promotion require the applicable human approval/evidence gate.

## Consequences

### Positive

- Discord or connector outages no longer become a single point of operational failure.
- Technical claims and readiness changes remain reviewable and version-controlled.
- External communication state can be reconciled without confusing draft/sent/replied states.
- Evidence and negative results remain anchored to repository history.
- Discord can provide richer live coordination while GitHub retains authoritative custody.

### Costs

- High-value Discord discussions require explicit GitHub reconciliation.
- Contributors must distinguish coordination context from durable evidence.
- Cross-links must be maintained for important work items.
- Bot permissions and credentials require independent lifecycle management.

## Related documents

- `docs/WORLDSHEPHERD_OPERATING_MODEL.md`
- `docs/DISCORD_GITHUB_CONTINUITY.md`
- `docs/DISCORD_SERVER_BLUEPRINT.md`
- `docs/WORLDSHEPHERD_WORKSPACE_MAP.md`
- `docs/SLACK_GITHUB_CONTINUITY.md` — legacy migration note
- `docs/CLAIMS_AND_EVIDENCE_POLICY.md`
- `docs/operations/FRESHNESS_POLICY.md`
- `.github/pull_request_template.md`
