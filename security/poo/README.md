# Worldshepherd Proof of Ownership (PoO) v1

## Purpose

PoO is a claims-controlled ownership-attestation protocol that composes independent evidence instead of treating any one consensus primitive as ownership.

### The three proof legs

- **PoW — Proof of Work:** claim-specific bounded work tied to the asset and claim. This adds freshness/cost and makes cheap claim flooding harder. It does **not** prove ownership by itself.
- **PoC — Proof of Concept:** a bounded demonstration that the claimed ownership mechanism for the asset actually works and can be independently checked. A PoC might demonstrate that an asset-binding method, custody handoff, secure-element challenge, registry integration, or other ownership mechanism performs as claimed. It does **not** prove current control or legal ownership by itself.
- **PoS — Proof of Stake:** bonded/slashable value or other accountable stake tied to the claim. This creates economic consequence for fraudulent assertions. It does **not** prove ownership by itself.

PoO separately requires **control/custody verification**. That predicate establishes that the claimant currently controls the asset-bound authority or custody surface. It is intentionally not called PoC.

PoO also requires title/provenance binding, asset fingerprint binding, claimant identity binding, freshness, and a non-revoked state.

## Core rule

PoO uses fail-closed AND semantics, not a weighted score:

```text
PoO_valid =
    asset_fingerprint_bound
    AND claimant_identity_bound
    AND title_or_provenance_bound
    AND PoW_verified
    AND PoC_concept_verified
    AND control_or_custody_verified
    AND PoS_bond_verified
    AND freshness_verified
    AND not_revoked
```

A claimant cannot compensate for missing proof-of-concept, control/custody, or provenance by adding more work or stake.

## Why control/custody is separate from PoC

Proof of Concept answers: **does the claimed ownership mechanism work as demonstrated?**

Control/custody verification answers: **does this claimant currently control the asset-bound authority?**

Those are different questions. A successful PoC cannot establish that the present claimant controls the asset, and a valid control proof cannot establish that the broader ownership mechanism has been demonstrated or validated.

## Why the title/provenance predicate is separate

PoW, PoC, control/custody, and PoS provide computational, demonstrative, control, and economic evidence. They cannot manufacture legal title. A valid PoO therefore means **technical ownership attestation under the supplied evidence**, not a court judgment, government registry entry, or statutory title determination.

Even when an external title reference has been verified, Worldshepherd reports only:

`TECHNICAL_ATTESTATION_WITH_EXTERNAL_TITLE_REFERENCE`

and keeps `legal_ownership_established = false`.

## Semantic commitment

The deterministic ownership digest commits to:

```text
schema
asset_id
claimant_id
title_reference
control_key_fingerprint
work_reference
concept_reference
stake_reference
issued_at
expires_at
previous_poo_digest
```

Evidence-verification booleans are deliberately excluded from the semantic digest. This allows the evidence state to be re-evaluated without changing the underlying ownership claim identity.

## Transfer chain

`previous_poo_digest` supports a transfer/provenance chain. A future transfer protocol should require, at minimum:

1. valid current PoO;
2. current-owner transfer authorization;
3. recipient control/custody verification;
4. fresh recipient PoW;
5. a recipient PoC demonstrating that the transfer/ownership mechanism performs as intended for the asset class;
6. recipient PoS bond where policy requires it;
7. title/provenance transition evidence;
8. revocation/supersession of the prior PoO;
9. ECHO provenance recording and PRIME/SARA policy approval.

A new PoO should reference the previous digest rather than overwriting history.

## Worldshepherd mapping

- **ECHO:** stores provenance, claim events, evidence hashes, revocations, PoC evidence, and transfer lineage.
- **PRIME:** enforces ownership policy, required predicates, PoC acceptance criteria, control/custody rules, stake rules, asset-class rules, and revocation policy.
- **SARA:** orchestrates bounded workflows and required human approvals.
- **OVERWATCH:** monitors expiration, revocation, stale control proofs, bond state, conflicts, and duplicate claims.
- **QCRYPTO:** supplies crypto-agility and hybrid/PQ migration policy for signatures and control challenges.

## Asset classes

PoO can be adapted to:

- digital assets and software/IP;
- physical equipment with serial/secure-element/PUF/manufacturer provenance;
- datasets and model artifacts;
- licenses/entitlements;
- custody positions;
- tokenized representations of off-chain assets.

For off-chain regulated or titled property, PoO remains an evidence layer and must defer to the relevant authoritative registry or legal process.

## Threat model

| Attack | PoW | PoC | Control/custody | PoS | Title/provenance | Result |
|---|---:|---:|---:|---:|---:|---|
| cheap Sybil claims | helps | neutral | helps | helps | neutral | harder |
| broken/fake ownership mechanism | neutral | detects failed concept | neutral | neutral | neutral | blocked |
| stolen key | weak | may still pass | may pass until revoked | neutral | helps | revocation/recovery required |
| wealthy false claimant | weak | insufficient alone | blocks without control | insufficient alone | blocks without provenance | fail closed |
| compute-rich false claimant | insufficient alone | insufficient alone | blocks without control | neutral | blocks without provenance | fail closed |
| replayed old claim | neutral | stale PoC can fail policy | freshness/control check | neutral | lineage helps | rejected when stale/revoked |
| registry/provenance conflict | neutral | neutral | neutral | neutral | detects conflict | human/policy resolution |

## Claims boundary

PoO v1 does **not** claim:

- legal title adjudication;
- government registry authority;
- transfer execution authority;
- live-value movement authority;
- external validation or certification;
- that PoW, PoC, control/custody, or PoS alone proves ownership.

Current status: **IMPLEMENTED IN SOFTWARE / validation pending** until exact-head tests pass.
