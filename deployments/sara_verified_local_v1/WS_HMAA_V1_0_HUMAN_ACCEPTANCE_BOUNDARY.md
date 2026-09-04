# WS-HMAA v1.0 — Human Acceptance Boundary

## Purpose

v1.0 adds the governed human decision step that follows a v0.9 external-attestation assessment. It records acceptance, rejection, or deferral without allowing a narrow partner attestation to become a broad validation claim.

## Acceptance preconditions

`ACCEPT` is legal only when the input assessment:

1. is `VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE`;
2. has an authenticated external signature;
3. carries a `CONFIRMED` outcome;
4. confirms every requested validation check;
5. still requires human acceptance; and
6. contains no preexisting partner/live/flight/operational validation claim.

Any violation fails closed.

## Decision states

- `PARTNER_ATTESTATION_ACCEPTED_FOR_REQUESTED_SCOPE`
- `PARTNER_ATTESTATION_REJECTED`
- `PARTNER_ATTESTATION_DEFERRED`

Rejection and deferral remain recordable for adverse, incomplete, or unverified assessments so the evidence trail can preserve an explicit human disposition.

## Evidence record

Each decision record binds to:

- decision ID and reviewer identifier;
- decision timestamp, action, and rationale;
- v0.8 request package SHA-256;
- v0.9 response SHA-256;
- verifier identifier; and
- a canonical record SHA-256.

The record hash detects later modification of the stored decision representation.

## Claims boundary

An accepted decision may state only:

- `IMPLEMENTED IN SOFTWARE`
- `PARTNER ATTESTATION ACCEPTED FOR REQUESTED SCOPE`

It explicitly keeps all of these false:

- `partner_validated`
- `live_environment_validated`
- `flight_validated`
- `operationally_validated`

The distinction is intentional: accepting an authenticated partner attestation for the narrow `read-only-sandbox-interoperability` request does not establish generalized partner validation, live-environment validation, flight validation, or operational validation.

## Control boundary

v1.0 adds no network transport, partner communication, OAuth behavior, credentials, signature trust store, entity publication, task mutation, manual-control, flight-control, weapons, or arbitrary HTTP operation. It records a human evidence disposition only.
