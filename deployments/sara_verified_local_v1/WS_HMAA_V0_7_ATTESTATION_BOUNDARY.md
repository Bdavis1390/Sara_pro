# WS-HMAA v0.7 — Evidence Attestation Boundary

## Purpose

v0.7 adds a claims-control layer over the existing bounded read-only capture and HMAA evidence-chain implementation. It measures whether candidate evidence is internally coherent and repeatable without converting that evidence into a claim that an external Lattice Sandbox has been validated.

## State model

- `NO_EVIDENCE`: no qualifying capture has been supplied.
- `CANDIDATE_EVIDENCE`: one or more qualifying captures exist, but the distinct-capture repeatability threshold has not been met.
- `EXTERNAL_ATTESTATION_REQUIRED`: the configured repeatability threshold has been met. This is the highest state v0.7 can produce.

There is deliberately no v0.7 transition to `LIVE_READ_VALIDATED`.

## Qualification rules

A candidate capture qualifies only when all of the following are true:

1. Capture and interop manifest both retain `live_environment_validated=false`.
2. Capture and manifest retain the bounded source label `authorized-sandbox-readonly-candidate`.
3. The finite sample count is nonzero and matches the manifest event count.
4. Evidence-bundle and manifest mission IDs match.
5. Evidence-bundle and manifest final chain hashes are present and identical.
6. Disposition totals match the event count.
7. Every captured event is `ALLOW`; `WARN`, `REVIEW`, or `INDETERMINATE` evidence cannot promote repeatability readiness.
8. Captures must use one mission ID for a single attestation package.
9. Duplicate capture digests do not count toward repeatability.

The default repeatability threshold is three distinct qualifying captures.

## Integrity

Each qualifying capture is reduced to a secret-free canonical reference and SHA-256 digest. The aggregate attestation digest is derived from the sorted set of distinct capture digests, making the aggregate deterministic and order-independent.

No bearer token, OAuth client secret, Sandbox authorization token, response body outside the already-normalized evidence manifest, or credential metadata is accepted by the attestation model.

## Claims boundary

v0.7 may support only these labels:

- `IMPLEMENTED IN SOFTWARE`
- `REQUIRES PARTNER VALIDATION`

v0.7 does **not** establish `PROVEN INTERNALLY`, partner validation, flight validation, operational validation, or live-environment validation.

A future external-validation increment must ingest independently produced evidence/attestation through a separately governed mechanism before any live-validation state can be considered. That mechanism is intentionally absent from v0.7.

## Control boundary

v0.7 adds no network transport, credential acquisition, entity publication, task creation/update, manual-control, flight-control, weapons, or arbitrary HTTP operation. It operates only on already-produced finite read-only capture results.
