# WS-HMAA v1.2 — Authorized Read-Only Sandbox Session Boundary

## Purpose

v1.2 composes the previously separate WS-HMAA preflight, Lattice Sandbox authentication, finite read-only capture, assurance replay, repeatability attestation, and partner-request packaging stages into one bounded execution protocol.

The purpose is to make an authorized interoperability evaluation mechanically reproducible without expanding the control surface. It does **not** turn a successful local session into an Anduril, partner, live-environment, flight, or operational validation claim.

## Default posture

The `ws-hmaa-sandbox-session` command is zero-network by default.

Without `--execute-network`, it evaluates only the v1.1 preflight and either prints or writes the secret-free preflight report. The default path does not instantiate an OAuth provider, create a stream transport, acquire a token, or connect to an external environment.

Network execution requires all of the following:

1. `--execute-network`;
2. `--authorization-confirmed`;
3. `--out <new-directory>` so evidence is retained locally;
4. a valid Lattice Sandboxes endpoint under `.env.sandboxes.developer.anduril.com`;
5. `SANDBOXES_TOKEN`;
6. exactly one environment credential mode:
   - `ENVIRONMENT_TOKEN`, or
   - `LATTICE_CLIENT_ID` + `LATTICE_CLIENT_SECRET`;
7. a finite capture plan requesting at least one entity or task stream message.

Failure of any precondition blocks before transport creation.

## Network boundary

The execution protocol can construct only the existing `SandboxReadOnlySSETransport`.

Its network surface remains restricted to:

- `POST /api/v1/entities/stream`
- `POST /api/v1/tasks/stream`
- `POST /api/v1/oauth/token` only when OAuth client credentials are selected

The stream transport does not expose entity publication, task creation/update, agent execution, manual control, flight control, weapons actions, arbitrary paths, arbitrary hosts, redirects, or arbitrary HTTP methods.

The OAuth provider retains short-lived access tokens in memory only and does not persist them into the evidence package.

## Finite capture and repeatability

Each execution attempt samples a configured finite number of messages and closes the stream iterator after the limit is reached.

The default session requests three capture attempts because WS-HMAA v0.7 requires three **distinct qualifying capture hashes** before it can construct a partner-validation request. Merely running three attempts is insufficient: duplicate captures remain `CANDIDATE_EVIDENCE`.

Every qualifying capture must remain fully `ALLOW` under the existing assurance state evaluator. Any non-ALLOW disposition prevents promotion into the repeatability-qualified partner-request state.

## Evidence outputs

A successful executed session writes a new output directory containing:

- `preflight-report.json` — zero-network preflight record and digest;
- `local-capture-NN.json` — local review evidence for each finite capture;
- `attestation-report.json` — repeatability/qualification state;
- `session-receipt.json` — secret-free hash-bound execution receipt;
- `partner-validation-request.json` — present only when distinct-capture requirements are met; and
- `manifest.json` — SHA-256 digests for the local artifact set.

The local capture files may contain simulated Sandbox entity/task payloads and are therefore local review evidence. The partner-validation request remains a separate raw-payload-excluding exchange artifact.

## Receipt semantics

A successful v1.2 receipt may truthfully state that:

- an explicitly authorized bounded read session was executed;
- the validated Sandbox endpoint shape and credential mode were used;
- only the allowed read stream paths were available to WS-HMAA;
- finite candidate evidence was captured and hash-bound; and
- a partner-validation request package was generated if repeatability requirements were satisfied.

The receipt deliberately records all of the following as false:

- `external_environment_provenance_confirmed`
- `live_environment_validated`
- `partner_validated`
- `flight_validated`
- `operationally_validated`

An endpoint string and successful network exchange do not independently prove that the external environment provenance asserted by a third party is correct. That remains part of the v0.8/v0.9 partner-attestation gate.

## Claims boundary

Allowed labels remain:

- `IMPLEMENTED IN SOFTWARE`
- `REQUIRES PARTNER VALIDATION`

Explicitly prohibited claims remain:

- `LIVE_ENVIRONMENT_VALIDATED`
- `PARTNER_VALIDATED`
- `FLIGHT_VALIDATED`
- `OPERATIONALLY_VALIDATED`

## Partner validation gate

When at least three distinct qualifying captures are present, v1.2 automatically invokes the existing v0.8 partner-request builder. The external reviewer is still required to confirm authorization/environment provenance, the source of the cited read-only evidence, the absence of write/control actions, and the referenced hashes.

The existing v0.9 external response verification and v1.0 human acceptance steps remain downstream gates. v1.2 does not bypass or weaken either gate.
