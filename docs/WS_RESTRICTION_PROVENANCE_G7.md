# WS-RESTRICTION-PROVENANCE G7 — SIGNER ISOLATION AND 10X ASSURANCE QUALITY

Status: **IMPLEMENTED IN SOFTWARE ON CURRENT-MAIN BRANCH / PENDING INTERNAL VALIDATION**

## Objective

G7 strengthens the signer trust boundary and defines a separate measurable "10x better" standard.

Protected main now contains both G6A signed ECHO witness verification and G6B signed-only PRIME V4 evidence.

G7 adds two controls:

1. SARA startup refuses PRIME private-signing material.
2. OVERWATCH reports a ten-dimension machine-resolved assurance-quality state for each validated restriction record.

## PRIME private-key ingress boundary

SARA is a verifier, not the PRIME signer.

At startup, recognized PRIME private/signing/seed/secret environment variable names fail closed when non-empty.

G7 also rejects common PEM private-key markers found under any `PRIME_SENTINEL_*` environment variable.

The following public verification configuration remains allowed:

- `PRIME_SENTINEL_PUBLIC_KEYS_JSON`;
- `PRIME_SENTINEL_REVOKED_KEY_IDS`.

The gate deliberately does not alter the independent ECHO checkpoint-signing design.

## Measurable signer-isolation improvement

The G7 test suite enumerates eight recognized PRIME private-key ingress variable classes.

Before this gate the SARA runtime secret validator did not reject those classes.

After G7 the accepted count is:

```text
8 recognized private-signing ingress classes -> 0 accepted
```

That is greater than a tenfold reduction in this declared ingress-path metric because the residual count reaches zero.

This does not establish HSM/KMS custody. It establishes that SARA itself refuses the recognized private-signing inputs.

## 10x better assurance metric

G7 evaluates ten operator assurance dimensions. At G3-start, four were already machine-resolved and six remained unresolved or weakly inferred.

Valid signed V4 evidence must resolve all ten automatically:

- restriction identity;
- event identity;
- delivery semantics;
- PRIME authority;
- authority binding;
- fingerprint-key epoch;
- signature verification;
- signing key identity;
- signing public-key fingerprint;
- raw-content persistence state.

Acceptance:

```text
6 baseline unresolved manual-inference units across 10 dimensions -> 0 unresolved
```

Historical V1-V3 records remain readable with visibly weaker assurance and cannot be counted as fully resolved V4 evidence.

## Required CI

The required build executes:

- existing PRIME authorization verification;
- restriction provenance G1-G7;
- signer-isolation tests;
- 10x security scorecard;
- 10x quality scorecard;
- signed V4 persistence and read-time verification.

## Claims boundary

G7 does not prove that the external PRIME signer uses:

- an HSM;
- a TPM;
- cloud KMS;
- a FIPS-validated module;
- two-person control;
- hardware-enforced non-exportability;
- certified key destruction.

Those require external signer/provider evidence.

G7 proves only the software boundary that SARA refuses recognized PRIME private signing material and verifies externally supplied signatures with configured public keys.

G7 is reconciled directly onto the combined protected G6A+G6B head. Until this exact head passes required CI, CodeQL/Analyze, full Verified Local deployment/recovery/evidence qualification, and protected merge, classify G7 as **IMPLEMENTED IN SOFTWARE / PENDING INTERNAL VALIDATION**.
