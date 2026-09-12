# Worldshepherd SpaceLink Event Assurance

Status: **INTERNAL SOFTWARE VALIDATION PASS THROUGH v0.4 / EXTERNAL PROVIDER VALIDATION OPEN**

Current validated head: `3d4bf428a82ee1c4a9e3b926ac03cb5c501dff5f`

## Purpose

SpaceLink extends the validated contact-schema boundary with read-only AWS Ground Station event ingestion, deterministic contact projection, provider-read reconciliation, and claims-controlled evidence suitable for an OVERWATCH common-operating-picture feed.

No AWS credentials, provider write path, RF path, telemetry path, or spacecraft-command path is created by this branch.

## Public interface basis

AWS documents that Ground Station emits direct EventBridge service events including **Ground Station Contact State Change**, with source `aws.groundstation`. AWS documents direct Ground Station service-event delivery as **best effort**. The Ground Station digital twin emits the same EventBridge event types and API responses as the production service, while digital-twin ground stations currently do not support data delivery or telemetry delivery.

AWS also documents `ListContacts` and `DescribeContact` as read/list operations. `DescribeContact` includes contact-version evidence in its nested `version` object; v0.4 preserves `versionId`, `lastUpdated`, `failureCodes`, and `failureMessage` from that documented response shape.

Authoritative references:

- <https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-groundstation.html>
- <https://docs.aws.amazon.com/ground-station/latest/ug/monitoring.automating-events.html>
- <https://docs.aws.amazon.com/ground-station/latest/ug/contacts.lifecycle.html>
- <https://docs.aws.amazon.com/ground-station/latest/ug/digital-twin.html>
- <https://docs.aws.amazon.com/ground-station/latest/APIReference/API_ListContacts.html>
- <https://docs.aws.amazon.com/ground-station/latest/APIReference/API_DescribeContact.html>
- <https://docs.aws.amazon.com/service-authorization/latest/reference/list_groundstation.html>

## Internally validated behavior

The exact current head passed all seven principal repository workflows, including SARA Verified Local v1 Gate #1946, Commit Closure Evidence #1720, Operational Resilience Drill #632, NIST 800-171 SSP Precursor #608, TLS Private Backend Architecture #1198, Replacement Environment Restore #1212, and Rollback Drill #1220.

Validated software behavior includes:

- strict source validation for `aws.groundstation`;
- strict detail-type validation for `Ground Station Contact State Change`;
- extraction and normalization of documented contact state fields;
- explicit `BEST_EFFORT` delivery semantics;
- deterministic provider-event-to-`MissionEvent` conversion;
- idempotence by provider event ID;
- rejection of out-of-order events that would overwrite newer state;
- rejection of transitions away from terminal contact states;
- bounded per-contact event-ID retention;
- read-only OVERWATCH-facing snapshot projection;
- non-mutating provider-read reconciliation;
- reconciliation states `MATCH`, `PROJECTION_MISSING`, `STALE_PROVIDER_READ`, `STATUS_DIVERGENCE`, and `TERMINAL_CONFLICT`;
- flat `ListContacts` normalization;
- nested `DescribeContact.version` evidence preservation;
- explicit claims boundaries excluding RF, data delivery, telemetry delivery, command delivery, spectrum rights, certification, and operational readiness.

## Not implemented / not claimed

- live AWS account connection;
- live EventBridge subscription;
- live `ListContacts` or `DescribeContact` execution;
- EventBridge rule creation;
- provider-side contact reservation or cancellation;
- production Ground Station integration;
- RF transmission or reception;
- telemetry/data delivery;
- command delivery;
- spectrum authorization, FCC licensing, or interference coordination;
- AWS/operator/partner/government validation;
- certification or operational readiness.

## Delivery-semantics rule

AWS documents direct Ground Station service events as best effort. Therefore Worldshepherd must never interpret absence of an event as proof that a provider transition did not occur. The EventBridge-derived projection is evidence of observed provider messages, not evidence of complete provider history.

