# Discord ↔ GitHub Continuity

## Operating principle

Discord is the primary live coordination surface. GitHub is the durable technical, governance, evidence, and decision record.

A Discord outage, bot failure, webhook failure, permission problem, or connector loss must never suspend the project or erase execution state.

## Source-of-truth split

Use **Discord** for:

- rapid coordination and discussion;
- routing and triage;
- short operational summaries;
- meeting coordination;
- partner/outreach status discussion;
- live handoffs and alerts;
- links to GitHub issues, PRs, evidence packages, and canonical documents.

Use **GitHub** for:

- architecture and canonical technical documentation;
- issues and decision records;
- code/configuration changes;
- tests, validation artifacts, and negative evidence;
- PR review and claims-state changes;
- opportunity/PRE records that affect reusable technical readiness;
- durable partner/outreach facts when they affect engineering, commitments, IP/data boundaries, or public claims.

## Discord outage fallback

If Discord is unavailable or a bot/webhook returns no usable result:

1. stop retry loops after one failed retry;
2. continue the active task in GitHub or another durable project source;
3. record the last successful Discord action or message link when known;
4. do not represent an unsent Discord message as sent;
5. when Discord returns, post one compact reconciliation note linking to the GitHub artifacts created during the outage;
6. never block code, documentation, evidence packaging, capture analysis, or validation solely because Discord is unavailable.

## Cross-link rule

A consequential Discord thread should link to its durable GitHub artifact when one exists.

A consequential GitHub issue or PR may link back to Discord for discussion context, but acceptance must not depend on inaccessible Discord-only evidence.

Prefer **one Discord parent thread ↔ one GitHub issue/PR** for consequential work.

## Bot and webhook security

- Use dedicated service identities rather than human credentials.
- Grant only the minimum channel and action permissions needed.
- Do not expose bot tokens, webhook URLs, API keys, secrets, private contact data, CUI, classified material, or uncleared export-controlled data in channels or repository content.
- Separate read-only notification bots from bots allowed to write, moderate, or trigger automation.
- Require explicit human approval before external commitments, destructive actions, privilege changes, or public-release actions.
- Log automation results and failures to a durable GitHub artifact when they affect consequential state.
- Rotate/revoke credentials immediately if compromise is suspected.

## Communication state

`DRAFTING` · `READY FOR APPROVAL` · `APPROVED` · `SENT` · `WAITING EXTERNAL` · `REPLIED` · `FOLLOW-UP DUE` · `CLOSED`

Technical state uses repository claim labels and lifecycle states defined in `docs/WORLDSHEPHERD_OPERATING_MODEL.md`.

## Recovery checklist

After any Discord outage or bot failure:

- [ ] confirm current GitHub branch/issue/PR state;
- [ ] identify actions completed while Discord was unavailable;
- [ ] identify messages drafted but not sent;
- [ ] post one reconciliation summary rather than duplicate history;
- [ ] preserve original evidence links and timestamps;
- [ ] verify bot/webhook permissions before re-enabling automation;
- [ ] resume from the GitHub source of truth.
