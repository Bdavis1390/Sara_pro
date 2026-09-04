# WS-HMAA v1.1 — Read-Only Preflight Boundary

## Purpose

v1.1 adds a zero-network preflight evaluator for the existing WS-HMAA read-only Sandbox path. It determines whether configuration, authorization posture, and the finite capture plan are internally ready without acquiring a token, constructing a live transport, or opening a stream.

## Default behavior

`network_enabled` defaults to `false`. Preflight evaluation always records `network_call_performed=false`.

A dry run may return `DRY_RUN_READY` even when external Sandbox configuration is missing. That means the local evaluator and finite capture plan are usable; it does **not** mean an external read can be attempted.

## Authorized-read readiness

`AUTHORIZED_READ_READY` requires all of the following:

1. `network_enabled=true`;
2. `authorization_confirmed=true`;
3. a valid HTTPS Lattice Sandbox environment endpoint;
4. `SANDBOXES_TOKEN` present;
5. exactly one complete environment-token mode:
   - static `ENVIRONMENT_TOKEN`, or
   - OAuth `LATTICE_CLIENT_ID` + `LATTICE_CLIENT_SECRET`;
6. no simultaneous static + OAuth mode; and
7. a finite valid entity/task capture plan requesting at least one message.

This state is readiness only. v1.1 still performs no network operation.

## Secret handling

The preflight report records credential **presence booleans only**. It does not export:

- environment bearer tokens;
- OAuth client secrets;
- Sandbox authorization token values; or
- OAuth client IDs.

The endpoint is retained because it is required to validate the permitted Sandbox host boundary.

## Integrity

Each report is bound to a canonical SHA-256 over the complete secret-free report body. The verifier detects later changes to the report representation.

## Claims boundary

Every v1.1 report keeps these false:

- `live_environment_validated`
- `partner_validated`
- `flight_validated`
- `operationally_validated`

`AUTHORIZED_READ_READY` must never be interpreted as evidence that a read occurred or that any external environment was validated.

## Control boundary

v1.1 does not instantiate the OAuth token provider or read-only SSE transport and adds no network call, token acquisition, stream consumption, partner communication, entity publication, task mutation, manual-control, flight-control, weapons, or arbitrary HTTP operation.
