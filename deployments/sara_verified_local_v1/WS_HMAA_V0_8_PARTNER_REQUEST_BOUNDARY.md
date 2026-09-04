# WS-HMAA v0.8 — Partner Validation Request Boundary

## Purpose

v0.8 converts a v0.7 `EXTERNAL_ATTESTATION_REQUIRED` report into a canonical, secret-free validation request that can be reviewed by an authorized external partner. It does not perform external validation and cannot convert the request into a live-validation claim.

## Preconditions

A package can be built only when:

- the v0.7 report state is `EXTERNAL_ATTESTATION_REQUIRED`;
- repeatability is satisfied;
- `live_environment_validated` is false;
- external attestation remains required;
- an aggregate attestation SHA-256 is present;
- one mission ID is present; and
- at least three distinct qualifying capture references remain internally consistent.

## Exported evidence

The request contains only:

- mission ID;
- attestation aggregate SHA-256;
- distinct qualifying capture count;
- capture SHA-256 references;
- fixture SHA-256 references;
- final evidence-chain hashes;
- event counts;
- requested partner validation checks;
- current claim labels and prohibited claims; and
- a canonical package SHA-256.

Raw entity/task stream payloads and credentials are intentionally excluded.

## Requested validation scope

The fixed request scope is `read-only-sandbox-interoperability`.

The external reviewer is asked to confirm authorization and environment provenance, verify that the cited evidence originated from the stated read-only environment, confirm that WS-HMAA did not request write/control actions, validate the referenced hashes, and return an independently attributable attestation bound to the package SHA-256.

## Claims boundary

The package status is `READY_FOR_PARTNER_VALIDATION_REQUEST`. It does not mean the request was sent, received, reviewed, approved, or validated.

Allowed labels remain:

- `IMPLEMENTED IN SOFTWARE`
- `REQUIRES PARTNER VALIDATION`

Explicitly prohibited claims include:

- `LIVE_ENVIRONMENT_VALIDATED`
- `PARTNER_VALIDATED`
- `FLIGHT_VALIDATED`
- `OPERATIONALLY_VALIDATED`

## Control boundary

v0.8 adds no network operation, OAuth behavior, partner communication, entity publication, task mutation, manual-control, flight-control, weapons, or arbitrary HTTP behavior. It only transforms an already-qualified v0.7 report into a hash-bound review package.
