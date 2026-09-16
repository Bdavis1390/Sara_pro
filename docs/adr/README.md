# Architecture Decision Records

Worldshepherd architecture decisions in this directory preserve consequential design and governance choices as durable, reviewable records.

- `0001-canonical-runtime.md` — canonical SARA runtime decision.
- `0002-slack-github-continuity.md` — messaging/GitHub continuity decision; revised to make Discord primary and Slack legacy/fallback while GitHub remains authoritative.
- `0003-discord-outbound-notification-boundary.md` — outbound-only Discord webhook notification boundary and future inbound-bot gate.
- `0004-discord-post-audit-event-projection.md` — project only already-audited SARA events to Discord, with strict event mapping and stable-ID notification receipts.
