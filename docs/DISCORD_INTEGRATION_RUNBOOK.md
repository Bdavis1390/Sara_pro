# Worldshepherd Discord Integration Runbook

## Status

This runbook covers the first, deliberately narrow Discord integration: an **outbound incoming-webhook publisher** from Worldshepherd/SARA plus a redacted application-level connector adapter.

It is designed as a notification surface only. GitHub and the SARA evidence/audit path remain authoritative.

The connector adapter is part of Worldshepherd/SARA. It is not a ChatGPT-native Discord plugin and does not imply that this ChatGPT workspace can directly read or manage a Discord server.

## Security boundary

The initial integration intentionally does **not** use a Discord bot token and does not request permissions to read server messages, enumerate members, manage roles, manage channels, execute commands, or moderate users.

The publisher may only send bounded status messages to the single Discord channel represented by the configured incoming webhook.

It cannot:

- approve Worldshepherd actions;
- mutate SARA registry state;
- change a technical claim state;
- mark evidence as accepted;
- create partner commitments;
- represent a Discord post as proof that external delivery, validation, certification, or adoption occurred.

## Configuration

Create an incoming webhook in the intended Discord channel using Discord's server/channel administration interface. Treat the resulting webhook URL as a credential.

Set it only in the runtime environment:

```bash
export WORLDSHEPHERD_DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/<id>/<token>'
```

Do not commit the URL, paste it into issues/PRs, place it in screenshots, or pass it as a CLI argument where it can enter shell history.

The implementation accepts only HTTPS webhook URLs on the official `discord.com` or legacy `discordapp.com` hosts with an incoming-webhook path. Query parameters and fragments are removed before delivery.

## Connector status

The installed connector-health entry point is:

```bash
ws-discord-connector-status
```

It performs no Discord network request. It reports only redacted application configuration state, including:

- connector ID and mode;
- `CONFIGURED`, `UNCONFIGURED`, or `INVALID_CONFIGURATION` state;
- whether the configured value passes the Discord webhook allowlist;
- the allowed endpoint host when valid;
- the fixed `NOTIFICATION_ONLY` authority boundary;
- explicit `false` values for inbound read and inbound commands;
- `live_delivery_claimed=false` until controlled external validation is separately completed.

The command never returns the webhook ID, token, path, or complete webhook URL. It exits successfully only when configuration is valid; unconfigured or invalid configuration returns a non-zero status for automation/health-check use.

A healthy connector status proves only that the local configuration is syntactically and policy-valid. It does **not** prove Discord reachability, channel permissions, delivery, availability, or external validation.

## Human-reviewed dry run

The installed notification entry point is:

```bash
ws-discord-notify \
  --event-class WORKFLOW_STATUS \
  --title 'PR validation complete' \
  --summary 'Required checks completed successfully.' \
  --status VALIDATED \
  --priority P1 \
  --source-event-id SARA-EVENT-EXAMPLE-001 \
  --evidence-ref PR-EXAMPLE \
  --source-url https://github.com/Bdavis1390/Sara_pro \
  --dry-run
```

Dry-run mode validates and renders the message but performs no network call and does not require a webhook credential.

## Controlled live validation

After a dry run is reviewed:

1. Configure the webhook URL only in the runtime secret environment.
2. Run `ws-discord-connector-status` and verify `CONFIGURED`, `configuration_valid=true`, and `live_delivery_claimed=false`.
3. Send one non-sensitive `WORKFLOW_STATUS` test notification to a dedicated Worldshepherd Discord test/operations channel.
4. Confirm that the Discord message content matches the dry-run content.
5. Record the test time, source event/reference, CLI result fingerprint, and the human-observed Discord message link in a GitHub validation issue or evidence record.
6. Rotate/revoke the webhook immediately if the URL is exposed.

Until that controlled external test is completed, the correct claim boundary is:

- code/tests: `IMPLEMENTED IN SOFTWARE` after repository validation;
- connector configuration status: local/redacted configuration evidence only;
- live Discord delivery: **not yet claimed**;
- Discord availability/reliability: **not yet claimed**;
- external partner validation/adoption: **not claimed**.

## Allowed notification classes

The first implementation allows only:

- `APPROVAL_REQUIRED`
- `EVIDENCE_STATUS`
- `OPPORTUNITY_STATUS`
- `OUTREACH_STATUS`
- `SYSTEM_ALERT`
- `WORKFLOW_STATUS`

An `EXECUTE_COMMAND` class is intentionally absent. Discord is not a control plane in this phase.

Priorities are bounded to `P0`, `P1`, `P2`, and `P3`.

## Content protections

Before delivery the publisher:

- rejects common credential-assignment patterns;
- rejects Discord webhook URLs embedded in message fields;
- rejects common `sk-...` secret-token forms;
- neutralizes `@` mentions;
- sends `allowed_mentions.parse=[]` as defense in depth;
- rejects messages over Discord's 2,000-character content limit instead of silently truncating them;
- never includes the configured webhook URL in its result object or error text.

The connector-health adapter additionally reports only redacted host-level configuration metadata and never performs an external network check merely to answer a health query.

These controls reduce accidental disclosure; they do not replace normal data-classification review. Do not send CUI, classified information, export-controlled technical data, private credentials, or proprietary partner material through this integration unless a separately approved handling architecture explicitly permits it.

## Retry behavior

Delivery is bounded to three attempts by default and never more than five. Only HTTP `429` and `5xx` responses are retried. Other `4xx` responses fail immediately. Retry delays are bounded.

The publisher does not treat a retry or an HTTP success as technical evidence. It reports only the notification-delivery result.

## Provenance correspondence

When available, include the SARA outbox/audit stable event ID in `--source-event-id`. This is correspondence metadata so a Discord notification can point back to durable provenance.

Discord does not replace `SARA_EVENT_OUTBOX`, the audit log, GitHub issues/PRs, or an evidence package. If Discord and the durable record disagree, reconcile from the durable record.

## Future inbound bot gate

Do not add an inbound Discord bot merely for convenience. A bot that reads messages or accepts commands expands the trust boundary substantially.

Before an inbound bot is introduced, require a separate architecture review covering at minimum:

- command allowlists;
- authentication and role mapping;
- CRE1AWS human-approval gates;
- replay protection and idempotency;
- audit/provenance linkage;
- rate limiting and denial-of-service handling;
- secret custody and rotation;
- channel and guild allowlists;
- prompt/data injection boundaries;
- fail-closed behavior;
- negative-path tests;
- bot permission minimization.

That future capability must be reviewed and validated independently from this outbound-only webhook publisher.