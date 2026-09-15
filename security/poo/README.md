# Worldshepherd Proof of Ownership (PoO) v1

## Purpose

PoO is a claims-controlled ownership-attestation protocol that composes independent evidence instead of treating any one consensus primitive as ownership.

### The three proof legs

- **PoW — Proof of Work:** claim-specific bounded work tied to the asset and claim. This adds freshness/cost and makes cheap claim flooding harder. It does **not** prove ownership by itself.
- **PoC — Proof of Control:** challenge-response proving current control of the authorized key, device, custody mechanism, or other asset-bound control surface. In this protocol, PoC means **Proof of Control**.
- **PoS — Proof of Stake:** bonded/slashable value or other accountable stake tied to the claim. This creates economic consequence for fraudulent assertions. It does **not** prove ownership by itself.

PoO also requires title/provenance binding, asset fingerprint binding, claimant identity binding, freshness, and a non-revoked state.

## Core rule

PoO uses fail-closed AND semantics, not a weighted score:

```text
PoO_valid =
    asset_fingerprint_bound
    AND claimant_identity_bound
    AND title_or_provenance_bound
    AND PoW_verified
    AND PoC_control_verified
    AND PoS_bond_verified
    AND freshness_verified
    AND not_revoked
```

A claimant cannot compensate for a missing control proof by adding more work or stake.

## Why the title/provenance predicate is separate

PoW, PoC, and PoS provide computational, control, and economic evidence. They cannot manufacture legal title. A valid PoO therefore means **technical ownership attestation under the supplied evidence**, not a court judgment, government registry entry, or statutory title determination.

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
3. recipient PoC challenge;
4. fresh recipient PoW;
5. recipient PoS bond where policy requires it;
6. title/provenance transition evidence;
7. revocation/supersession of the prior PoO;
8. ECHO provenance recording and PRIME/SARA policy approval.

A new PoO should reference the previous digest rather than overwriting history.

## Worldshepherd mapping

- **ECHO:** stores provenance, claim events, evidence hashes, revocations, and transfer lineage.
- **PRIME:** enforces ownership policy, required predicates, stake rules, asset class rules, and revocation policy.
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

| Attack | PoW | PoC | PoS | Title/provenance | Result |
|---|---:|---:|---:|---:|---|
| cheap Sybil claims | helps | helps | helps | neutral | harder |
| stolen key | weak | may pass until revoked | neutral | helps | revocation/recovery required |
| wealthy false claimant | weak | blocks without control | insufficient alone | blocks without provenance | fail closed |
| compute-rich false claimant | insufficient alone | blocks without control | neutral | blocks without provenance | fail closed |
| replayed old claim | neutral | freshness check | neutral | lineage helps | rejected when stale/revoked |
| registry/provenance conflict | neutral | neutral | neutral | detects conflict | human/policy resolution |

## Claims boundary

PoO v1 does **not** claim:

- legal title adjudication;
- government registry authority;
- transfer execution authority;
- live-value movement authority;
- external validation or certification;
- that PoW, PoC, or PoS alone proves ownership.

Current status: **IMPLEMENTED IN SOFTWARE / validation pending** until exact-head tests pass.