For operational use, reconciliation against authoritative provider read APIs is required in addition to event ingestion. The current reconciler performs comparison only and is deliberately unable to mutate provider state or silently rewrite mission history.

## Terminal-state rule

The projection treats these AWS contact states as terminal:

- `COMPLETED`
- `FAILED`
- `FAILED_TO_SCHEDULE`
- `CANCELLED`
- `AWS_CANCELLED`
- `AWS_FAILED`

A subsequent different state for the same contact fails closed rather than silently rewriting terminal history.

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

It does not expose synthetic link-quality, telemetry-quality, RF-success, or command-success fields because no such evidence is established by provider contact-state messages alone.

## Validation ladder

| Gate | Requirement | State |
|---|---|---|
| SL-0 | Provider-neutral normalized contact schema | **INTERNAL_PASS** |
| SL-1 | Authoritative AWS contact-state mapping | **INTERNAL_PASS** |
| SL-2 | Fail-closed unknown-state handling | **INTERNAL_PASS** |
| SL-3 | Replayable contact-state mission events | **INTERNAL_PASS** |
| SL-4 | Human-gated non-executable reservation proposal | **INTERNAL_PASS** |
| SL-4B | Nested `DescribeContact.version` evidence preservation | **INTERNAL_PASS** |
| SL-5A | Live read-only AWS digital-twin API validation | **NOT EXECUTED** |
| SL-5B | Digital-twin scheduling/config/error API validation | **NOT EXECUTED** |
| SL-6 | Idempotent provider write path with dedicated PRIME authorization | **NOT IMPLEMENTED** |
| SL-7A | EventBridge contact-event schema ingestion | **INTERNAL_PASS** |
| SL-7R | Provider-read reconciliation logic | **INTERNAL_PASS** |
| SL-7B | Live EventBridge delivery/reconciliation evidence | **NOT EXECUTED** |
| SL-8A | OVERWATCH read-only contact projection | **INTERNAL_PASS** |
| SL-8B | Live OVERWATCH COP integration | **NOT IMPLEMENTED / NOT EXECUTED** |
| SL-9 | Independent GSaaS/partner validation | **REQUIRES PARTNER VALIDATION** |
| SL-10 | RF / flight / operational validation | **REQUIRES EXTERNAL PHYSICAL VALIDATION AND APPLICABLE AUTHORIZATIONS** |

## SL-5A external validation boundary

The next useful evidence is a live **read-only** provider interaction after AWS Ground Station digital-twin onboarding. AWS classifies `groundstation:ListContacts` as a List action and `groundstation:DescribeContact` as a Read action. A validation identity should therefore begin without Ground Station write permissions.

Minimum intended permissions for the SL-5A validation identity:

- `groundstation:ListContacts`
- `groundstation:DescribeContact`

Optional discovery-only permissions when needed for digital-twin setup verification:

- `groundstation:ListGroundStations`
- `groundstation:ListSatellites`

No `ReserveContact`, `CancelContact`, mission-profile mutation, configuration mutation, ephemeris mutation, agent registration, or other provider write permission belongs in SL-5A.

### External-evidence handling rule

A live provider payload may contain account identifiers, ARNs, mission metadata, or other operational details. Raw provider output must not be committed to the public repository by default. Preserve exact raw evidence in an access-controlled location, record a SHA-256 digest, and only promote sanitized fields required for the claims-controlled evidence record.

A successful read-only API call would establish **provider-read interoperability evidence only**. It would not establish RF success, telemetry delivery, command delivery, spectrum authorization, flight readiness, partner endorsement, certification, or operational readiness.

## Promotion rule

Internal software claims may be promoted only on exact-head green CI. External/provider claims require externally obtained evidence with provenance and must remain separate from internal software validation.

The PR remains **BLOCK MERGE pending explicit CRE1AWS incorporation authorization**.