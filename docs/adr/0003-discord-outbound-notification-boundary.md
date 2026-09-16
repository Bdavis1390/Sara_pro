# ADR-0003 — Discord Outbound Notification Boundary

- **Status:** Proposed
- **Date:** 2026-09-16
- **Owner:** Worldshepherd
- **Decision class:** Integration / security / evidence custody

## Context

Worldshepherd now uses Discord as its preferred live coordination surface while GitHub remains the durable source of truth. A direct ChatGPT Discord connector is not currently available, and a full Discord bot would create a larger trust boundary than is required for basic operating notifications.

The canonical SARA runtime already maintains durable provenance and audit behavior independently of any messaging platform. Discord should consume bounded status information without becoming an authorization, evidence, or execution plane.

## Decision

The first Discord integration is an **outbound-only incoming-webhook publisher**.

The publisher:

- uses a webhook URL supplied only through runtime secret configuration;
- accepts a small allowlist of notification classes;
- performs no inbound message reading or command handling;
- has no authority to approve actions or mutate SARA/GitHub state;
- neutralizes mentions and disables Discord allowed mentions;
- rejects likely credential material and embedded Discord webhook URLs;
- restricts destinations to official Discord HTTPS webhook endpoints;
- bounds message size, timeout, and retry count;
- supports a no-network dry-run approval mode;
- may carry a SARA stable event ID solely as provenance correspondence metadata.

GitHub/SARA evidence remains authoritative regardless of Discord delivery status.

## Consequences

### Positive

- Discord can become operationally useful without granting broad bot permissions.
- A leaked or compromised command channel cannot directly invoke Worldshepherd actions through this integration.
- Notification rendering and network behavior are unit-testable without contacting Discord.
- Credentials are kept out of repository configuration and CLI arguments.
- Discord outages do not block durable work.

### Costs / limitations

- The first integration cannot read replies, reactions, threads, or approvals.
- Live Discord delivery remains unvalidated until a human configures a webhook and performs a controlled external test.
- Webhook delivery itself is at-most a notification result; it does not create technical evidence or advance readiness.
- Any future inbound bot requires a separate architecture/security decision and negative-path validation.

## Claim boundary

After repository tests pass, the notifier may be described as `IMPLEMENTED IN SOFTWARE`.

Do not claim live Discord delivery, reliability, external adoption, partner validation, or command/control capability until separately demonstrated and recorded.

## Related documents

- `docs/DISCORD_GITHUB_CONTINUITY.md`
- `docs/DISCORD_SERVER_BLUEPRINT.md`
- `docs/DISCORD_INTEGRATION_RUNBOOK.md`
- `docs/WORLDSHEPHERD_OPERATING_MODEL.md`
- `deployments/sara_verified_local_v1/worldshepherd_sara/discord_webhook.py`
