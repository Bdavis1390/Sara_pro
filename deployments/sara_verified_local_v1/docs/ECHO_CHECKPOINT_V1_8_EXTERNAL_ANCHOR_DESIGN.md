# ECHO SENTINEL LINK external checkpoint anchoring v1.8

## Purpose

v1.8 adds a bounded anchor-request and read-back content-verification layer around the signed ECHO checkpoint bundles implemented in v1.7. It does **not** change the v1.7 checkpoint schema, signing key, Merkle construction, predecessor chain, or local checkpoint database.

The design goal is to make a verified checkpoint digest portable to an external publication surface while preventing the reference software from granting itself external-provider provenance.

## Trust boundary

v1.8 separates four facts that must not be collapsed into one claim:

1. **Checkpoint validity** — v1.7 verifies the Ed25519 signature, trusted ECHO key fingerprint, event ordering, Merkle root, predecessor chain, and monotonic membership.
2. **Anchor-contract validity** — v1.8 deterministically binds the verified checkpoint sequence, ID, checkpoint SHA-256, ECHO key ID, and pinned key fingerprint into a domain-separated anchor payload and request digest.
3. **Read-back content match** — v1.8 can prove that a supplied JSON document exactly equals the deterministic anchor request and can bind that content to an evidence artifact and receipt.
4. **Provider retrieval provenance** — proof that the supplied document was actually retrieved from the stated remote provider/reference is a separate evidence action outside this local verifier.

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

This mode cannot be established by hashes alone. Verification requires the actual provider document supplied to the verifier. The document must parse as a JSON object and equal the exact deterministic anchor request. The verifier recomputes the canonical provider-content SHA-256 and requires it to match the evidence record.

Successful content verification is labeled `READ_BACK_CONTENT_MATCH`, not `VERIFIED_READ_BACK`. This wording is deliberate. The local software performs no network fetch and therefore cannot prove that the supplied document actually came from the stated provider URL or account.

The caller must preserve separate provider-retrieval evidence tying the supplied provider document to the provider reference. That control-plane evidence may come from an authenticated provider API response, independently captured retrieval record, transparency/timestamp service, or another separately evaluated mechanism. Its strength must be assessed on its own terms.

## Receipt and complete evidence set

The receipt schema is `WS-ECHO-CHECKPOINT-ANCHOR-RECEIPT-V1`.

A receipt binds the checkpoint, anchor request, provider identity/mode/reference, evidence digest, verification state, and provider-content digest where external read-back applies. A receipt SHA-256 detects alteration of that normalized receipt.

Receipt verification is deliberately **not** receipt-only. The verifier requires the actual evidence artifact and reconstructs the expected receipt from that evidence. A syntactically valid evidence SHA-256 written into a receipt is insufficient. If the supplied evidence artifact differs—even if its own digest has been recomputed—the original receipt is rejected.

For `EXTERNAL_READ_BACK`, the complete local verification set is:

- signed v1.7 checkpoint bundle;
- separately supplied trusted ECHO checkpoint-key fingerprint;
- provider evidence artifact;
- anchor receipt;
- supplied provider read-back document.

The provider document must exactly equal the deterministic anchor request. Passing this set proves content binding only. Provider-retrieval provenance remains a separate external evidence gate.

## Claims boundary

After protected exact-head CI passes and this software is merged, Worldshepherd may claim:

- `IMPLEMENTED IN SOFTWARE` — deterministic checkpoint anchor requests;
- `IMPLEMENTED IN SOFTWARE` — provider evidence and receipt schemas;
- `IMPLEMENTED IN SOFTWARE` — fail-closed test-provider separation;
- `IMPLEMENTED IN SOFTWARE` — receipt verification requiring the actual evidence artifact;
- `IMPLEMENTED IN SOFTWARE` — read-back content matching requiring the actual supplied provider document;
- `IMPLEMENTED IN SOFTWARE` — tamper detection across checkpoint/request/evidence/provider-content/receipt binding.

These statements do **not** establish that any checkpoint has actually been externally published or externally retrieved.

Only after a real provider publication is performed **and** a separately evidenced provider retrieval supplies the document that passes the v1.8 content verifier may the bounded evidence statement be:

> `PROVEN INTERNALLY — the identified checkpoint anchor request was observed through the separately evidenced provider retrieval and its content matched the local deterministic anchor request.`

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
5. receipt verification requires the actual evidence artifact, not only its stated digest;
6. substituting a different internally valid evidence artifact invalidates the original receipt;
7. `EXTERNAL_READ_BACK` cannot pass content verification without an actual provider document;
8. an external provider document must equal the exact deterministic anchor request;
9. provider-content SHA-256 is recomputed from the supplied document rather than trusted from the receipt;
10. a different provider document is rejected;
11. external mode reports `READ_BACK_CONTENT_MATCH` and does not assert provider-retrieval provenance;
12. the existing full unit/API suite remains green;
13. existing deployment, destructive recovery, operational snapshot, release identity, and release evidence-index gates remain green.

## Operational sequence for a real external anchor

1. export a verified v1.7 checkpoint bundle;
2. calculate or supply the trusted ECHO key fingerprint independently;
3. run `ws-echo-anchor request` to produce the deterministic anchor request;
4. publish that exact JSON request through the authorized provider control plane;
5. retrieve the published JSON through a separate, evidenced provider path;
6. retain the provider retrieval response/metadata sufficient to support the provenance claim actually being made;
7. construct read-back evidence from the supplied retrieved document;
8. build the receipt from that evidence;
9. verify the checkpoint, evidence artifact, receipt, and provider document together;
10. retain the checkpoint, request, provider evidence, receipt, read-back content, provider retrieval evidence, and provider locator together in the release evidence set.

The publication/retrieval operation is a separate evidence action and must not be inferred merely from successful CI or from a caller supplying matching JSON to the local verifier.
