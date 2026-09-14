# Worldshepherd / WS-HMAA — Lattice Sandbox Read-Only Validation Brief

**Document status:** non-confidential technical validation brief  
**Requested scope:** `read-only-sandbox-interoperability`  
**Current claim state:** `IMPLEMENTED IN SOFTWARE` / `REQUIRES PARTNER VALIDATION`

## Objective

Evaluate whether the Worldshepherd HMAA assurance layer can consume a small, finite sample of Lattice entity/task stream events from an authorized Lattice Sandbox, normalize the public-contract messages, apply its existing assurance/evidence logic, and produce independently checkable evidence without invoking any write or control action.

This is an interoperability and evidence-governance exercise, not an operational, flight, autonomy, weapons, or mission-performance demonstration.

## Requested environment

The exercise is intended for an authorized Lattice Sandboxes environment using Anduril's documented Sandbox credential model and public REST streaming interfaces.

WS-HMAA permits only the documented Sandbox host shape:

`<environment-id>.env.sandboxes.developer.anduril.com`

The bounded transport exposes only:

- `POST /api/v1/entities/stream`
- `POST /api/v1/tasks/stream`

When client credentials are used, the credential provider additionally uses:

- `POST /api/v1/oauth/token`

No arbitrary host, arbitrary path, redirect target, entity publish endpoint, task mutation endpoint, taskable-agent execution stream, or manual-control path is exposed by the session runner.

## Proposed test sequence

1. **Human authorization** — reviewer/operator confirms that the specified Sandbox environment is authorized for this test.
2. **Zero-network preflight** — WS-HMAA validates endpoint shape, credential presence, exclusive credential mode, finite capture limits, and explicit authorization posture. The preflight performs no network call.
3. **Credential establishment** — use either the supplied static environment token or the documented OAuth client-credentials flow. OAuth access tokens remain memory-only.
4. **Finite read attempt** — consume only the configured number of entity/task SSE messages, then close each stream iterator.
5. **Contract normalization** — transform documented stream envelopes into HMAA events while preserving source-event identity through canonical SHA-256 identifiers.
6. **Assurance evaluation** — run the existing state/evidence assessment. Any non-`ALLOW` disposition prevents qualification.
7. **Evidence sealing** — chain captured events, record fixture/capture hashes, and generate a secret-free session receipt.
8. **Repeatability check** — repeat the bounded capture. Three attempts do not automatically qualify; at least three **distinct** qualifying capture hashes are required.
9. **Evidence request generation** — if the repeatability threshold is satisfied, generate the existing v0.8 evidence-reference request.
10. **Session binding** — wrap that evidence request in the preferred v1.2 external exchange package, binding the exact Sandbox endpoint, zero-network preflight digest, executed session-receipt digest, inner request digest, aggregate attestation, and qualifying capture references.
11. **Independent review** — reviewer confirms environment provenance/authorization, read-only origin, absence of write/control requests, and the bound evidence hashes.
12. **Authenticated response and human acceptance** — any external response must bind to the v1.2 package hash and pass configured signature verification. A `CONFIRMED` result still requires a separate governed human acceptance decision.

## Acceptance criteria for the bounded interoperability exercise

The exercise is successful for the requested scope only when all of the following are true:

- the preflight state is `AUTHORIZED_READ_READY`;
- all external calls are confined to the documented Sandbox OAuth/read-only stream surface;
- at least one finite stream message is captured;
- each qualifying capture is fully `ALLOW` under the existing assurance evaluator;
- captured event counts and evidence-chain heads are internally consistent;
- the session receipt verifies against its SHA-256 digest;
- the local artifact manifest verifies all retained evidence-file hashes;
- no credential value appears in the serialized evidence package;
- the preferred v1.2 partner exchange package cryptographically binds the exact endpoint, preflight, session receipt, inner evidence request, and qualifying capture evidence; and
- every package remains explicitly marked `REQUIRES PARTNER VALIDATION` until an independently authenticated response is reviewed and accepted for the requested scope.

## Preferred partner exchange artifact

The preferred external exchange artifact is:

`partner-session-validation-request-v1.2.json`

Its canonical `package_sha256` covers:

- mission identifier;
- exact Sandbox endpoint;
- preflight report SHA-256;
- session receipt SHA-256;
- inner `partner-validation-request-v0.8.json` package SHA-256;
- aggregate attestation SHA-256;
- qualifying capture references;
- fixture and evidence-chain references inherited from the inner request;
- the exact requested validation checks; and
- the claim/prohibition boundary.

The accompanying `partner-validation-request-v0.8.json` is retained as the inner evidence-reference request. It is **not** the final session-binding artifact because it predates the executable v1.2 session protocol and does not itself bind the precise endpoint and session receipt.

For a v1.2 review, the reviewer's response must set `request_package_sha256` to the SHA-256 of `partner-session-validation-request-v1.2.json`, not to the inner v0.8 request hash. A response bound only to the v0.8 package is rejected by the v1.2 assessor.

## External response semantics

The partner response must identify the same mission and requested scope and must confirm the exact requested-check digests. The configured verifier must authenticate the response signature before it can advance beyond `UNVERIFIED_EXTERNAL_RESPONSE`.

Even an authenticated `CONFIRMED` response advances only to:

`VERIFIED_RESPONSE_REQUIRES_HUMAN_ACCEPTANCE`

It does not automatically set generalized `partner_validated`, `live_environment_validated`, `flight_validated`, or `operationally_validated` flags. The existing governed human-acceptance record is the next mandatory step and remains limited to the exact requested attestation scope.

## What a successful run does **not** establish

Even a technically successful session does not by itself establish:

- generalized Anduril endorsement or validation;
- production-Lattice compatibility beyond the reviewed Sandbox scope;
- live-environment provenance absent independent confirmation;
- flightworthiness;
- autonomous mission performance;
- weapons-system integration or authorization;
- operational suitability; or
- government accreditation/certification.

Those claims remain outside the test boundary.

## Evidence supplied to the reviewer

The partner-facing v1.2 package can provide, without credentials or raw stream payloads:

- mission identifier;
- exact Sandbox endpoint;
- preflight and session-receipt hashes;
- inner v0.8 evidence-request hash;
- distinct qualifying capture count;
- capture SHA-256 references;
- fixture SHA-256 references;
- final evidence-chain hashes;
- event counts;
- aggregate attestation SHA-256;
- exact requested validation checks; and
- the canonical v1.2 session-partner package SHA-256.

Raw simulated capture payloads remain local unless an authorized reviewer specifically requests them through an approved exchange path.

## Requested partner action

Provide an authorized Sandbox review path or technical contact who can independently witness/review this narrow exercise and return an attributable attestation whose `request_package_sha256` is bound to the generated **v1.2 session-partner package SHA-256**.

The desired outcome is deliberately narrow and falsifiable: **verify or falsify read-only Sandbox interoperability for one identified, authorized session under a reproducible, auditable boundary.**
