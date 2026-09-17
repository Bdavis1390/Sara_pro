# WS-RESTRICTION-PROVENANCE G5 — FINGERPRINT KEY EPOCH PROVENANCE

Status: **IMPLEMENTED IN SOFTWARE ON CANDIDATE BRANCH / PENDING EXACT-HEAD CI**

## Objective

G5 makes keyed restriction fingerprints rotation-aware without persisting the fingerprint secret.

Before G5, the evidence envelope stored HMAC-SHA256 fingerprints but did not identify which fingerprint-key epoch produced them. A later analyst could observe that two fingerprints differed without being able to distinguish content change from key rotation.

G5 removes that ambiguity for new evidence.

## V3 provenance schema

New captures use:

```text
schema = WS-RESTRICTION-PROVENANCE-V3
authority = PRIME_SENTINEL
fingerprint_key_epoch_id = <32 lowercase hex characters>
```

The epoch identifier is derived by a domain-separated HMAC over a constant label using the same high-entropy fingerprint key. The secret key itself is never placed in the evidence record.

The identifier is therefore:

- stable for the same fingerprint key;
- different after key rotation;
- opaque and non-secret under the existing high-entropy-key assumption;
- bound into the canonical V3 restriction identity before `restriction_id` is computed.

Changing epoch semantics cannot silently preserve the same V3 restriction identity.

## Comparison rule

Fingerprint equality is meaningful only when the compared records have the same non-null `fingerprint_key_epoch_id`.

For V1/V2 evidence, epoch provenance is explicitly unknown. Consumers must not infer that fingerprints from legacy records were produced under the same key merely because they use the same algorithm.

## Legacy compatibility

- V1 remains readable with outer authority only.
- V2 remains readable with authority bound into the payload identity.
- V3 adds fingerprint-key epoch binding.

The strict observability projection reports:

```text
fingerprint_key_epoch_id = null
fingerprint_epoch_bound_in_payload = false
```

for V1/V2, and the concrete epoch identifier plus `true` for V3.

This preserves old evidence without retroactively upgrading its assurance level.

## Remediation binding

Restriction remediation directives now carry the fingerprint-key epoch identifier alongside the content fingerprints. Human-review and safe-transform workflows can therefore reject cross-epoch comparisons instead of treating rotated-key fingerprints as directly comparable.

## Executable 10x gate

The G5 test declares four G4-era residual ambiguity classes:

1. evidence does not identify the fingerprint-key epoch;
2. observability cannot expose whether epoch provenance is bound;
3. remediation content bindings omit epoch context;
4. the same raw content under a rotated key cannot be distinguished from an ordinary content change by epoch metadata.

Baseline residual units: **4**.

10x threshold: **<= 0.4 residual units**.

Because the count is integral, the implemented pass condition is **0/4 residual ambiguity classes open**, while all previous zero-tolerance controls remain closed.

This is a narrow engineering ratio. It is not a claim that the entire system is ten times more secure.

## Claims boundary

G5 does not provide:

- independent key custody;
- HSM/TPM protection;
- digital signatures;
- external witness authentication;
- compromise detection if the fingerprint key itself is stolen;
- proof that deployment operators rotated keys correctly;
- cross-organization key identity.

The epoch identifier is evidence context, not a certificate or signing key.

## Next gate

G6 should address **signer/witness assurance**: move from application-level authority strings and unkeyed semantic IDs toward independently verifiable authenticity for selected evidence, with explicit signer identity, algorithm agility, verification failure behavior, and key-custody boundaries.
