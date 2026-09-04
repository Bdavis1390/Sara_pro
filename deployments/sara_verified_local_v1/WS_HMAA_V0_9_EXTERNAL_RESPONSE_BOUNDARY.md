# WS-HMAA v0.9 — External Attestation Return Boundary

## Purpose

v0.9 defines how an independently produced partner-attestation response can be represented and assessed against a v0.8 partner-validation request. It separates structural integrity, signature authenticity, and human acceptance so that no single software step can manufacture a partner- or live-validation claim.

## Binding requirements

A response must bind exactly to the v0.8 request through:

- `request_package_sha256`;
- mission ID; and
- requested scope.

The response also carries an organization identifier, reviewer identifier, UTC-capable attestation timestamp, outcome, confirmed requested-check digests, evidence references, external-signature metadata, and a response SHA-256.

## Integrity vs. authenticity

The response SHA-256 detects alteration of the response container. It does **not** authenticate the external organization or reviewer.

Authenticity is delegated to the `PartnerAttestationVerifier` protocol. The production default is fail-closed and returns an unverified result until a trusted verifier is explicitly configured. v0.9 does not implement custom cryptography or embed a trust store.

## Outcome states

- `UNVERIFIED_EXTERNAL_RESPONSE`: structurally bound evidence exists, but external signature authenticity is not established.
- `VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE`: an authenticated `CONFIRMED` response covers every requested check, but a human must still accept it.
- `VERIFIED_RESPONSE_REQUIRES_HUMAN_REVIEW`: an authenticated `PARTIAL` response requires human review.
- `VERIFIED_RESPONSE_REJECTED`: an authenticated reviewer rejection is preserved as a rejection.

## Claims boundary

Every v0.9 assessment keeps all of these false:

- `partner_validated`
- `live_environment_validated`
- `flight_validated`
- `operationally_validated`

The only claimable labels remain:

- `IMPLEMENTED IN SOFTWARE`
- `REQUIRES PARTNER VALIDATION`

A future human-acceptance workflow may record a governed acceptance decision, but it must remain distinct from flight or operational validation and must not infer facts that the external evidence did not attest.

## Check coverage

Each v0.8 requested check is represented by a SHA-256 digest of its canonical text. A `CONFIRMED` external response must cover every requested check. Unknown check references are rejected. A `REJECTED` response may not simultaneously assert confirmed checks.

## Control boundary

v0.9 adds no network transport, email/messaging, OAuth behavior, credentials, trust-store mutation, entity publication, task mutation, manual-control, flight-control, weapons, or arbitrary HTTP operation. It only assesses an externally supplied response object against an existing v0.8 request.
