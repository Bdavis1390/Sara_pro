# Slack ↔ GitHub Continuity

## Operating principle

Slack is the fast coordination surface. GitHub is the durable technical and governance record.

A Slack connector failure must never suspend the project or erase execution state.

## Source-of-truth split

Use **Slack** for:

- rapid coordination
- routing
- discussion
- partner/outreach state updates
- meeting notes
- short operational summaries

Use **GitHub** for:

- architecture and canonical technical documentation
- issues and decision records
- code/configuration changes
- tests, validation artifacts and negative evidence
- PR review and claims-state changes
- opportunity/PRE records that affect reusable technical readiness
- durable external-engagement facts when they affect engineering, commitments, or public claims

## Connector-outage fallback

If Slack disconnects or returns an unusable response:

1. Stop retry loops after the first failed retry.
2. Continue the active task in GitHub or the local project source of truth.
3. Record the last successful Slack action or message link when known.
4. Do not represent unsent Slack messages as sent.
5. When Slack returns, post a compact reconciliation note linking to the GitHub artifact created during the outage.
6. Never block code, documentation, evidence packaging, capture analysis, or validation solely because Slack is unavailable.

## Cross-link rule

A consequential Slack work item should link to its durable GitHub artifact when one exists.

A consequential GitHub issue/PR may link back to Slack for discussion context, but acceptance must not depend on inaccessible Slack-only evidence.

## State vocabulary

Communication state:

`DRAFTING` · `READY FOR APPROVAL` · `APPROVED` · `SENT` · `WAITING EXTERNAL` · `REPLIED` · `FOLLOW-UP DUE` · `CLOSED`

Technical state uses the repository claim labels and lifecycle states defined in `docs/WORLDSHEPHERD_OPERATING_MODEL.md`.

## Recovery checklist

After any Slack outage:

- [ ] confirm current GitHub branch/issue/PR state
- [ ] identify actions completed while Slack was unavailable
- [ ] identify any Slack messages that were drafted but not sent
- [ ] post one reconciliation summary, not duplicate history
- [ ] preserve original evidence links and timestamps
- [ ] resume from the GitHub source of truth
