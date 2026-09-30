# WS-PRIME G8 — MONOTONIC VERIFICATION-ROOT ROLLBACK GUARD

Status: **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH / PENDING #452 + CURRENT-MAIN QUALIFICATION**

## Objective

G8 closes the local software rollback gap in PRIME verification-root configuration.

G7 already proves that SARA rejects PRIME private signing material and operates as a verification-only consumer. G6/G7 also verify signed restriction and ECHO evidence. Before G8, however, a privileged operator could restore an older but syntactically valid PRIME public-key / revocation configuration and SARA had no durable monotonic memory that the trust policy had moved forward.

G8 adds that memory and makes trust-root admission fail closed.

## Guarded trust material

The guarded PRIME trust material is derived from:

- `PRIME_SENTINEL_PUBLIC_KEYS_JSON`;
- `PRIME_SENTINEL_REVOKED_KEY_IDS`;
- `PRIME_SENTINEL_TRUST_EPOCH`.

Only public-key SHA-256 fingerprints, key IDs, revocation IDs, epoch, and a canonical trust-material SHA-256 digest are persisted.

Private signing keys are never accepted or persisted.

## Monotonic rules

The protected state schema is `WS-PRIME-TRUST-ROOT-V1`.

### First configuration

A configured PRIME trust root requires a positive integer `PRIME_SENTINEL_TRUST_EPOCH`.

The initial state is written under the protected registry namespace:

`PRIME_TRUST_ROOT_STATE`.

### Same epoch

Same epoch + identical canonical trust material is accepted.

Same epoch + changed key/revocation material fails closed.

### Lower epoch

Any epoch lower than the persisted epoch fails closed as rollback.

### Higher epoch

A higher epoch is accepted only when all of these hold:

1. every previously revoked key ID remains revoked;
2. an existing key ID is never rebound to different public-key material;
3. a removed key ID remains explicitly revoked;
4. newly introduced key IDs are allowed;
5. the candidate state is canonical and self-digesting.

This makes key retirement one-way at the software policy layer. Reusing a retired key ID for new key material is forbidden; rotation must use a new key ID.

## Runtime integration

The guard is the first PRIME trust decision after durable SARA storage is opened. It runs before the PRIME verifier is constructed and before any pending event-outbox replay.

A violation aborts startup before verifier construction or governed replay, preventing rollback-rejected configuration from producing startup-side effects.

When audit storage is functional, a rejected trust root appends only a bounded non-secret reason code such as `TRUST_EPOCH_ROLLBACK`, `KEY_ID_REBINDING`, or `REVOCATION_ROLLBACK`. Exception text, key IDs, public-key material, and configuration blobs are not copied into the rejection audit record.

The generic `/admin/registry` patch endpoint cannot modify `PRIME_TRUST_ROOT_STATE`.

Bounded health/startup evidence exposes only:

- guard status;
- epoch;
- trust-material digest.

## Executable 10x rollback metric

Frozen G7-boundary local rollback baseline: **4 accepted rollback classes**.

1. lower epoch;
2. same-epoch trust-material mutation;
3. higher-epoch key-ID rebinding;
4. revocation rollback.

G8 required residual: **0/4 accepted**.

10x threshold: `<= 0.4` residual classes.

Because the unit count is integral, practical pass condition is **0**.

This is a bounded software rollback metric, not a universal system-security multiplier.

## Additional invariants

Tests also require:

- configured roots without epoch fail closed;
- removed keys require explicit revocation;
- forward rotation with new key ID + old-key revocation succeeds;
- missing runtime trust configuration after prior initialization fails closed;
- stored state digest is self-checked;
- state survives service/store restart;
- successful startup order is trust-root guard -> verifier construction -> outbox replay;
- rejected trust root prevents verifier construction and outbox replay entirely;
- rejection audit evidence is reason-code-only and does not echo trust material;
- unconfigured development runtime remains explicitly `UNCONFIGURED`;
- trust-root registry namespace is protected from generic admin mutation.

## Relationship to ECHO external signer work

G8 guards PRIME verification-root configuration.

The separate ECHO external signer/KMS-adapter lane controls where ECHO signatures are produced and verifies signer-returned signatures. G8 does not claim to establish the ECHO checkpoint trust fingerprint as a remotely monotonic trust root.

That is a later composition gate.

## Claims boundary

If exact-head CI and full deployment/recovery qualification pass, G8 can establish:

**PROVEN INTERNALLY for the declared local PRIME trust-root rollback classes and rotation invariants.**

It does **not** establish:

- rollback resistance if a privileged actor restores the entire SARA persistence directory together with old configuration;
- independent administration;
- remote monotonic anchoring;
- WORM retention;
- HSM/TPM/KMS private-key custody;
- FIPS validation;
- signer non-compromise;
- external third-party witnessing;
- hardware-backed monotonic counters.

## Next gate

G9 should reuse the existing remote monotonic witness protocol rather than invent another local lineage system.

The target composition is:

`PRIME trust-root epoch + material digest -> signed remote monotonic witness receipt -> startup precondition`

with independently pinned witness identity and no caller-selectable bypass.

Only a genuinely separate deployment/administrative domain can promote that beyond local software rollback resistance.
