# ECHO G7 SIGNER BOUNDARY PRECURSOR

Status: **IMPLEMENTED IN SOFTWARE ON CANDIDATE BRANCH / REQUIRES PARTNER OR HARDWARE VALIDATION**

Related gate: #435

## Purpose

This change prepares ECHO checkpoint signing for a non-exportable or independently managed signer without claiming that such custody exists today.

The protected-main baseline signs checkpoints with Ed25519 private-key material loaded from a tightly permissioned local PEM file. That path has strong local file controls, but the private key is still software-readable inside the service trust domain.

G7 requires a stronger custody boundary.

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

The signer receives canonical checkpoint-manifest bytes only.

The manifest contains event IDs and semantic SHA-256 digests, not ECHO event payload bodies. A regression test places a distinctive payload marker in an ECHO event and verifies that the marker and its field name do not reach the signer request.

This does not prove that every future manifest field is non-sensitive; future schema changes must preserve the same review boundary.

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
6. the signing request excludes event payload content under the tested checkpoint schema.

## What it does **not** prove

This change is **not G7 completion** and is not evidence of 10x custody improvement.

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

## G7 promotion evidence

To promote G7, attach an actual non-exportable or independently managed signer and retain evidence for the fixed #435 test set, including:

- key export attempt/result;
- external-mode no-fallback result;
- trusted signer fingerprint mismatch result;
- invalid signature result;
- explicit key-rotation evidence;
- checkpoint rollback/stale-anchor result;
- environment and signer product/configuration;
- evaluator identity/custody where applicable.

Only then should the measured residual exposure ratio be calculated against the predeclared baseline.
