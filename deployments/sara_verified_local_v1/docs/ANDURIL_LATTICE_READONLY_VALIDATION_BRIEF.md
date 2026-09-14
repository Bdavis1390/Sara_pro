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
9. **Partner request generation** — only if the repeatability threshold is satisfied, generate the existing hash-bound partner-validation request.
10. **Independent review** — reviewer confirms environment provenance/authorization, read-only origin, absence of write/control requests, and evidence hashes.

## Acceptance criteria for the bounded interoperability exercise

The exercise is successful for the requested scope only when all of the following are true:

- the preflight state is `AUTHORIZED_READ_READY`;
- all external calls are confined to the documented Sandbox OAuth/read-only stream surface;
- at least one finite stream message is captured;
- each qualifying capture is fully `ALLOW` under the existing assurance evaluator;
- captured event counts and evidence-chain heads are internally consistent;
- the session receipt verifies against its SHA-256 digest;
- the local artifact manifest verifies all retained evidence-file hashes;
- no credential value appears in the serialized evidence package; and
- any partner-validation request remains explicitly marked `REQUIRES PARTNER VALIDATION`.

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

The partner-facing package can provide, without credentials or raw stream payloads:

- mission identifier;
- preflight/session receipt hashes;
- distinct capture count;
- capture SHA-256 references;
- fixture SHA-256 references;
- final evidence-chain hashes;
- event counts;
- aggregate attestation SHA-256;
- requested validation checks; and
- the canonical partner-request package SHA-256.

Raw simulated capture payloads can remain local unless the authorized reviewer specifically requests them through an approved exchange path.

## Requested partner action

Provide an authorized Sandbox review path or technical contact who can independently witness/review this narrow exercise and return an attributable attestation bound to the generated partner-request package SHA-256.

The desired outcome is deliberately modest: **verify or falsify read-only Sandbox interoperability under a reproducible, auditable boundary.**
