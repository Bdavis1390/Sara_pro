# Discord Bridge Validation Gates

## Purpose

This record defines the evidence required before the Worldshepherd Discord bridge advances beyond repository implementation.

## Gate A — repository implementation

Required before `IMPLEMENTED IN SOFTWARE` is asserted:

- module imports and compiles;
- targeted security-boundary tests pass in required PR CI;
- webhook destination allowlist is enforced;
- dry-run performs no network call;
- credential-like content is rejected;
- mentions are neutralized and Discord allowed mentions are disabled;
- retry behavior is bounded;
- non-retryable client failures stop immediately;
- no webhook credential is stored in the repository;
- ADR-0003 and the integration runbook are reviewed with the code.

## Gate B — controlled live Discord delivery

Required before live Discord delivery is claimed:

- a dedicated Discord test/operations channel exists;
- a channel-scoped incoming webhook is created by an authorized human;
- the webhook is held only in runtime secret configuration;
- the approved dry-run content is recorded;
- one controlled non-sensitive notification is sent;
- the returned HTTP result is recorded without the webhook URL;
- a human verifies the expected Discord message exists;
- the Discord message link, time, content fingerprint, and corresponding GitHub/SARA source event are recorded in durable evidence;
- negative-path behavior is checked with a deliberately invalid/revoked test webhook or equivalent safe failure condition without exposing a production credential.

Passing Gate A does not imply Gate B.

## Gate C — operational use

Required before Discord is treated as a routine Worldshepherd notification surface:

- webhook ownership and rotation responsibility are assigned;
- the destination channel is governed by the Worldshepherd Discord server blueprint;
- incident/revocation procedure is documented and exercised;
- delivery failures reconcile to GitHub/SARA rather than blocking work;
- no workflow treats Discord acknowledgement as CRE1AWS approval or technical evidence;
- notification volume/rate limits are bounded and reviewed.

## Explicit non-claims

This outbound bridge does not establish:

- inbound command capability;
- Discord-based authorization;
- autonomous partner communication;
- evidence acceptance through reactions or messages;
- Discord reliability/SLA;
- certification or partner validation;
- hardware or physical-system readiness.
