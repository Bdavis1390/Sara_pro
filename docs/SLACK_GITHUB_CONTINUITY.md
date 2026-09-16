# Slack ↔ GitHub Continuity — Legacy Migration Note

## Status

Slack is no longer the primary Worldshepherd live coordination surface. Discord is the designated live coordination layer; GitHub remains the durable technical and governance source of truth.

This document is retained to preserve migration history, existing links, and outage lessons learned from the Slack integration.

## Legacy rule

Slack may be used only as a temporary fallback, archive, or migration surface. No new Worldshepherd architecture, evidence, opportunity, partner, outreach, or readiness workflow should depend on Slack availability.

If Slack is used during migration:

1. consequential state changes must still resolve to GitHub;
2. unsent Slack messages must never be represented as sent;
3. Slack-only evidence cannot satisfy a GitHub acceptance gate;
4. bot/list/connector instability must not block work;
5. reconciliation should be compact and link to the durable GitHub artifact.

## Superseding documents

Primary continuity policy:

- `docs/DISCORD_GITHUB_CONTINUITY.md`
- `docs/DISCORD_SERVER_BLUEPRINT.md`
- `docs/WORLDSHEPHERD_WORKSPACE_MAP.md`
- ADR-0002

GitHub remains usable if Discord, Slack, or any messaging connector is unavailable.
