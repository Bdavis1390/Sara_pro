# Worldshepherd SpaceLink Event Assurance v0.2

Status: **DRAFT / INTERNAL SOFTWARE VALIDATION PENDING FOR THIS HEAD**

## Purpose

v0.2 extends the validated v0.1 contact-schema boundary with a read-only AWS Ground Station EventBridge ingestion contract and a deterministic SpaceLink contact projection suitable for an OVERWATCH common-operating-picture feed.

No AWS account connection, EventBridge rule, Lambda function, provider write, RF path, telemetry path, or spacecraft-command path is created by this change.

## Public interface basis

AWS documents that Ground Station emits direct EventBridge service events including **Ground Station Contact State Change**, and that the service event source is `aws.groundstation`. AWS documents direct Ground Station service-event delivery as **best effort**. The Ground Station digital twin emits the same EventBridge events and API responses as the production service, while digital-twin ground stations currently do not support data delivery or telemetry delivery.

Authoritative references:

- <https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-groundstation.html>
- <https://docs.aws.amazon.com/ground-station/latest/ug/monitoring.automating-events.html>
- <https://docs.aws.amazon.com/ground-station/latest/ug/contacts.lifecycle.html>
- <https://docs.aws.amazon.com/ground-station/latest/ug/digital-twin.html>

## Implemented in v0.2

- strict source validation for `aws.groundstation`;
- strict detail-type validation for `Ground Station Contact State Change`;
- extraction of provider event ID, event time, region, contact ID, ground-station name, mission-profile ARN, satellite ARN, and contact status;
- reuse of the v0.1 AWS contact-state normalizer;
- explicit `BEST_EFFORT` delivery semantics in normalized evidence;
- deterministic provider-event-to-`MissionEvent` conversion;
- idempotence by provider event ID;
- rejection of out-of-order events that would overwrite newer state;
- rejection of transitions away from documented terminal contact states;
- bounded per-contact event-ID retention;
- read-only OVERWATCH-facing snapshot projection;
- explicit digital-twin claims boundary excluding RF, data delivery, telemetry delivery, and spacecraft-command delivery.

## Not implemented / not claimed

- live EventBridge subscription;
- EventBridge rule creation;
- Lambda, SQS, SNS, Kinesis, or Step Functions deployment;
- AWS credentials or account access;
- proof that an event stream is complete;
- live digital-twin onboarding or scheduling;
- production Ground Station integration;
- RF transmission or reception;
- telemetry/data delivery;
- command delivery;
- spectrum authorization, FCC licensing, or interference coordination;
- partner/operator/government validation;
- operational readiness.

## Delivery-semantics rule

AWS documents direct Ground Station service events as best effort. Therefore the Worldshepherd projection must never interpret absence of an event as proof that a provider transition did not occur. Event-driven projection is evidence of observed provider messages, not evidence of a complete provider history.

For operational use, reconciliation against authoritative provider read APIs would be required in addition to EventBridge ingestion.

## Terminal-state rule

The projection treats these AWS contact states as terminal:

- `COMPLETED`
- `FAILED`
- `FAILED_TO_SCHEDULE`
- `CANCELLED`
- `AWS_CANCELLED`
- `AWS_FAILED`

A subsequent different state for the same contact fails closed instead of silently rewriting terminal history.

## OVERWATCH projection

The projection exposes only claims-controlled state:

- contact ID;
- current documented provider status;
- normalized disposition;
- ground station;
- AWS region;
- mission-profile and satellite references when present;
- first and last observed event times;
- last provider event ID;
- applied event count;
- terminal flag;
- delivery semantics;
- explicit claims scope.

It does not expose a synthetic link-quality, telemetry-quality, RF-success, or command-success field because no such evidence is established by EventBridge contact-state messages alone.

## Validation ladder update

| Gate | Requirement | State |
|---|---|---|
| SL-0 | Provider-neutral normalized contact schema | **INTERNAL_PASS at commit `849f336...`; exact evidence recorded** |
| SL-1 | Authoritative AWS contact-state mapping | **INTERNAL_PASS at commit `849f336...`; exact evidence recorded** |
| SL-2 | Fail-closed unknown-state handling | **INTERNAL_PASS at commit `849f336...`; exact evidence recorded** |
| SL-3 | Replayable contact-state mission events | **INTERNAL_PASS at commit `849f336...`; exact evidence recorded** |
| SL-4 | Human-gated non-executable reservation proposal | **INTERNAL_PASS at commit `849f336...`; exact evidence recorded** |
| SL-5 | Digital-twin scheduling/config/error API validation | **NOT EXECUTED** |
| SL-6 | Idempotent provider write path with dedicated PRIME authorization | **NOT IMPLEMENTED** |
| SL-7A | EventBridge contact-event schema ingestion | **IMPLEMENTED; EXACT-HEAD CI REQUIRED** |
| SL-7B | Live EventBridge delivery/retry/reconciliation evidence | **NOT IMPLEMENTED / NOT EXECUTED** |
| SL-8A | OVERWATCH read-only contact projection | **IMPLEMENTED; EXACT-HEAD CI REQUIRED** |
| SL-8B | Live OVERWATCH COP integration | **NOT IMPLEMENTED / NOT EXECUTED** |
| SL-9 | External GSaaS/partner validation | **REQUIRES PARTNER VALIDATION** |
| SL-10 | RF / flight / operational validation | **REQUIRES EXTERNAL PHYSICAL VALIDATION AND APPLICABLE AUTHORIZATIONS** |

## Promotion rule

Do not promote SL-7A or SL-8A to `INTERNAL_PASS` until repository CI succeeds on the exact commit containing `spacelink_eventbridge.py`, its tests, and this document.

A future live EventBridge integration must also add reconciliation logic because a best-effort event stream cannot by itself establish complete contact history.
