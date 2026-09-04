# WS-HMAA v0.5 — Authorized Sandbox Readiness

Status: IMPLEMENTED IN SOFTWARE / NOT LIVE-VALIDATED

## Objective

WS-HMAA v0.5 turns the v0.4 public-contract harness into a bounded, credentials-aware **read-only** Sandbox execution path. This increment is designed so an authorized Lattice Sandbox can later be exercised without changing the assurance core or adding any operational write/control capability.

No live Sandbox connection is performed as part of this increment, and `live_environment_validated` remains false.

## Authentication basis

Current public Lattice documentation states that Sandbox API requests require:

- the Sandbox resource endpoint (`LATTICE_ENDPOINT`);
- a Lattice bearer token (`ENVIRONMENT_TOKEN`), either a long-lived environment token or an OAuth-derived access token;
- the account-level Sandbox bearer token (`SANDBOXES_TOKEN`) in the `Anduril-Sandbox-Authorization` header.

For OAuth client credentials, public documentation states access tokens expire after approximately 30 minutes. v0.5 deliberately does **not** implement client-secret exchange or token refresh. It accepts a pre-provisioned bearer token only, keeping credential acquisition outside the assurance process.

Official references:

- https://developer.anduril.com/guides/developer-tools/sandboxes
- https://developer.anduril.com/guides/getting-started/authenticate
- https://developer.anduril.com/reference/rest/entities/stream-entities

## Runtime environment contract

Only these environment-variable names are consumed:

```text
LATTICE_ENDPOINT
ENVIRONMENT_TOKEN
SANDBOXES_TOKEN
```

Secret values are represented with Pydantic `SecretStr`, omitted from readiness reports, and never included in sanitized connection errors.

## Transport controls

`SandboxReadOnlySSETransport` implements the v0.4 `LatticeReadTransport` protocol and exposes only:

- `stream_entities(...)`
- `stream_tasks(...)`

The concrete endpoint allowlist is exactly:

```text
/api/v1/entities/stream
/api/v1/tasks/stream
```

The transport additionally enforces:

- HTTPS-only endpoint configuration;
- hostname-only base endpoint with no embedded credentials, path, query, fragment, or non-default port;
- exact endpoint allowlisting;
- blocked HTTP redirects to prevent bearer-header forwarding;
- `Accept: text/event-stream` and content-type verification;
- bounded SSE lines/events;
- UTF-8 and JSON-object validation;
- sanitized HTTP/network errors;
- no arbitrary request method;
- no entity publish, task creation/update, manual-control, or vehicle-control methods.

## Finite evidence capture

`capture_readonly_stream_evidence(...)` accepts a read-only transport plus a bounded capture plan. It samples at most the configured number of entity and task messages, closes the iterators, then passes those messages through the v0.4 public-contract parser and HMAA evidence chain.

This allows a future authorized run to produce:

1. public-contract validation;
2. replay/chronology assessment;
3. SHA-256 event-chain evidence;
4. a fixture/capture digest and disposition counts;
5. finite, reproducible evidence rather than an indefinitely open stream.

The capture result still records `live_environment_validated=false`. A separate governed attestation step is required before that claim may change.

## Acceptance boundary

Passing v0.5 means Worldshepherd has an executable, CI-tested path prepared for an authorized Lattice Sandbox **read-only** trial. It does not establish:

- that Sandbox credentials are currently available;
- that authentication has succeeded against a live Sandbox;
- that a live SSE stream has been received;
- that Anduril or Hermeus has reviewed or approved this integration;
- that Quarterhorse or any operational platform is integrated;
- any flight-control, mission-command, weapons, or task-execution authority.

## Authorized live-validation procedure

When credentials are legitimately provisioned:

1. Export the three runtime variables locally; never commit them.
2. Run the redacted readiness check and confirm `live_environment_validated=false`.
3. Exercise a finite read-only entity/task capture against the Sandbox.
4. Preserve only governed evidence outputs; do not log bearer headers.
5. Verify evidence-chain integrity and expected stream-envelope types.
6. Repeat the read-only capture to establish reproducibility.
7. Only after reproducible external evidence and review may a separate attestation record mark Sandbox read interoperability as validated.

Production integration remains a later, independent gate.
