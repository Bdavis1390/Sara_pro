# Worldshepherd Proof of Ownership (PoO) v1

## Purpose

PoO is a claims-controlled ownership-attestation protocol that composes independent evidence instead of treating any one consensus primitive as ownership.

### The proof and verification legs

- **PoW — Proof of Work:** claim-specific bounded work tied to the asset and claim. This adds freshness/cost and makes cheap claim flooding harder. It does **not** prove ownership by itself.
- **PoC — Proof of Concept:** a bounded demonstration that the claimed ownership mechanism for the asset actually works and can be independently checked. A PoC might demonstrate that an asset-binding method, custody handoff, secure-element challenge, registry integration, or other ownership mechanism performs as claimed. It does **not** prove current control or legal ownership by itself.
- **COC — Control/Custody Verification:** verifies that the claimant currently controls or holds custody over the asset-bound authority or custody surface. It is a separate mandatory predicate and is not PoC.
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
    AND PoC_concept_verified
    AND COC_verified
    AND PoS_bond_verified
    AND freshness_verified
    AND not_revoked
```

A claimant cannot compensate for missing Proof of Concept, COC, or provenance by adding more work or stake.

## Why COC is separate from PoC

Proof of Concept answers: **does the claimed ownership mechanism work as demonstrated?**

COC answers: **does this claimant currently control or hold custody over the asset-bound authority?**

Those are different questions. A successful PoC cannot establish present control/custody, and a valid COC cannot establish that the broader ownership mechanism itself has been demonstrated or validated.

## Why the title/provenance predicate is separate

PoW, PoC, COC, and PoS provide computational, demonstrative, control/custody, and economic evidence. They cannot manufacture legal title. A valid PoO therefore means **technical ownership attestation under the supplied evidence**, not a court judgment, government registry entry, or statutory title determination.

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

## Governed transfer and supersession

A transfer never edits or erases the prior PoO. It prepares a **new PoO candidate** whose `previous_poo_digest` points to the prior attestation.

Transfer readiness is also fail-closed:

```text
Transfer_ready =
    prior_PoO_valid
    AND asset_continuity_verified
    AND current_owner_authorized
    AND recipient_identity_bound
    AND recipient_PoC_concept_verified
    AND recipient_COC_verified
    AND recipient_PoW_verified
    AND recipient_PoS_bond_verified
    AND title_or_provenance_transition_bound
    AND freshness_verified
    AND no_active_dispute
    AND transfer_not_revoked
    AND human_approval_verified
```

When every predicate passes, Worldshepherd reports only:

`READY_FOR_GOVERNED_SUPERSESSION`

This means the evidence package is internally ready to produce the next technical PoO candidate. It does **not** mean a transfer has executed, funds/value moved, legal title changed, or a government/third-party registry accepted the transition.

The transfer guard hard-codes:

```text
transfer_executed = false
live_value_authorized = false
legal_title_transferred = false
```

The derived recipient candidate must itself pass the ordinary PoO evaluator, and its `previous_poo_digest` must match the prior ownership record. A disputed, stale, revoked, unauthorized, or incomplete transfer cannot derive the next PoO candidate.

## Recovery and disputes

Recovery is a separate **same-owner** path for lost control, compromised control, custody failure, or a technical record correction. It is not an alternate transfer mechanism and cannot silently change the claimant.

Recovery readiness requires stronger re-verification:

```text
Recovery_ready =
    prior_PoO_valid
    AND asset_continuity_verified
    AND claimant_continuity_verified
    AND claimant_identity_reverified
    AND title_or_provenance_reverified
    AND compromise_or_loss_evidence_bound
    AND recovery_PoW_verified
    AND recovery_PoC_concept_verified
    AND alternate_COC_verified
    AND recovery_PoS_bond_verified
    AND multisource_or_quorum_verified
    AND freshness_verified
    AND recovery_not_revoked
    AND human_approval_verified
    AND (NOT active_dispute OR dispute_resolution_verified)
