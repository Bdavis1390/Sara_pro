# WS-RESTRICTION-PROVENANCE G5 — FINGERPRINT KEY EPOCH PROVENANCE

Status: **IMPLEMENTED IN SOFTWARE / PROVEN INTERNALLY FOR THE TESTED KEY-EPOCH AND CUMULATIVE 10X INVARIANTS**

## Objective

G5 removes ambiguity when the deployment HMAC key used for non-content fingerprints is intentionally rotated.

Before G5, two otherwise identical restriction events generated under different HMAC keys produce different fingerprints, but persisted evidence does not state which non-secret key epoch produced them. Operators therefore cannot distinguish:

- content changed;
- fingerprint key changed;
- both changed.

G5 adds a bounded non-secret epoch identifier to the evidence identity.

## V3 provenance schema

New captures use:

```text
schema             = WS-RESTRICTION-PROVENANCE-V3
authority          = PRIME_SENTINEL
fingerprint_key_id = <non-secret bounded identifier>
```

The key ID is included in the canonical safe identity before `restriction_id` is derived.

The HMAC secret itself remains outside the restriction record.

## Required epoch identifier

`capture_restriction()` requires `fingerprint_key_id` for new V3 evidence.

There is intentionally no "unknown epoch" fallback. A new event whose epoch cannot be identified fails closed instead of reintroducing the comparison ambiguity.

`fingerprint_key_id_from_environment()` reads the non-secret ID from `RESTRICTION_FINGERPRINT_KEY_ID` and applies the same bounded identifier grammar used for other provenance components.

## Rotation semantics

For identical content and identical HMAC key material:

```text
epoch A -> fingerprint X, restriction ID A
epoch B -> fingerprint X, restriction ID B
```

The content fingerprint remains the same because the HMAC key did not change, while evidence identity changes because the declared epoch changed.

For identical content and changed HMAC key material:

```text
fingerprint changes
restriction ID changes
```

That difference is now interpretable because the record also names the declared key epoch.

## Observability

G5 extends the strict non-content projection with:

- `fingerprint_key_id`;
- `fingerprint_key_epoch_bound_in_payload`.

V1/V2 historical records remain readable and report:

```text
fingerprint_key_id = null
fingerprint_key_epoch_bound_in_payload = false
```

V3 requires a valid bounded key ID and reports the binding as true.

Status aggregation includes `by_fingerprint_key_id`, using `UNBOUND_LEGACY` for V1/V2 records.

## Downgrade and tamper detection

The key epoch is included in V3 semantic-ID recomputation.

Therefore:

- changing the key ID while retaining the old restriction ID fails;
- stripping the V3 key ID and relabeling the record V2 while retaining the old V3 restriction ID fails;
- V2 cannot carry the V3-only key-ID field without failing its field contract.

## Remediation binding

G5 includes `fingerprint_key_id` in the remediation content-binding block so later bounded remediation is interpreted in the same declared fingerprint epoch as the originating restriction evidence.

## Acceptance tests

The G5 suite verifies:

1. new captures use V3 and require a non-secret key epoch ID;
2. key ID is persisted but key material is not;
3. changing only the declared epoch changes restriction identity but not content fingerprints;
4. changing key material changes fingerprints even if a caller reuses the same declared ID;
5. V3 projections expose only the non-secret epoch identifier;
6. V2 legacy records remain explicitly epoch-unbound;
7. V3 key-ID tampering with a stale restriction ID fails;
8. V3-to-V2 downgrade with the stale V3 ID fails;
9. invalid or missing environment key IDs fail closed;
10. bounded observability aggregates records by key epoch;
11. G1-G5 restriction suites run together in required CI;
12. the cumulative 10x gate expands from five to six G3-start residual classes and requires 0/6 open.

## Claims boundary

`fingerprint_key_id` is an operator/deployment provenance identifier. G5 does not cryptographically prove that a particular secret key corresponds to that identifier.

G5 does not store, export, derive, or expose the HMAC secret.

It does not establish KMS/HSM custody, key rotation automation, secure key destruction, independent key registry validation, or external signer/witness assurance.

Those are separate gates.

G5 merged through protected main in PR #430 at commit `0714d058b07edbe26d301409c6b403615d4b1c89` after required CodeQL/Analyze/test-and-build and the full Verified Local deployment/recovery/evidence gate succeeded. The cumulative executable scorecard closed all six declared G3-start residual classes (6 -> 0) while preserving every prior zero-tolerance control. This proof applies only to those declared software invariants.
