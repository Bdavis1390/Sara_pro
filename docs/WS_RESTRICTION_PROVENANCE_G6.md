# WS-RESTRICTION-PROVENANCE G6 — PRIME SIGNED EVIDENCE

Status: **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH / PENDING G5 + INTERNAL VALIDATION**

## Objective

G6 moves new restriction evidence from application-level authority labeling to independently verifiable PRIME Ed25519 authenticity.

SARA remains verification-only. PRIME private signing key material is not accepted, generated, derived, or stored by the restriction pipeline.

## Trust primitive reuse

G6 reuses the existing `PrimeSentinelVerifier` public-key trust store and revocation configuration.

The verifier is refactored to expose one detached Ed25519 verification primitive. Existing PRIME requalification authorization now uses that same primitive, preventing a parallel cryptographic implementation.

The shared verifier enforces:

- configured public key;
- unknown-key rejection;
- revoked-key rejection;
- strict base64url signature decoding;
- Ed25519 verification;
- SHA-256 public-key fingerprint derivation.

## Signature protocol

The external PRIME signer signs a domain-separated canonical message:

```text
WS-RESTRICTION-PRIME-SIGNATURE-V1\0
canonical_json({
  schema,
  issuer,
  signing_key_id,
  restriction: <complete safe V3 restriction document>
})
```

The signed restriction contains no raw prompt, blocked candidate output, safe replacement text, HMAC key, or PRIME private key.

Because the complete V3 safe document is signed, the signature covers:

- restriction ID;
- PRIME application authority;
- HMAC fingerprint key epoch ID;
- action and reason code;
- source/processor;
- version/policy/correlation lineage;
- content fingerprints;
- approved context profile and typed metadata;
- raw-content-persistence assertion.

## V4 signed envelope

After detached signature verification, SARA constructs:

```text
WS-RESTRICTION-PROVENANCE-V4
  restriction     = complete V3 safe restriction document
  prime_signature = verified signature attestation
```

The signature attestation records only:

- signing key ID;
- configured public-key SHA-256 fingerprint;
- Ed25519 signature;
- SHA-256 digest of the exact domain-separated signed message;
- restriction ID.

The public-key fingerprint is derived from SARA's configured verification key, not supplied as trusted caller metadata.

## Signed-only new-event emission

G6 retires the unsigned `queue_restriction_event()` path. It remains as a fail-closed migration sentinel that raises an explicit error.

New restriction events enter the SARA -> ECHO outbox only through `queue_signed_restriction_event()`, which accepts a `VerifiedSignedRestriction` produced after successful PRIME signature verification.

Historical V1-V3 records remain readable but cannot be newly emitted through the governed unsigned helper.

## Read-time re-verification

G6 does not rely only on verification before persistence.

OVERWATCH/G2 observability revalidates V4 records from serialized evidence using the current PRIME verifier:

1. outer SARA actor and delivery metadata;
2. nested V3 structure, semantic restriction ID, authority, context profile, and key epoch;
3. PRIME signature schema and restriction-ID binding;
4. detached Ed25519 signature against the current configured public key;
5. configured public-key fingerprint;
6. signed-message digest.

If the signing key is unknown or currently revoked, the V4 record is preserved as bytes but does not count as currently verified evidence.

## Projection minimization

Administrator projections do not return the signature value or full signature object.

They add only:

- signed envelope schema;
- wrapped restriction schema;
- `signature_verified=true`;
- signing key ID;
- configured public-key fingerprint.

This is enough to diagnose assurance state without turning OVERWATCH into a signature-export API.

## Acceptance tests

The G6 suite verifies:

1. generic detached PRIME signatures verify using public keys only;
2. message tampering fails;
3. signature-byte tampering fails;
4. unknown keys fail;
5. revoked keys fail;
6. malformed signatures and empty messages fail;
7. the existing PRIME authorization flow still uses the shared verifier;
8. restriction signatures bind the complete safe V3 document;
9. expected signing key ID is part of the signed message;
10. verified V4 envelopes queue through normal SARA outbox semantics;
11. raw restriction/HMAC secret material is absent from the signed envelope;
12. tampered restriction evidence cannot be bound as verified V4;
13. V4 observability re-verifies signatures on read;
14. signature/public-key-fingerprint/message-digest tampering fails;
15. revoked signing keys make V4 evidence currently untrusted;
16. unsigned new-event queueing fails closed;
17. required CI executes PRIME authorization plus G1-G6 restriction suites together.

## Cumulative 10x gate

G6 extends the G3-start residual-risk baseline to seven declared classes by adding:

```text
new restriction events can enter SARA without independently verified PRIME signature
```

The cumulative requirement is **0/7 open classes** while every previously zero-tolerance channel remains closed.

This metric is a declared attack-path/provenance metric. It is not a claim of 10x Ed25519 strength or 10x lower real-world incident probability.

## Claims boundary

G6 establishes software-level verification of Ed25519 signatures against configured PRIME public keys.

It does not establish:

- HSM/TPM-backed private-key custody;
- external certificate authority status;
- FIPS validation;
- secure key destruction;
- independent transparency-log or witness publication;
- proof that a human approved each signed event;
- secure erasure of transient Python strings.

Those are separate gates.

Until G5 is merged and G6 is reconciled onto that protected head, then passes exact-head required CI, broader Verified Local validation, and protected merge, classify G6 as **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH / PENDING INTERNAL VALIDATION**.
