# ECHO EXTERNAL SIGNER BOUNDARY

Status: **IMPLEMENTED IN SOFTWARE ON CANDIDATE BRANCH / REQUIRES PARTNER OR HARDWARE VALIDATION**

## Purpose

This change prepares ECHO checkpoint signing for a non-exportable or independently managed signer without claiming that such custody exists today.

The protected-main baseline signs checkpoints with Ed25519 private-key material loaded from a tightly permissioned local PEM file. That path has strong local file controls, but the private key is still software-readable inside the service trust domain.

external-signer requires a stronger custody boundary.

## Software boundary

ECHO checkpoint creation now accepts an injected signer with four capabilities only:

- report algorithm;
- report bounded key ID;
- expose public-key bytes;
- sign canonical checkpoint-manifest bytes.

ECHO does not require an injected signer to expose private-key bytes.

The existing local PEM path is retained through a compatibility signer and remains the default when no signer mode is explicitly selected.

## Explicit mode behavior

`ECHO_CHECKPOINT_SIGNER_MODE` supports:

- `LOCAL_PEM` — existing local Ed25519 PEM path;
- `EXTERNAL` — fails closed in `from_environment()` until an actual external signer adapter is injected.

There is intentionally no automatic fallback from `EXTERNAL` to `LOCAL_PEM`.

This prevents a deployment that requested external custody from silently receiving weaker local custody because the external signer is unavailable.

## Returned-signature verification

ECHO verifies every signer-returned signature locally against the signer's declared public key before inserting the checkpoint into the ledger.

A signer that is unavailable, errors, returns a malformed signature, or returns a signature that does not verify blocks checkpoint creation.

Unsigned checkpoint fallback is not permitted.

## Signing-request minimization

New checkpoints do not send the full manifest to the signer. ECHO computes the canonical manifest SHA-256 digest and signs a domain-separated, fixed-size digest input.

The full manifest remains in the checkpoint bundle so verifiers can recompute the digest. Historical bundles that have no signature-input mode remain verifiable under the legacy raw-manifest signature path.

A regression test places a distinctive payload marker in an ECHO event and verifies that neither the marker nor its field name reaches the signer request.

### Fixed 100-event 10x efficiency gate

For a fixed 100-event checkpoint, the test compares:

- baseline: byte length of the legacy canonical raw-manifest signing request;
- candidate: byte length of the new domain-separated digest signing request.

The candidate must be at least **10x smaller** than the baseline.

This is a narrow signer-request byte-count metric. It does not establish 10x end-to-end performance, 10x lower cost, or 10x overall security.

## Key identity

The existing checkpoint database binding of:

`key_id -> public-key fingerprint`

applies equally to injected signers.

Reusing an existing key ID with different public-key material fails closed.

## What this precursor proves

Under repository-controlled tests, the software boundary demonstrates:

1. ECHO can create and verify a signed checkpoint through a signer interface without receiving private-key bytes through that interface;
2. the existing local PEM path remains compatible;
3. external mode does not silently downgrade to local PEM;
4. signer-returned invalid signatures are rejected before persistence;
5. signer key-ID rebinding is rejected;
6. the signing request excludes event payload content under the tested checkpoint schema;
7. the fixed 100-event signing request is at least 10x smaller than the legacy raw-manifest request while legacy verification remains supported.

## AWS KMS Ed25519 adapter

The candidate also includes a dependency-injected AWS KMS adapter for the current `ECC_NIST_EDWARDS25519` / `ED25519_SHA_512` API shape.

The adapter:

- validates the KMS key spec is Ed25519 and usage is `SIGN_VERIFY`;
- requires `ED25519_SHA_512` support;
- resolves and pins the KMS key identity returned by `GetPublicKey`;
- uses `MessageType=RAW`;
- rejects a changed key identity or signing algorithm in the sign response;
- exposes only the Ed25519 public key to ECHO;
- does not own AWS credentials or add the AWS SDK as a mandatory runtime dependency.

The adapter is tested with a local fake KMS client. This is **not** evidence that a live AWS KMS key has been provisioned or validated for Worldshepherd.

## What it does **not** prove

This change is **not external-signer completion** and is not evidence of 10x custody improvement.

It does not prove:

- a hardware-backed or non-exportable key exists;
- KMS/HSM/TPM/FIPS validation;
- external signer availability or service authentication;
- private-key non-exportability;
- signer non-compromise;
- privileged-host compromise resistance;
- external monotonic counters or rollback prevention;
- independent validation.

Maximum claim before a real signer is attached:

**IMPLEMENTED IN SOFTWARE / REQUIRES PARTNER OR HARDWARE VALIDATION**

## external-signer promotion evidence

To promote external-signer, attach an actual non-exportable or independently managed signer and retain evidence for the fixed #435 test set, including:

- key export attempt/result;
- external-mode no-fallback result;
- trusted signer fingerprint mismatch result;
- invalid signature result;
- explicit key-rotation evidence;
- checkpoint rollback/stale-anchor result;
- environment and signer product/configuration;
- evaluator identity/custody where applicable.

Only then should the measured residual exposure ratio be calculated against the predeclared baseline.
