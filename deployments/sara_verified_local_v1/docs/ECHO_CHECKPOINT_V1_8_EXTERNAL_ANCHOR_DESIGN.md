# ECHO SENTINEL LINK external checkpoint anchoring v1.8

## Purpose

v1.8 adds a bounded anchor-request and read-back verification layer around the signed ECHO checkpoint bundles implemented in v1.7. It does **not** change the v1.7 checkpoint schema, signing key, Merkle construction, predecessor chain, or local checkpoint database.

The design goal is to make a verified checkpoint digest portable to an external publication surface and to require independently retrieved content before software may label that publication as `VERIFIED_READ_BACK`.

## Trust boundary

v1.8 separates three facts that must not be collapsed into one claim:

1. **Checkpoint validity** — v1.7 verifies the Ed25519 signature, trusted ECHO key fingerprint, event ordering, Merkle root, predecessor chain, and monotonic membership.
2. **Anchor-contract validity** — v1.8 deterministically binds the verified checkpoint sequence, ID, checkpoint SHA-256, ECHO key ID, and pinned key fingerprint into a domain-separated anchor payload and request digest.
3. **External observability** — only an actual provider publication followed by a separate read-back of the exact anchor request can establish that the digest was externally observable at that provider reference.

A local test provider exercises the contract in CI but is permanently labeled `SIMULATED_ONLY` and cannot satisfy external read-back mode.

## Anchor request

The request schema is `WS-ECHO-CHECKPOINT-ANCHOR-REQUEST-V1`.

The request is built only after the supplied checkpoint bundle passes the v1.7 `verify_bundle()` path against an expected, separately supplied ECHO checkpoint-key fingerprint.

The request binds:

- checkpoint sequence;
- checkpoint ID;
- checkpoint SHA-256;
- ECHO checkpoint key ID;
- trusted ECHO public-key fingerprint;
- a domain-separated anchor payload SHA-256;
- an anchor-request SHA-256 over the canonical request.

The anchor payload digest is computed over the checkpoint binding using the domain separator `WS-ECHO-CHECKPOINT-EXTERNAL-ANCHOR-V1`.

## Provider evidence

Provider evidence uses `WS-ECHO-CHECKPOINT-ANCHOR-EVIDENCE-V1`.

Two provider modes exist in the v1.8 reference software:

### `TEST_PROVIDER`

Used only for deterministic CI and negative testing. The provider is fixed to `WORLDSHEPHERD_TEST_PROVIDER`, references must use `test://`, and verification state must remain `SIMULATED_ONLY`.

### `EXTERNAL_READ_BACK`

This mode cannot be established by hashes alone. Verification requires the actual provider document retrieved outside the ECHO service. The document must parse as a JSON object and equal the exact deterministic anchor request. The verifier then recomputes the canonical provider-content SHA-256 and requires it to match the evidence record.

The software performs no network fetch itself. This is intentional: provider retrieval is a separately evidenced control-plane action, allowing the read-back source, identity, authorization, and transport to be audited independently from ECHO.

## Receipt

The receipt schema is `WS-ECHO-CHECKPOINT-ANCHOR-RECEIPT-V1`.

A receipt binds the checkpoint, anchor request, provider identity/mode/reference, evidence digest, verification state, and provider-content digest where external read-back applies. A receipt SHA-256 detects alteration of that normalized receipt.

For `EXTERNAL_READ_BACK`, receipt verification again requires the retrieved provider document. A receipt alone is insufficient.

## Claims boundary

After protected exact-head CI passes and this software is merged, Worldshepherd may claim:

- `IMPLEMENTED IN SOFTWARE` — deterministic checkpoint anchor requests;
- `IMPLEMENTED IN SOFTWARE` — provider evidence and receipt schemas;
- `IMPLEMENTED IN SOFTWARE` — fail-closed test-provider separation;
- `IMPLEMENTED IN SOFTWARE` — external read-back verification requiring the actual retrieved provider document;
- `IMPLEMENTED IN SOFTWARE` — tamper detection for checkpoint/request/provider-content/receipt binding.

These statements do **not** establish that any checkpoint has actually been externally anchored.

After a real provider publication is performed and a separately retrieved provider document passes the v1.8 verifier, the bounded evidence statement may be:

> `PROVEN INTERNALLY — the identified checkpoint anchor request was externally observable at the recorded provider reference and matched on read-back.`

That statement still does **not** establish:

- independent third-party attestation when the provider account is controlled by Worldshepherd;
- immutable or WORM retention;
- transparency-log or trusted-timestamp guarantees unless the chosen provider separately proves them;
- protection against a privileged actor deleting or rewriting both local and remote records;
- legal chain-of-custody status;
- production HSM/KMS custody;
- certification, government authorization, or customer acceptance;
- exactly-once transport;
- physical-system qualification.

## Protected validation gate

The v1.8 candidate must demonstrate on the exact candidate commit:

1. anchor requests are deterministic for the same verified v1.7 checkpoint;
2. an untrusted ECHO checkpoint-key fingerprint is rejected;
3. the CI test provider remains `SIMULATED_ONLY`;
4. changing checkpoint binding data invalidates a receipt even when the attacker recomputes the receipt digest;
5. `EXTERNAL_READ_BACK` cannot pass without an actual provider document;
6. an external provider document must equal the exact deterministic anchor request;
7. provider-content SHA-256 is recomputed from the retrieved document rather than trusted from the receipt;
8. a different retrieved provider document is rejected;
9. the existing full unit/API suite remains green;
10. existing deployment, destructive recovery, operational snapshot, release identity, and release evidence-index gates remain green.

## Operational sequence for a real external anchor

1. export a verified v1.7 checkpoint bundle;
2. calculate or supply the trusted ECHO key fingerprint independently;
3. run `ws-echo-anchor request` to produce the deterministic anchor request;
4. publish that exact JSON request through the authorized provider control plane;
5. retrieve the published JSON through a separate read-back path;
6. record provider identity, reference, retrieval time, and retrieved content;
7. construct external read-back evidence from the exact retrieved document;
8. build and verify the anchor receipt;
9. retain the local checkpoint, request, provider evidence, receipt, provider read-back, and provider locator together in the release evidence set.

The external publication/read-back operation is a separate evidence action and must not be inferred merely from successful CI.
