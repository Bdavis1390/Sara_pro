# SPDX Cryptographic Algorithm List — PQC parameter proposal

Status: **DRAFT / NOT AN SPDX POSITION**  
Target discussion: https://github.com/spdx/cryptographic-algorithm-list/issues/88  
Prepared for Worldshepherd/QCRYPTO validation before upstream submission.

## Decision proposed

Use the **same parameter mechanism as classic algorithms** for PQC. Reuse the existing `variant` parameter for named parameter sets instead of introducing a second parameter-set concept.

This matches the current SPDX Cryptographic Algorithm List distinction:

- **Property** — intrinsic, static characteristic of an algorithm.
- **Parameter** — operational/configuration element affecting how the algorithm is used.

## Minimal parameter additions

| Name | Description | Cardinality | Values |
|---|---|---:|---|
| `variant` | Existing parameter. Named parameter set from the governing specification, e.g. `ML-KEM-768`. | `[0..1]` | string or ordered list of strings |
| `nistSecurityCategory` | NIST PQC security category associated with a supported parameter set. | `[0..1]` | `'1'`, `'2'`, `'3'`, `'5'`, or an ordered subset |
| `publicKeyLength` | Public/encapsulation key length supported by the algorithm. | `[0..1]` | integer, list, or range; **bits** |
| `privateKeyLength` | Private/decapsulation key length supported by the algorithm. | `[0..1]` | integer, list, or range; **bits** |
| `ciphertextLength` | KEM ciphertext length. | `[0..1]` | integer, list, or range; **bits** |
| `signatureLength` | Digital-signature length. | `[0..1]` | integer, list, or range; **bits** |
| `sharedSecretLength` | KEM shared-secret length. | `[0..1]` | integer, list, or range; **bits** |
| `signingMode` | Signature-generation mode when deterministic and hedged/randomized operation are both specified. | `[0..1]` | `deterministic`, `hedged` |

### Why `signingMode`, not a boolean `deterministic`

A mode name expresses the actual operational choice and remains extensible. A boolean would encode one mode as the special case and would become awkward if later standards add another signing mode.

## Statefulness should be a property

`stateful` should not be introduced as a normal runtime parameter. For schemes such as XMSS/LMS, statefulness is intrinsic to the construction. Under the repository's own property/parameter definition, it belongs with algorithm properties unless a future algorithm genuinely makes statefulness configurable.

## Variant association problem

For modern PQC standards, artifact sizes and security categories are generally **derived from the selected variant** rather than independently selectable knobs.

Example: selecting `ML-KEM-768` fixes the encapsulation-key length, decapsulation-key length, ciphertext length, and NIST security category.

A flat SPDX record can list all supported variants and all supported lengths, but consumers **must not infer positional association between independent arrays** unless the format explicitly defines that relationship.

Recommended path:

1. **Phase 1 — compatibility-first:** retain the existing flat parameter structure; use `variant` as the primary PQC configuration selector and document supported lengths/categories.
2. **Phase 2 — structured mapping if required:** evaluate a variant-specific mapping such as `variant -> {securityCategory, publicKeyLength, ...}` for machine-readable association.

Worldshepherd keeps a structured fixture locally so that the relationship is never lost even if the initial upstream representation remains flat.

## Units

The current SPDX `keyLength` parameter is expressed in **bits**. New length parameters should therefore use bits for consistency. Authoritative standards that publish byte counts are converted deterministically at ingestion (`bits = bytes * 8`).

The provenance record must retain the authoritative source value and unit when transformation history matters.

## Security category semantics

Do **not** translate a NIST PQC category into a claim such as "exactly 128/192/256 bits of security." Store the categorical value (`1`, `2`, `3`, or `5`) and its governing reference.

## Initial validation scope

Validate the proposal against finalized NIST standards before using candidates whose parameter sets may still change:

- **ML-KEM — FIPS 203** — https://csrc.nist.gov/pubs/fips/203/final
- **ML-DSA — FIPS 204** — https://csrc.nist.gov/pubs/fips/204/final
- **SLH-DSA — FIPS 205** — https://csrc.nist.gov/pubs/fips/205/final

NIST also published the initial public draft of **SP 800-230** in 2026, defining additional SLH-DSA parameter sets for limited-signature use cases with an explicit per-key signature limit. This is a useful test that operational constraints may eventually need their own structured representation, but it should not expand the first SPDX PQC parameter PR.

## Worldshepherd/QCRYPTO invariants

- `WS-CRYPTO-001` — A PQC observation SHALL retain the named variant when known.
- `WS-CRYPTO-002` — A NIST security category SHALL be stored with the governing standard/version.
- `WS-CRYPTO-003` — Numeric artifact lengths SHALL have an explicit unit internally.
- `WS-CRYPTO-004` — Derived artifact dimensions SHALL NOT be treated as independently selectable unless the specification permits it.
- `WS-CRYPTO-005` — Algorithm identity SHALL NOT imply implementation validation.
- `WS-CRYPTO-006` — Side-channel, constant-time, interoperability, and implementation-validation evidence SHALL be stored separately from the algorithm taxonomy.
- `WS-CRYPTO-007` — Standardization/lifecycle state SHALL be temporally versioned.
- `WS-CRYPTO-008` — Withdrawn, deprecated, or superseded variants SHALL remain historically resolvable for provenance.
- `WS-CRYPTO-009` — Transformations SHALL retain original identifier, normalized identifier, variant, source standard, implementation version, and evidence source.
- `WS-CRYPTO-010` — Unknown attributes remain `UNKNOWN`; they SHALL NOT be inferred from popularity or defaults.

## Upstream-ready concise proposal

> I support using the same parameter mechanism as the classic algorithms for PQC. The existing `variant` parameter is the natural place for named parameter sets such as `ML-KEM-768`, so I would reuse it rather than introduce a second parameter-set field. I suggest adding `nistSecurityCategory`, `publicKeyLength`, `privateKeyLength`, `ciphertextLength`, `signatureLength`, `sharedSecretLength`, and `signingMode`, with numeric lengths expressed in bits for consistency with `keyLength`. Statefulness appears better modeled as a property because it is intrinsic to constructions such as XMSS/LMS. One modeling caveat is that PQC artifact sizes/categories are usually derived from the selected variant; flat arrays should therefore not imply positional mapping. The finalized FIPS 203/204/205 algorithms provide a stable first validation set before candidate algorithms are used to drive the schema.