```

Only the following recovery reasons are accepted by v1:

- `LOST_CONTROL`
- `COMPROMISED_CONTROL`
- `CUSTODY_FAILURE`
- `TECHNICAL_RECORD_CORRECTION`

`OWNER_CHANGE` is intentionally not a recovery reason; ownership change belongs in the governed transfer lane.

When all recovery predicates pass, the state is only:

`READY_FOR_GOVERNED_RECOVERY_SUPERSESSION`

The recovery guard hard-codes:

```text
ownership_restored = false
control_rotated = false
transfer_executed = false
live_value_authorized = false
legal_title_changed = false
```

A ready recovery may derive a **same-claimant replacement PoO candidate** using a newly verified COC surface and linking back to `previous_poo_digest`. It does not rotate credentials, revoke the prior control surface, modify ECHO records, or execute any transfer by itself.

An active dispute blocks recovery unless `dispute_resolution_verified` is explicitly present. This keeps dispute resolution visible and prevents recovery from becoming a hidden bypass around transfer/title conflicts.

## Worldshepherd mapping

- **ECHO:** stores provenance, claim events, evidence hashes, revocations, PoC evidence, COC evidence, prior/new PoO lineage, disputes, recovery evidence, and transfer evidence.
- **PRIME:** enforces ownership policy, required predicates, PoC acceptance criteria, COC rules, stake rules, asset-class rules, revocation policy, transfer policy, and dispute/recovery policy.
- **SARA:** orchestrates bounded claim, transfer, recovery, and dispute workflows with required human approvals.
- **OVERWATCH:** monitors expiration, revocation, stale COC evidence, bond state, conflicts, duplicate claims, recovery state, and unresolved disputes.
- **QCRYPTO:** supplies crypto-agility and hybrid/PQ migration policy for signatures, COC challenges, transfer authorization, and recovery evidence.

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

| Attack | PoW | PoC | COC | PoS | Title/provenance | Result |
|---|---:|---:|---:|---:|---:|---|
| cheap Sybil claims | helps | neutral | helps | helps | neutral | harder |
| broken/fake ownership mechanism | neutral | detects failed concept | neutral | neutral | neutral | blocked |
| stolen key | weak | may still pass | may pass until revoked | neutral | helps | recovery/revocation required |
| wealthy false claimant | weak | insufficient alone | blocks without COC | insufficient alone | blocks without provenance | fail closed |
| compute-rich false claimant | insufficient alone | insufficient alone | blocks without COC | neutral | blocks without provenance | fail closed |
| replayed old claim | neutral | stale PoC can fail policy | freshness/COC check | neutral | lineage helps | rejected when stale/revoked |
| registry/provenance conflict | neutral | neutral | neutral | neutral | detects conflict | human/policy resolution |
| unauthorized transfer | neutral | neutral | recipient COC insufficient | neutral | transition blocked | current-owner authorization required |
| double-transfer/conflicting lineage | neutral | neutral | neutral | neutral | lineage/dispute check | blocked pending resolution |
| compromised current key recovery | fresh work required | recovery mechanism demonstrated | alternate COC required | fresh bond required | reverified | governed recovery only |
| disputed recovery | insufficient | insufficient | insufficient | insufficient | dispute resolution required | blocked until resolved |

## Claims boundary

PoO v1 does **not** claim:

- legal title adjudication;
- government registry authority;
- automatic transfer execution;
- automatic credential/key rotation;
- automatic prior-control revocation;
- live-value movement authority;
- external validation or certification;
- that PoW, PoC, COC, or PoS alone proves ownership.

Validation record:

- Ownership-attestation core with **PoC = Proof of Concept** and **COC = Control/Custody Verification**: schema `WS-POO-V2`; exact-head validation required after the COC schema correction.
- Governed transfer/supersession extension: schema `WS-POO-TRANSFER-V2`; exact-head validation required after the COC schema correction.
- Same-owner recovery/dispute extension: schema `WS-POO-RECOVERY-V2`; exact-head validation required after the COC schema correction.
